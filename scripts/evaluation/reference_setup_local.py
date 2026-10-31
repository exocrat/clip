"""Explicit native PG18.6 setup/permission rehearsal; never AWS or existing data.

Own a fresh Unix-only cluster via the existing pinned native harness. Compare the
prepared migration runner with canonical dbmate, then exercise the real bulk SQL
under an actual restricted login. Planned media keys are not S3 acceptance.
"""

import argparse
import asyncio
from datetime import datetime, UTC, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import re
import traceback

import psycopg

from data.generators import reference, files
from data.generators.reference_rows import insert_rows, validate_rows
from scripts.evaluation.reference_local import OwnedCluster
from scripts.evaluation import reference_database_setup as setup
from scripts.evaluation import reference_load_access as load_access
from psycopg.conninfo import conninfo_to_dict
from scripts.evaluation.reference_vector_access import VectorAccess
from scripts.evaluation.reference_vector_local import run as run_vectors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--local-rehearsal", action="store_true", required=True)
    parser.add_argument(
        "--credentials",
        action="store_true",
        help="Also exercise one-window access with real native SCRAM authentication",
    )
    parser.add_argument(
        "--vectors",
        action="store_true",
        help="Also verify a dedicated vector producer with actual pinned model/worker",
    )
    args = parser.parse_args(argv)
    if args.vectors and not args.credentials:
        parser.error("--vectors requires --credentials")
    cluster = OwnedCluster()
    access_window = None
    vector_access = None
    native_password = None
    report = {
        "state": "started",
        "mode": "owned native permission rehearsal; not cloud/media acceptance",
        "events": [],
    }
    options = " ".join(f"-c {k}={v}" for k, v in setup.LOGGING.items())
    connect = lambda database, role=setup.ADMIN, password=None: psycopg.connect(
        host=str(cluster.socket),
        port=55438,
        dbname=database,
        user=role,
        password=password,
        autocommit=True,
        connect_timeout=3,
        options=options if role == setup.ADMIN else "",
    )

    def record(**data):
        report["events"].append(data)
        (cluster.root / "setup-result.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )

    def require(condition):
        if not condition:
            raise RuntimeError("native_rehearsal_check_failed")

    try:
        cluster.start()  # Existing canonical dbmate baseline, private owned cluster.
        with psycopg.connect(
            host=str(cluster.socket),
            port=55438,
            dbname="postgres",
            user="clip_native_test",
            autocommit=True,
        ) as bootstrap:
            bootstrap.execute(
                "ALTER ROLE clip_next06_loader RENAME TO clip_baseline_owner"
            )
            bootstrap.execute(
                "CREATE ROLE clip_test_admin LOGIN CREATEDB CREATEROLE NOINHERIT"
            )
            bootstrap.execute(
                "GRANT SET ON PARAMETER "
                + ",".join(setup.LOGGING)
                + " TO clip_test_admin"
            )
            bootstrap.execute("CREATE DATABASE clip_test OWNER clip_test_admin")
            # Test unsafe PUBLIC access before repairing only this new local fixture.
        bundle = files._read_json(
            files._run_path("next06-transfer-42-20261030-a") / "dataset.json"
        )
        reference.validate_reference(
            bundle, image_root=Path("/Users/mohitmahapatra/Desktop/clip-dataset-images")
        )
        with connect("clip_test") as control:
            try:
                setup.prepare(
                    control,
                    lambda: connect(setup.DATABASE),
                    bundle["manifest"]["source_binding"],
                    owned_socket=cluster.socket,
                    record=record,
                )
            except setup.SetupRefused as error:
                require(str(error) == "other_application_database_public_connect")
            else:
                raise RuntimeError("unsafe_public_access_not_refused")
            require(
                control.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", (setup.LOADER,)
                ).fetchone()
                is None
            )
        with psycopg.connect(
            host=str(cluster.socket),
            port=55438,
            dbname="postgres",
            user="clip_native_test",
            autocommit=True,
        ) as bootstrap:
            bootstrap.execute("REVOKE ALL ON DATABASE clip_test FROM PUBLIC")
            bootstrap.execute(
                "REVOKE ALL ON DATABASE clip_test_next06_reference FROM PUBLIC"
            )
        with connect("clip_test") as control:
            result = setup.prepare(
                control,
                lambda: connect(setup.DATABASE),
                bundle["manifest"]["source_binding"],
                owned_socket=cluster.socket,
                record=record,
            )
            require(result["state"] == "isolated_database_prepared_roles_inactive")
            try:
                setup.prepare(
                    control,
                    lambda: connect(setup.DATABASE),
                    bundle["manifest"]["source_binding"],
                    owned_socket=cluster.socket,
                    record=record,
                )
            except setup.SetupRefused as error:
                require(str(error) == "existing_target_or_role_refused")
            else:
                raise RuntimeError("existing_target_not_refused")

        def dump(database):
            content = subprocess.check_output(
                [
                    str(cluster.pg / "pg_dump"),
                    "-h",
                    str(cluster.socket),
                    "-p",
                    "55438",
                    "-U",
                    "clip_native_test",
                    "-d",
                    database,
                    "--schema-only",
                    "--no-owner",
                    "--no-privileges",
                    "--no-comments",
                ],
                env=cluster.env,
                timeout=30,
                text=True,
            )
            return "\n".join(
                line
                for line in content.splitlines()
                if not line.startswith(("\\restrict ", "\\unrestrict "))
            )

        baseline = dump("clip_test_next06_reference")
        actual = dump(setup.DATABASE)
        (cluster.root / "dbmate-schema.sql").write_text(baseline)
        (cluster.root / "prepared-schema.sql").write_text(actual)
        require(baseline == actual)
        record(
            stage="schema_identical_to_canonical_dbmate",
            sha256=hashlib.sha256(actual.encode()).hexdigest(),
        )
        if args.credentials:
            hba = cluster.cluster / "pg_hba.conf"
            hba.write_text(
                "local all clip_next06_loader scram-sha-256\nlocal all clip_next06_embeddings scram-sha-256\n"
                + hba.read_text()
            )
            cluster.run(
                cluster.pg / "pg_ctl",
                ["-D", str(cluster.cluster), "reload"],
                "reload.log",
            )
            access_window = load_access.WindowAccess()
            with connect(setup.DATABASE) as admin:
                native_secret = access_window.activate(
                    admin,
                    expires=datetime.now(UTC) + timedelta(minutes=30),
                    record=record,
                    owned_socket=cluster.socket,
                )
            native_password = conninfo_to_dict(native_secret)["password"]
            try:
                with connect(setup.DATABASE, setup.LOADER, "synthetic-wrong-password"):
                    pass
            except psycopg.OperationalError:
                pass
            else:
                raise RuntimeError("incorrect_native_password_not_refused")
            record(stage="native_wrong_scram_password_refused")
        else:
            with connect(setup.DATABASE) as admin:
                # Only this owned local role is activated; cloud setup never does this.
                admin.execute(f"ALTER ROLE {setup.LOADER} LOGIN")
        with connect(setup.DATABASE, setup.LOADER, native_password) as loader:
            require(
                loader.execute("SELECT current_user,session_user").fetchone()
                == (setup.LOADER, setup.LOADER)
            )
            validation = insert_rows(
                loader,
                bundle,
                object_key_for=lambda upload: f"id01/next06-reference-42-v1/{upload}",
                audit=datetime.now(UTC),
            )
            denied = [
                "CREATE TABLE public.unapproved(id integer)",
                "ALTER TABLE identity.users ADD COLUMN unapproved integer",
                "TRUNCATE identity.users",
                "DELETE FROM listings.images",
                "UPDATE listings.categories SET active=false",
                "SELECT 1 FROM conversations.entries LIMIT 1",
                "CREATE ROLE unapproved",
                "SET ROLE clip_test_admin",
            ]
            for statement in denied:
                try:
                    loader.execute(statement)
                except psycopg.errors.InsufficientPrivilege:
                    pass
                else:
                    raise RuntimeError("unintended_privilege_allowed")
            require(
                loader.execute(
                    "SELECT has_database_privilege(current_user,'clip_test','CONNECT'),has_database_privilege(current_user,current_database(),'TEMP')"
                ).fetchone()
                == (False, False)
            )
        with connect(setup.DATABASE) as admin:
            require(
                admin.execute(
                    "SELECT rolcanlogin FROM pg_roles WHERE rolname=%s",
                    (setup.RUNTIME,),
                ).fetchone()
                == (False,)
            )
            require(
                admin.execute(
                    "SELECT has_database_privilege(%s,current_database(),'CONNECT')",
                    (setup.RUNTIME,),
                ).fetchone()
                == (False,)
            )
        if access_window is not None:
            with connect(setup.DATABASE) as admin:
                access_window.close(admin, record=record, owned_socket=cluster.socket)
            try:
                with connect(setup.DATABASE, setup.LOADER, native_password):
                    pass
            except psycopg.OperationalError:
                pass
            else:
                raise RuntimeError("disabled_native_login_not_refused")
            with psycopg.connect(
                host=str(cluster.socket),
                port=55438,
                dbname="postgres",
                user="clip_native_test",
                autocommit=True,
            ) as bootstrap:
                require(
                    bootstrap.execute(
                        "SELECT rolpassword IS NULL FROM pg_authid WHERE rolname=%s",
                        (setup.LOADER,),
                    ).fetchone()
                    == (True,)
                )
            record(stage="native_login_disabled_and_password_null_verified")
            report["credential_lifecycle"] = (
                "Real native SCRAM: wrong password refused, generated password accepted, load passed, NOLOGIN and NULL verifier verified, old password refused"
            )
            del native_secret, native_password
        if args.vectors:
            vector_access = VectorAccess()
            with connect(setup.DATABASE) as admin:
                vector_secret = vector_access.activate(
                    admin,
                    expires=datetime.now(UTC) + timedelta(minutes=30),
                    record=record,
                    owned_socket=cluster.socket,
                )
            vector_password = conninfo_to_dict(vector_secret)["password"]

            async def bounded_vectors():
                async with asyncio.timeout(600):
                    return await run_vectors(cluster, vector_password, record=record)

            report["vector_result"] = asyncio.run(bounded_vectors())
            with connect(setup.DATABASE) as admin:
                vector_access.close(admin, record=record, owned_socket=cluster.socket)
                after = validate_rows(
                    admin,
                    bundle,
                    object_key_for=lambda upload: f"id01/next06-reference-42-v1/{upload}",
                )
                require(after == validation)
            try:
                with connect(setup.DATABASE, "clip_next06_embeddings", vector_password):
                    pass
            except psycopg.OperationalError:
                pass
            else:
                raise RuntimeError("revoked_vector_password_not_refused")
            report["vector_access_closed"] = True
            del vector_secret, vector_password
        report.update(
            state="passed",
            setup=result,
            sql_validation=validation,
            negative_permission_checks=len(denied),
            cloud_calls=0,
            media_objects_uploaded=0,
            notes="Native-only loader LOGIN enabled to prove real privileges; cloud plan retains both NOLOGIN. Model proof is recorded only when --vectors is explicitly selected. Real Identity session/S3/cloud runtime acceptance remains pending.",
        )
    except Exception as error:
        report.update(state="failed", failure_type=type(error).__name__)
        report["failure_sqlstate"] = getattr(error, "sqlstate", None)
        report["failure_frames"] = [
            {"function": f.name, "line": f.lineno}
            for f in traceback.extract_tb(error.__traceback__)
        ]
        primary = getattr(getattr(error, "diag", None), "message_primary", "") or ""
        if re.fullmatch(
            r"permission denied for (?:schema|table|relation|sequence) [a-z_]+", primary
        ):
            report["permission_diagnostic"] = primary
        if isinstance(error, setup.SetupRefused):
            report["refusal_code"] = str(error)
    finally:
        if (
            vector_access is not None
            and vector_access.attempted
            and not vector_access.closed
        ):
            try:
                with connect(setup.DATABASE) as admin:
                    vector_access.close(
                        admin, record=record, owned_socket=cluster.socket
                    )
            except Exception as error:
                report["vector_cleanup_failure_type"] = type(error).__name__
        if (
            access_window is not None
            and access_window.attempted
            and not access_window.closed
        ):
            try:
                with connect(setup.DATABASE) as admin:
                    access_window.close(
                        admin, record=record, owned_socket=cluster.socket
                    )
            except Exception as error:
                report["access_cleanup_failure_type"] = type(error).__name__
        try:
            cluster.stop()
            report["owned_cluster_stopped"] = not cluster.started
        except Exception as error:
            report.update(
                owned_cluster_stopped=False, stop_failure_type=type(error).__name__
            )
        (cluster.root / "setup-result.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(
            json.dumps(
                {
                    "state": report["state"],
                    "owned_cluster_stopped": report.get("owned_cluster_stopped"),
                    "evidence": str(cluster.root / "setup-result.json"),
                }
            )
        )
    return (
        0 if report["state"] == "passed" and report.get("owned_cluster_stopped") else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
