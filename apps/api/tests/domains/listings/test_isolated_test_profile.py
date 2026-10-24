"""Guard the fixed caller and database target used by the cloud rehearsal."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domains.listings.isolated_test import (
    ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
    ISOLATED_TEST_SELLER_ID,
    IsolatedListingsTestIdentity,
    isolated_test_caller,
    require_isolated_test_database,
)


class _Cursor:
    def __init__(self, target):
        self.target = target

    async def fetchone(self):
        return self.target


class _Connection:
    def __init__(self, target):
        self.target = target

    async def execute(self, query):
        assert "current_database()" in query
        assert "rolsuper" in query
        assert "rolcreatedb" in query
        return _Cursor(self.target)


class _Pool:
    def __init__(self, target):
        self.target = target

    @asynccontextmanager
    async def connection(self):
        yield _Connection(self.target)


def test_test_identity_and_caller_accept_only_the_fixed_server_user():
    identity = IsolatedListingsTestIdentity()
    caller = isolated_test_caller()

    assert caller.user_id == ISOLATED_TEST_SELLER_ID
    assert caller.account_class == "regular"
    assert caller.valid_until > datetime.now(UTC)
    assert asyncio.run(identity.account_is_eligible(ISOLATED_TEST_SELLER_ID))
    assert not asyncio.run(identity.account_is_eligible(UUID(int=1)))


@pytest.mark.parametrize(
    "target",
    [
        {
            "database_name": "clip_test_listings",
            "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "is_superuser": False,
            "can_create_database": False,
            "can_create_role": False,
            "can_replicate": False,
            "can_bypass_row_security": False,
        },
        None,
        {
            "database_name": "clip_test",
            "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "is_superuser": False,
            "can_create_database": False,
            "can_create_role": False,
            "can_replicate": False,
            "can_bypass_row_security": False,
        },
        {
            "database_name": "clip_test_listings",
            "current_role": "suraj",
            "login_role": "suraj",
            "is_superuser": False,
            "can_create_database": False,
            "can_create_role": False,
            "can_replicate": False,
            "can_bypass_row_security": False,
        },
        {
            "database_name": "clip_test_listings",
            "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "is_superuser": True,
            "can_create_database": True,
            "can_create_role": True,
            "can_replicate": True,
            "can_bypass_row_security": True,
        },
        {
            "database_name": "clip_test_listings",
            "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "is_superuser": False,
            "can_create_database": True,
            "can_create_role": False,
            "can_replicate": False,
            "can_bypass_row_security": False,
        },
        {
            "database_name": "clip_test_listings",
            "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "is_superuser": False,
            "can_create_database": False,
            "can_create_role": True,
            "can_replicate": False,
            "can_bypass_row_security": False,
        },
        {
            "database_name": "clip_test_listings",
            "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "is_superuser": False,
            "can_create_database": False,
            "can_create_role": False,
            "can_replicate": True,
            "can_bypass_row_security": False,
        },
        {
            "database_name": "clip_test_listings",
            "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
            "is_superuser": False,
            "can_create_database": False,
            "can_create_role": False,
            "can_replicate": False,
            "can_bypass_row_security": True,
        },
    ],
    ids=[
        "approved-target",
        "missing-role",
        "shared-database",
        "wrong-login",
        "superuser",
        "createdb",
        "createrole",
        "replication",
        "bypassrls",
    ],
)
def test_database_guard_allows_only_dedicated_low_privilege_database_role(target):
    pool = _Pool(target)

    async def run():
        if (
            target
            and target["database_name"] == "clip_test_listings"
            and all(
                target[key] == value
                for key, value in {
                    "current_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
                    "login_role": ISOLATED_LISTINGS_TEST_DATABASE_ROLE,
                    "is_superuser": False,
                    "can_create_database": False,
                    "can_create_role": False,
                    "can_replicate": False,
                    "can_bypass_row_security": False,
                }.items()
            )
        ):
            await require_isolated_test_database(pool)
            return
        with pytest.raises(RuntimeError, match="target check failed"):
            await require_isolated_test_database(pool)

    asyncio.run(run())
