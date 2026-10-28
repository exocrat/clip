"""Exercise the real loopback transfer boundary without Docker, AWS or secrets."""

from contextlib import closing
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path
from threading import Thread

import pytest

from scripts.identity_build_transfer import MAX_SOURCE, transfer_server


@pytest.fixture
def endpoint(tmp_path: Path):
    """Start a real disposable server with only synthetic source bytes."""
    directory = tmp_path / "transfer"
    server = transfer_server(directory, hashlib.sha256(b"source").hexdigest(), 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield directory, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(port: int, method: str, path: str, body: bytes | None = None, **headers):
    """Read a complete local response and close the connection after each attempt."""
    with closing(HTTPConnection("127.0.0.1", port, timeout=3)) as connection:
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        return response.status, response.read()


def test_upload_once_and_completed_artifacts(endpoint):
    directory, port = endpoint
    assert request(port, "POST", "/source.tar", b"source")[0] == 201
    assert (directory / "source.tar").read_bytes() == b"source"
    assert request(port, "POST", "/source.tar", b"source")[0] == 409
    (directory / "image.tar").write_bytes(b"image")
    assert request(port, "GET", "/image.tar")[0] == 404
    (directory / "result.json").write_text(json.dumps({"synthetic": True}))
    assert request(port, "GET", "/image.tar") == (200, b"image")
    assert request(port, "GET", "/result.json")[0] == 200


def test_bad_hash_and_unbounded_upload_leave_no_source(endpoint):
    directory, port = endpoint
    assert request(port, "POST", "/source.tar", b"wrong")[0] == 400
    assert not (directory / "source.tar").exists()
    assert not (directory / "source.part").exists()
    assert (
        request(
            port, "POST", "/source.tar", b"", **{"Content-Length": str(MAX_SOURCE + 1)}
        )[0]
        == 400
    )


def test_no_browsing_query_paths_or_symlinks(endpoint, tmp_path):
    directory, port = endpoint
    for path in ("/", "/../secret", "/source.tar", "/result.json?x=1"):
        assert request(port, "GET", path)[0] == 404
    outside = tmp_path / "outside"
    outside.write_bytes(b"unrelated")
    (directory / "result.json").write_text("{}")
    (directory / "image.tar").symlink_to(outside)
    assert request(port, "GET", "/image.tar")[0] == 404
