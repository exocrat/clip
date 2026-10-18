"""Check existing storage guarantees in a fresh local Compose test database.

Run with Python 3.14 and the local wrapper's synthetic password environment.
No driver dependency, domain adapter, private data or cloud target is used.
This intentionally leaves the isolated test database for inspection and stops
only the validated local service. Application locking/delivery is not tested.
"""

import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = "clip-local-postgres-1"


class Checks:
    """Own a uniquely named synthetic database and bounded subprocess evidence."""

    def __init__(self):
        """Use only required local inputs; never inherit database target settings."""
        password = os.environ.get("CLIP_LOCAL_POSTGRES_PASSWORD", "")
        if not password or not re.fullmatch(r"[a-zA-Z0-9_.~-]+", password):
            raise ValueError("Set the wrapper-compatible local synthetic password")
        self.password = password
        self.env = {key: os.environ[key] for key in ("PATH", "HOME")}
        self.env["CLIP_LOCAL_POSTGRES_PASSWORD"] = password
        self.db = "clip_test_races_" + uuid.uuid4().hex[:12]
        self.evidence = Path(tempfile.mkdtemp(prefix="clip-pd08-races-"))
        self.children = []

    def run(self, name, args, sql=None, extra=None):
        """Execute one bounded command and retain sanitized output, failing closed."""
        result = subprocess.run(
            args,
            input=sql,
            capture_output=True,
            text=True,
            timeout=90,
            env=self.env | (extra or {}),
            cwd=ROOT,
        )
        output = (result.stdout + result.stderr).replace(self.password, "[REDACTED]")
        (self.evidence / f"{name}.log").write_text(output)
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect sanitized evidence")
        return result.stdout.strip()

    def command(self, database=None, app="clip-check"):
        """Fix psql to the validated container and explicit local test database."""
        return [
            "docker",
            "exec",
            "-i",
            "--env",
            f"PGAPPNAME={app}",
            CONTAINER,
            "psql",
            "-XqAt",
            "-U",
            "clip_local",
            "-d",
            database or self.db,
            "-v",
            "ON_ERROR_STOP=1",
            "-v",
            "VERBOSITY=verbose",
        ]

    def sql(self, name, text):
        """Bound lock waits and statement execution for administrative test SQL."""
        return self.run(
            name,
            self.command(),
            "SET statement_timeout='15s'; SET lock_timeout='10s';" + text,
        )

    def start(self):
        """Validate/start the owned service and migrate a new database exactly once."""
        self.run("start", ["bash", "database/local-db.sh", "start"])
        self.run("create", self.command("clip_local"), f"CREATE DATABASE {self.db};")
        url = f"postgres://clip_local:{self.password}@127.0.0.1:5432/{self.db}?sslmode=disable"
        self.run(
            "migrate",
            [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--network",
                f"container:{CONTAINER}",
                "--env",
                "DATABASE_URL",
                "--mount",
                f"type=bind,src={ROOT}/database/migrations,dst=/db/migrations,readonly",
                "ghcr.io/amacneil/dbmate:2.36.0",
                "--env-file",
                "/dev/null",
                "--migrations-dir",
                "/db/migrations",
                "--no-dump-schema",
                "migrate",
                "--strict",
            ],
            extra={"DATABASE_URL": url},
        )

    def seed(self, image_count=2, thread=True):
        """Create fresh regular users, listing/uploads/images and optional members."""
        ids = {
            key: str(uuid.uuid4())
            for key in ("seller", "buyer", "item", "thread", "offer", "sk", "bk")
        }
        s, b, item, t = (ids[k] for k in ("seller", "buyer", "item", "thread"))
        text = f"""BEGIN;
INSERT INTO identity.users(id,account_class,status) VALUES ('{s}','regular','active'),('{b}','regular','active');
INSERT INTO listings.sale_listings(id,owner_id,title,description,category_id,condition_code,asking_price_paise,negotiable,pickup_area,availability)
SELECT '{item}','{s}','Synthetic books','Controlled fixture',id,'good',100,true,'Synthetic','available' FROM listings.categories WHERE code='books';
"""
        ids["images"] = []
        for position in range(image_count):
            image = str(uuid.uuid4())
            ids["images"].append(image)
            text += self.image(ids, image, position)
        if thread:
            text += self.thread(ids, t)
            text += f"""INSERT INTO conversations.public_key_versions(id,user_id,version,public_key_material,protocol_id)
VALUES ('{ids['sk']}','{s}',1,decode('01','hex'),'synthetic-storage-test'),('{ids['bk']}','{b}',1,decode('02','hex'),'synthetic-storage-test');"""
        self.sql("seed-" + item, text + "COMMIT;")
        return ids

    def image(self, ids, image, position):
        """Build a confirmed synthetic upload and its image without storage calls."""
        return f"""INSERT INTO listings.image_uploads(id,owner_id,object_key,state,expires_at,confirmed_at)
VALUES ('{image}','{ids['seller']}','test/{image}','confirmed',CURRENT_TIMESTAMP+INTERVAL '24 hours',CURRENT_TIMESTAMP);
INSERT INTO listings.images(id,listing_id,upload_id,object_key,position,media_type,size_bytes)
VALUES ('{image}','{ids['item']}','{image}','test/{image}',{position},'image/png',1);"""

    def thread(self, ids, thread):
        """Create exactly the two approved origin participants in one transaction."""
        return f"""INSERT INTO conversations.threads(id,listing_id,initiator_id,counterparty_id)
VALUES ('{thread}','{ids['item']}','{ids['buyer']}','{ids['seller']}');
INSERT INTO conversations.members(conversation_id,user_id) VALUES ('{thread}','{ids['buyer']}'),('{thread}','{ids['seller']}');"""

    def entry(self, ids, kind="message"):
        """Build an entry; message bytes are deliberately fake storage-shape data."""
        entry = str(uuid.uuid4())
        text = f"""INSERT INTO conversations.entries(id,conversation_id,sender_id,client_operation_id,kind)
VALUES ('{entry}','{ids['thread']}','{ids['buyer']}','{uuid.uuid4()}','{kind}');"""
        if kind == "message":
            text += f"""INSERT INTO conversations.encrypted_payloads(entry_id,protocol_id,envelope_version,sender_key_version_id,recipient_key_version_id,envelope)
VALUES ('{entry}','synthetic-storage-test',1,'{ids['bk']}','{ids['sk']}',decode('00','hex'));"""
        return entry, text

    def race(self, name, first, second, loser=None, isolation="READ COMMITTED"):
        """Prove actual lock overlap before committing the first independent session.

        SQLSTATE is checked for expected rejection; any timeout, deadlock or
        unrelated error fails. Both clients and their server statements are bounded.
        """
        prefix = f"SET statement_timeout='15s'; SET lock_timeout='10s'; SET idle_in_transaction_session_timeout='25s'; BEGIN ISOLATION LEVEL {isolation};"
        holder = subprocess.Popen(
            self.command(app=name + "-holder"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env,
        )
        self.children.append(holder)
        holder.stdin.write(prefix + first + "\n\\echo READY\n")
        holder.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(holder.stdout, selectors.EVENT_READ)
            if not selector.select(20) or holder.stdout.readline().strip() != "READY":
                raise RuntimeError(f"{name}: holder did not reach transaction barrier")
        waiter = subprocess.Popen(
            self.command(app=name + "-waiter"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env,
        )
        self.children.append(waiter)
        waiter.stdin.write(prefix + second + "COMMIT;\n")
        waiter.stdin.close()
        waiter.stdin = None
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            blocked = self.sql(
                name + "-overlap",
                f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{name}-waiter' AND cardinality(pg_blocking_pids(pid))>0;",
            )
            if blocked == "1":
                break
            if waiter.poll() is not None:
                raise RuntimeError(
                    f"{name}: contender exited without observed lock contention"
                )
            time.sleep(0.05)
        else:
            raise RuntimeError(f"{name}: no lock overlap observed")
        out, err = holder.communicate("COMMIT;\n", timeout=20)
        if holder.returncode:
            raise RuntimeError(f"{name}: holder failed: {err}")
        out2, err2 = waiter.communicate(timeout=20)
        (self.evidence / f"{name}.log").write_text(
            (out + err + out2 + err2).replace(self.password, "[REDACTED]")
        )
        if loser:
            assert waiter.returncode != 0 and re.search(
                rf"ERROR:\s+{loser}:", err2
            ), name
        else:
            assert waiter.returncode == 0, name
        print(f"PASS {name}: overlapping sessions, expected outcome", flush=True)

    def cases(self):
        """Exercise stored count, uniqueness, sequence and offer revision invariants."""
        for isolation, state in [
            ("READ COMMITTED", "23514"),
            ("REPEATABLE READ", "40001"),
        ]:
            ids = self.seed()
            self.race(
                "last-image-" + isolation.replace(" ", "-"),
                f"DELETE FROM listings.images WHERE id='{ids['images'][0]}';",
                f"DELETE FROM listings.images WHERE id='{ids['images'][1]}';",
                state,
                isolation,
            )
            assert (
                self.sql(
                    "image-count",
                    f"SELECT count(*) FROM listings.images WHERE listing_id='{ids['item']}';",
                )
                == "1"
            )
        ids = self.seed(image_count=7)
        self.race(
            "image-upper-bound",
            self.image(ids, str(uuid.uuid4()), 7),
            self.image(ids, str(uuid.uuid4()), 8),
            "23514",
        )
        assert (
            self.sql(
                "image-upper-count",
                f"SELECT count(*) FROM listings.images WHERE listing_id='{ids['item']}';",
            )
            == "8"
        )
        ids = self.seed(thread=False)
        self.race(
            "unique-pair",
            self.thread(ids, ids["thread"]),
            self.thread(ids, str(uuid.uuid4())),
            "23505",
        )
        assert (
            self.sql(
                "pair-count",
                f"SELECT count(*) FROM conversations.threads WHERE listing_id='{ids['item']}';",
            )
            == "1"
        )
        ids = self.seed(thread=False)
        request = str(uuid.uuid4())
        self.sql(
            "wanted-seed",
            f"INSERT INTO search.wanted_requests(id,author_id,title,description,category_id,status) SELECT '{request}','{ids['seller']}','Synthetic request','Controlled fixture',id,'open' FROM listings.categories WHERE code='books';",
        )
        wanted = ids | {"item": request}
        self.race(
            "unique-wanted-pair",
            self.thread(wanted, ids["thread"]).replace(
                "listing_id", "wanted_request_id"
            ),
            self.thread(wanted, str(uuid.uuid4())).replace(
                "listing_id", "wanted_request_id"
            ),
            "23505",
        )
        assert (
            self.sql(
                "wanted-pair-count",
                f"SELECT count(*) FROM conversations.threads WHERE wanted_request_id='{request}';",
            )
            == "1"
        )
        ids = self.seed()
        self.race("entry-sequence", self.entry(ids)[1], self.entry(ids)[1])
        assert (
            self.sql(
                "sequence-head",
                f"SELECT string_agg(sequence::text,',' ORDER BY sequence) FROM conversations.entries WHERE conversation_id='{ids['thread']}'; SELECT next_sequence FROM conversations.threads WHERE id='{ids['thread']}';",
            )
            == "1,2\n3"
        )
        entry, text = self.entry(ids, "offer")
        self.sql(
            "offer-seed",
            f"BEGIN;{text} INSERT INTO conversations.offers(id,conversation_id,buyer_id,current_revision,next_revision) VALUES ('{ids['offer']}','{ids['thread']}','{ids['buyer']}',1,2); INSERT INTO conversations.offer_revisions(offer_id,revision,entry_id,amount_paise,status) VALUES ('{ids['offer']}',1,'{entry}',100,'submitted'); COMMIT;",
        )
        updates = []
        for amount in (200, 300):
            entry, text = self.entry(ids, "offer")
            updates.append(
                text
                + f"UPDATE conversations.offers SET current_revision=2,next_revision=3 WHERE id='{ids['offer']}'; INSERT INTO conversations.offer_revisions(offer_id,revision,entry_id,amount_paise,status) VALUES ('{ids['offer']}',2,'{entry}',{amount},'submitted');"
            )
        # The second append is rejected by the revision primary key; the
        # transaction must also roll back its allocated entry sequence.
        self.race("offer-revision", *updates, loser="23505")
        assert (
            self.sql(
                "offer-current",
                f"SELECT current_revision,next_revision FROM conversations.offers WHERE id='{ids['offer']}'; SELECT count(*) FROM conversations.offer_revisions WHERE offer_id='{ids['offer']}';",
            )
            == "2|3\n2"
        )

        assert (
            self.sql(
                "offer-entry-rollback",
                f"SELECT next_sequence FROM conversations.threads WHERE id='{ids['thread']}'; SELECT count(*) FROM conversations.entries WHERE conversation_id='{ids['thread']}';",
            )
            == "5\n4"
        )

    def plans(self):
        """Record natural plans and prove index eligibility, not workload performance.

        Tiny fixtures may correctly select sequential scans. Disabling those
        scans is a separate diagnostic and never counted as production plan evidence.
        """
        ids = self.seed()
        queries = {
            "owner": f"SELECT id FROM listings.sale_listings WHERE owner_id='{ids['seller']}' ORDER BY created_at DESC,id DESC LIMIT 20",
            "images": f"SELECT id FROM listings.images WHERE listing_id='{ids['item']}'",
            "entries": f"SELECT sequence FROM conversations.entries WHERE conversation_id='{ids['thread']}' AND sequence>0 ORDER BY sequence LIMIT 20",
            "search": "SELECT id FROM listings.sale_listings WHERE search_vector @@ plainto_tsquery('english','books')",
            "notification": "SELECT id FROM conversations.notification_intents WHERE state='pending' AND due_at<CURRENT_TIMESTAMP ORDER BY due_at,id LIMIT 20",
        }

        def indexes(node):
            """Collect only index names recursively from PostgreSQL JSON plans."""
            return ([node["Index Name"]] if "Index Name" in node else []) + [
                i for child in node.get("Plans", []) for i in indexes(child)
            ]

        for name, query in queries.items():
            self.sql("plan-natural-" + name, "EXPLAIN (FORMAT JSON) " + query)
            plan = self.sql(
                "plan-index-" + name,
                "SET enable_seqscan=off; EXPLAIN (FORMAT JSON) " + query,
            )
            assert indexes(json.loads(plan)[0]["Plan"]), name
            print(
                f"PASS {name}: natural plan recorded, index eligibility verified",
                flush=True,
            )

    def close(self):
        """Terminate unfinished clients and stop the owned service; retain test data."""
        for child in self.children:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=10)
        self.run("stop", ["bash", "database/local-db.sh", "stop"])


def main():
    """Run this explicit integration check without joining normal Python pytest."""
    checks = Checks()
    print(f"Evidence: {checks.evidence}; database: {checks.db}", flush=True)
    try:
        checks.start()
        checks.cases()
        checks.plans()
    finally:
        checks.close()


if __name__ == "__main__":
    main()
