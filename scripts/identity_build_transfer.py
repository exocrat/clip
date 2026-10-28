"""Serve only a hash-pinned source upload and completed image over an SSM tunnel.

Explicit operator tool for a disposable private build host, never an app service.
Bind loopback only; AWS SSM session authorization supplies the transport boundary.
No credentials, directory browsing, archive extraction or build execution occurs.
"""

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import re
import shutil
import time

MAX_SOURCE = 100 * 1024 * 1024


def transfer_server(directory: Path, source_hash: str, port: int = 18765) -> HTTPServer:
    """Create a loopback-only server in a new owner-only directory.

    Accept source.tar once after streaming SHA verification. Expose only image.tar
    and result.json after the operator build has written its completion marker.
    The optional port supports isolated local checks; live instructions pin18765.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        raise ValueError("Invalid source digest")
    directory.mkdir(mode=0o700)

    class Handler(BaseHTTPRequestHandler):
        """No access/error logs, arbitrary paths, chunked uploads or overwrite."""

        def log_message(self, *_: object) -> None:
            """Keep request details out of SSM/system logs."""

        def do_POST(self) -> None:
            """Bound each source upload and discard incomplete/mismatched bytes."""
            self.connection.settimeout(30)
            if self.path != "/source.tar" or (directory / "source.tar").exists():
                self.send_error(409)
                return
            size = self.headers.get("Content-Length", "")
            if (
                self.headers.get("Transfer-Encoding")
                or not 1 <= len(size) <= 9
                or not size.isascii()
                or not size.isdecimal()
                or not 0 < int(size) <= MAX_SOURCE
            ):
                self.send_error(400)
                return
            temporary = directory / "source.part"
            try:
                digest = hashlib.sha256()
                remaining = int(size)
                with temporary.open("xb") as output:
                    temporary.chmod(0o600)
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError("Incomplete upload")
                        output.write(chunk)
                        digest.update(chunk)
                        remaining -= len(chunk)
                if digest.hexdigest() != source_hash:
                    raise ValueError("Source digest mismatch")
                temporary.rename(directory / "source.tar")
                self.send_response(201)
                self.end_headers()
            except (OSError, ValueError) as failure:
                # Binding preserves parentheses under Black/Python3.14 for the
                # Amazon Linux host Python3.9 parser; never log the exception.
                del failure
                temporary.unlink(missing_ok=True)
                self.send_error(400)

        def do_GET(self) -> None:
            """Stream only completed artifacts; never follow file symlinks."""
            if self.path not in ("/image.tar", "/result.json"):
                self.send_error(404)
                return
            path = directory / self.path[1:]
            marker = directory / "result.json"
            if (
                not marker.is_file()
                or marker.is_symlink()
                or not path.is_file()
                or path.is_symlink()
            ):
                self.send_error(404)
                return
            self.connection.settimeout(30)
            self.send_response(200)
            self.send_header("Content-Length", str(path.stat().st_size))
            self.end_headers()
            try:
                with path.open("rb") as source:
                    shutil.copyfileobj(source, self.wfile, 1024 * 1024)
            except OSError:
                pass  # A lost private tunnel is not permission to retry publication.

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    return server


def main() -> None:
    """Require explicit host inputs and stop accepting requests after two hours."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()
    with transfer_server(args.directory, args.source_sha256) as server:
        deadline = time.monotonic() + 7200
        while time.monotonic() < deadline:
            server.handle_request()


if __name__ == "__main__":
    main()
