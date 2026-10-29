"""Operator-only guarded development bootstrap; import/help never connects.

The caller owns approved cloud targeting and secret retrieval. No startup hook,
provider call, key/password rotation or automatic recovery is installed. Live
execution requires exact reviewed inputs and the existing runner's manifest gate.
"""

from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from psycopg import sql
from pydantic import SecretStr

from app.domains.identity import migration_runner as migrations
from app.domains.identity.database_setup import LOGGING
from app.domains.identity.runtime_database import APPEND_ONLY, TABLES
from app.domains.identity.temporary_challenges import Database

INVENTORY = ROOT / "docs/evaluation/identity/id-01-step-13/bootstrap-inventory.sql"
SCHEMAS = ("identity", "listings", "search", "conversations")
LOCK = (1129072976, 12)


@dataclass
class BootstrapFailure(Exception):
    """Safe phase/commit receipt, without raw SQL, credentials or nested errors."""

    phase: str
    reset_committed: bool

    def __str__(self) -> str:
        return (
            f"Bootstrap stopped in {self.phase}; reset_committed={self.reset_committed}"
        )


def proposed_grants() -> dict[str, dict[str, list[str]]]:
    """Fixed proposed allowlist; embedding additions require affected-owner review.

    Preserve the historical ten-table marketplace grants. Invalidation adds only
    pipeline/chunk reads and generation select/insert/delete. No Conversations,
    Identity, pipeline/chunk writes or future-table defaults are granted to it.
    """
    identity = {}
    for name in sorted(TABLES):
        privileges = ["SELECT", "INSERT"]
        if name not in APPEND_ONLY:
            privileges += ["UPDATE"] + ([] if name == "users" else ["DELETE"])
        identity["identity." + name] = privileges
    identity["public.schema_migrations"] = ["SELECT"]
    marketplace = {
        "listings.categories": ["SELECT"],
        "listings.conditions": ["SELECT"],
        "listings.sale_listings": ["SELECT", "INSERT", "UPDATE"],
        "listings.images": ["SELECT", "INSERT", "UPDATE", "DELETE"],
        "listings.image_uploads": ["SELECT", "INSERT", "UPDATE", "DELETE"],
        "listings.create_command_results": ["SELECT", "INSERT", "UPDATE"],
        "listings.owner_command_results": ["SELECT", "INSERT", "DELETE"],
        "search.wanted_requests": ["SELECT", "INSERT", "UPDATE"],
        "search.wanted_command_results": ["SELECT", "INSERT", "UPDATE"],
        "search.saved_listings": ["SELECT", "INSERT", "DELETE"],
        "listings.embedding_pipelines": ["SELECT"],
        "listings.embedding_generations": ["SELECT", "INSERT", "DELETE"],
        "listings.embedding_chunks": ["SELECT"],
    }
    return {
        "clip_test_identity_app": identity,
        "clip_test_marketplace_app": marketplace,
    }


def _require(condition: bool) -> None:
    """Keep destructive safety gates active even with Python optimization enabled."""
    if not condition:
        raise ValueError("Bootstrap precondition rejected")


def _digest(value: Any) -> str:
    """Bind deterministic catalog rows to the exact reviewed drift baseline."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _target(c: Database, target: migrations.MigrationTarget) -> None:
    """Require fixed login, verified TLS and effective privacy defaults."""
    _require(c.autocommit and c.pgconn.ssl_in_use)
    _require(
        c.execute("SELECT current_database(),current_user,session_user").fetchone()
        == (target.database, target.admin, target.admin)
    )
    for name, value in LOGGING.items():
        _require(
            c.execute("SELECT current_setting(%s)", (name,)).fetchone() == (value,)
        )
    for name, allowed in (
        ("pgaudit.log", {None, "", "none"}),
        ("auto_explain.log_min_duration", {None, "", "-1"}),
    ):
        row = c.execute("SELECT current_setting(%s,true)", (name,)).fetchone()
        if row is None:
            raise ValueError("Missing privacy setting")
        _require(row[0] in allowed)


def _capture(
    c: Database, target: migrations.MigrationTarget, *, read_only: bool
) -> list[dict[str, Any]]:
    """Capture reviewed metadata within the caller's repeatable-read transaction.

    Reset verification explicitly expects read-write; ordinary inventory expects
    read-only. Only that predicate and isolated fixture target literals vary.
    The canonical read-only file is never edited or executed as reset SQL.
    """
    text = INVENTORY.read_text()
    begin = "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;"
    _require(text.count(begin) == 1 and text.endswith("ROLLBACK;\n"))
    text = text.replace(begin, "", 1).removesuffix("ROLLBACK;\n")
    if target.isolated:
        for old, new in (
            (
                "current_database() = 'clip_test'",
                "current_database() = 'clip_test_identity'",
            ),
            ("current_user = 'clip_test_admin'", "current_user = 'clip_identity_ci'"),
            ("session_user = 'clip_test_admin'", "session_user = 'clip_identity_ci'"),
        ):
            _require(text.count(old) == 1)
            text = text.replace(old, new)
    if not read_only:
        predicate = "current_setting('transaction_read_only') = 'on'"
        _require(text.count(predicate) == 1)
        text = text.replace(
            predicate, "current_setting('transaction_read_only') = 'off'"
        )
    cursor = c.execute(text, prepare=False)
    result = []
    while True:
        if cursor.description:
            columns = [column.name for column in cursor.description]
            rows = cursor.fetchall()
            _require(len(rows) <= 5000)
            result.append({"columns": columns, "rows": [list(row) for row in rows]})
        if not cursor.nextset():
            break
    return result


def _rows(snapshot: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    """Select one named result set from the pinned inventory collector."""
    item = next(item for item in snapshot if field in item["columns"])
    return [dict(zip(item["columns"], row)) for row in item["rows"]]


def _counts(c: Database, names: list[str]) -> dict[str, int]:
    """Count only reviewed project tables; never select individual app values."""
    result: dict[str, int] = {}
    for qualified in sorted(names):
        _require(
            re.fullmatch(
                r"(identity|listings|search|conversations)\.[a-z_]+", qualified
            )
            is not None
        )
        row = c.execute(
            sql.SQL("SELECT count(*) FROM {}").format(
                sql.Identifier(*qualified.split("."))
            )
        ).fetchone()
        if row is None:
            raise ValueError("Missing scalar count")
        result[qualified] = int(row[0])
    return result


def snapshot(c: Database, target: migrations.MigrationTarget) -> dict[str, Any]:
    """Explicit read-only baseline collector; this API cannot reset/grant."""
    _target(c, target)
    with c.transaction():
        c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        metadata = _capture(c, target, read_only=True)
        names = [
            row["object_schema"] + "." + row["relname"]
            for row in _rows(metadata, "object_acl")
            if row["relkind"] == "r" and row["object_schema"] in SCHEMAS
        ]
        counts = _counts(c, names)
    return {
        "catalogue_sha256": _digest(metadata),
        "counts": counts,
        "metadata": metadata,
    }


def _check_state(
    c: Database, metadata: list[dict[str, Any]], plan: dict[str, Any]
) -> None:
    """Refuse unreviewed drift, missing counts, clients or column privileges."""
    _require(_digest(metadata) == plan["expected_catalogue_sha256"])
    names = {
        row["object_schema"] + "." + row["relname"]
        for row in _rows(metadata, "object_acl")
        if row["relkind"] == "r" and row["object_schema"] in SCHEMAS
    }
    _require(len(names) == 37 and names == set(plan["expected_counts"]))
    _require(_counts(c, sorted(names)) == plan["expected_counts"])
    versions = [
        str(row[0])
        for row in c.execute(
            "SELECT version FROM public.schema_migrations ORDER BY version LIMIT 1001"
        )
    ]
    _require(versions == plan["expected_versions"])
    _require(_rows(metadata, "other_client_sessions")[0]["other_client_sessions"] == 0)
    _require(
        not _rows(metadata, "external_fk_schema")
        and not _rows(metadata, "event_trigger")
    )
    _require(
        all(
            not row["relrowsecurity"] and not row["relforcerowsecurity"]
            for row in _rows(metadata, "object_acl")
        )
    )
    _require(
        c.execute(
            """SELECT count(*) FROM pg_attribute a JOIN pg_class r ON r.oid=a.attrelid
        JOIN pg_namespace n ON n.oid=r.relnamespace WHERE a.attacl IS NOT NULL
        AND (n.nspname=ANY(%s) OR r.oid=to_regclass('public.schema_migrations'))""",
            (list(SCHEMAS),),
        ).fetchone()
        == (0,)
    )


def _drop_project(c: Database) -> None:
    """Only inside guarded reset transaction; no IF EXISTS or automatic adoption."""
    c.execute("DROP SCHEMA identity,listings,search,conversations CASCADE")
    c.execute("DROP TABLE public.schema_migrations RESTRICT")


def _restore_grants(c: Database, grants: dict[str, dict[str, list[str]]]) -> None:
    """Restore exact grants to retained roles; no role/database/secret changes."""
    for role, schemas in (
        ("clip_test_identity_app", ["identity", "public"]),
        ("clip_test_marketplace_app", ["listings", "search"]),
    ):
        c.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.SQL(",").join(map(sql.Identifier, schemas)), sql.Identifier(role)
            )
        )
        for table, privileges in grants[role].items():
            c.execute(
                sql.SQL("GRANT {} ON {} TO {}").format(
                    sql.SQL(",").join(map(sql.SQL, privileges)),
                    sql.Identifier(*table.split(".")),
                    sql.Identifier(role),
                )
            )


def bootstrap(
    connect: Callable[[], Database],
    password: SecretStr,
    target: migrations.MigrationTarget,
    *,
    plan: dict[str, Any],
    directory: Path,
    manifest: Path,
    ca: Path,
    image: str,
) -> dict[str, Any]:
    """Reset exact dev baseline, migrate fresh and restore reviewed grants.

    One dedicated connection holds the existing reentrant wrapper advisory lock
    across all phases. nullcontext lends it to the runner without closing it;
    the runner only uses its factory as a context manager (its legacy annotation
    is narrower). Existing runner and prefix guards remain unchanged.
    Reset commits before per-file migration commits. No failure auto-retries or
    restores/drops again; closing this owned connection releases all lock levels.
    """
    phase, committed = "package", False
    try:
        _require(
            plan["discard_confirmed"] is True and plan["grants"] == proposed_grants()
        )
        _require(
            hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
            == plan["inventory_sha256"]
        )
        _require(
            hashlib.sha256(manifest.read_bytes()).hexdigest() == plan["manifest_sha256"]
        )
        if target.isolated:
            _require(plan["isolated_rehearsal_only"] is True)
        else:
            _require(plan["isolated_rehearsal_only"] is False)
            _require(
                all(
                    plan[name] is True
                    for name in (
                        "live_ddl_approved",
                        "affected_owner_reviewed",
                        "independent_reviewed",
                        "dependency_closure_reviewed",
                    )
                )
            )
        _require(len(plan["expected_counts"]) == 37)
        _require(
            all(
                type(value) is int and value >= 0
                for value in plan["expected_counts"].values()
            )
        )
        migrations.validate_manifest(directory, manifest, image, target)
        _require(
            plan["expected_versions"]
            == [
                row["version"]
                for row in json.loads(manifest.read_text())["migrations"][:17]
            ]
        )
        with connect() as c:
            _target(c, target)
            phase = "lock"
            _require(
                c.execute("SELECT pg_try_advisory_lock(%s,%s)", LOCK).fetchone()
                == (True,)
            )
            phase = "baseline"
            before = snapshot(c, target)
            _require(before["catalogue_sha256"] == plan["expected_catalogue_sha256"])
            _require(before["counts"] == plan["expected_counts"])
            with c.transaction():
                c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE")
                c.execute("SET LOCAL lock_timeout='3s'")
                for table in [
                    "public.schema_migrations",
                    *sorted(plan["expected_counts"]),
                ]:
                    c.execute(
                        sql.SQL("LOCK TABLE {} IN ACCESS EXCLUSIVE MODE NOWAIT").format(
                            sql.Identifier(*table.split("."))
                        )
                    )
                current = _capture(c, target, read_only=False)
                _check_state(c, current, plan)
                phase = "reset"
                c.execute("SET LOCAL statement_timeout='30s'")
                _drop_project(c)
            committed = True
            phase = "migrate"
            borrowed: Callable[[], Any] = lambda: nullcontext(c)
            migrations.run_migrations(
                borrowed,
                password,
                target,
                directory=directory,
                manifest=manifest,
                ca=ca,
                image=image,
            )
            phase = "grants"
            with c.transaction():
                c.execute("SET TRANSACTION READ WRITE")
                c.execute("SET LOCAL statement_timeout='5s'")
                c.execute("SET LOCAL lock_timeout='3s'")
                _restore_grants(c, plan["grants"])
            phase = "verify"
            after = snapshot(c, target)
            for field in (
                "project_role",
                "logging_role",
                "member_role",
                "database_role",
            ):
                _require(
                    _rows(before["metadata"], field) == _rows(after["metadata"], field)
                )
            for role, tables in plan["grants"].items():
                observed: dict[str, set[str]] = {}
                for row in _rows(after["metadata"], "privilege_role"):
                    if row["privilege_role"] == role and row["allowed"]:
                        observed.setdefault(
                            row["nspname"] + "." + row["relname"], set()
                        ).add(row["privilege"])
                _require(
                    observed
                    == {table: set(privileges) for table, privileges in tables.items()}
                )
            _require(
                not any(
                    row["usage"]
                    for row in _rows(after["metadata"], "runtime_role")
                    if row["runtime_role"] == "clip_test_marketplace_app"
                    and row["access_schema"] in ("identity", "conversations")
                )
            )
            return {
                "reset_committed": True,
                "migrations": 23,
                "head": "20261027112205",
                "role_identity_preserved": True,
                "table_grants_verified": True,
                "real_login_acceptance": False,
            }
    except Exception:
        raise BootstrapFailure(phase, committed) from None


if __name__ == "__main__":
    print(__doc__)
    print("No execution CLI: call only through a reviewed explicit operator window.")
