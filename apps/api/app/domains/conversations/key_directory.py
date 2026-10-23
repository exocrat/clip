"""Transactional storage of public SDK bundles and one-time public prekeys."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection, Error as PsycopgError
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool, PoolTimeout
from pydantic import ValidationError

from app.contracts.domain_types import (
    KeyBundle,
    MemberKeyBundles,
    MemberPreKeyBundle,
    OwnPreKeyInventory,
    PreKeyBundleRequest,
    PublicKeyBundleRequest,
    PublicKeyBundleView,
    PublicPreKeyBatchRequest,
    PublicPreKeyBatchView,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError


class PostgresKeyDirectory:
    """Expose public material only; private identities never cross this boundary.

    Operation locks protect exact retry results. Separate account locks serialize
    registration, publication and reservation for the same bundle owner. All
    mutations and their durable retry records commit together.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _conflict() -> PublicError:
        return PublicError(ERRORS[409], (FieldError("body", "conflict"),))

    @asynccontextmanager
    async def _transaction(
        self, caller: CallerContext
    ) -> AsyncIterator[AsyncConnection[Any]]:
        """Check trusted session expiry and hide storage/key decoding diagnostics."""
        caller.require_current()
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    yield connection
        except PsycopgError, PoolTimeout, ValidationError, ValueError:
            raise PublicError(ERRORS[503]) from None

    @staticmethod
    async def _lock(connection: AsyncConnection[Any], name: str) -> None:
        """Serialize only this operation/account, without querying Identity tables."""
        await connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (name,)
        )

    async def _replay(
        self,
        connection: AsyncConnection[Any],
        caller: CallerContext,
        operation_id: UUID,
        request: dict[str, Any],
    ) -> dict[str, Any] | None:
        """One caller/UUID namespace covers registration, batches and reservations."""
        await self._lock(connection, f"key-operation:{caller.user_id}:{operation_id}")
        cursor = await connection.execute(
            "SELECT request, result FROM conversations.key_directory_operations "
            "WHERE user_id = %s AND operation_id = %s",
            (caller.user_id, operation_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        if row[0] != request:
            raise self._conflict()
        return dict(row[1])

    @staticmethod
    async def _save(
        connection: AsyncConnection[Any],
        caller: CallerContext,
        operation_id: UUID,
        request: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Persist only public request/result data in the mutation transaction."""
        await connection.execute(
            "INSERT INTO conversations.key_directory_operations "
            "(user_id, operation_id, request, result) VALUES (%s, %s, %s, %s)",
            (caller.user_id, operation_id, Jsonb(request), Jsonb(result)),
        )

    @staticmethod
    async def _active(
        connection: AsyncConnection[Any], user_id: UUID
    ) -> tuple[Any, ...]:
        cursor = await connection.execute(
            "SELECT id, version, public_key_material FROM conversations.public_key_versions "
            "WHERE user_id = %s AND retired_at IS NULL",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise PostgresKeyDirectory._conflict()
        return tuple(row)

    @staticmethod
    def _decode(material: Any) -> KeyBundle:
        """Refuse partial/legacy/incompatible bundles rather than misrepresenting keys."""
        bundle = KeyBundle.model_validate_json(bytes(material))
        if (
            bundle.protocol_id != "open-e2ee-signal"
            or bundle.protocol_version != "13.0.0"
        ):
            raise PostgresKeyDirectory._conflict()
        return bundle

    @staticmethod
    async def _peer(
        connection: AsyncConnection[Any], caller: CallerContext, conversation_id: UUID
    ) -> UUID:
        """Derive the peer from a member-scoped thread; never accept a browser peer ID."""
        cursor = await connection.execute(
            "SELECT CASE WHEN thread.initiator_id = member.user_id "
            "THEN thread.counterparty_id ELSE thread.initiator_id END "
            "FROM conversations.threads AS thread JOIN conversations.members AS member "
            "ON member.conversation_id = thread.id "
            "WHERE thread.id = %s AND member.user_id = %s",
            (conversation_id, caller.user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise PublicError(ERRORS[404])
        return UUID(str(row[0]))

    async def read_own_key(self, caller: CallerContext) -> KeyBundle | None:
        """Distinguish first registration from lost browser keys without a thread.

        Null means no public version has ever existed. A retired latest version,
        malformed bundle or inconsistent owner/version must never look like a
        fresh account: callers fail closed instead of replacing a lost identity.
        The account lock gives a coherent read against concurrent registration.
        """
        async with self._transaction(caller) as connection:
            await self._lock(connection, f"key-account:{caller.user_id}")
            cursor = await connection.execute(
                "SELECT version, protocol_id, public_key_material, retired_at "
                "FROM conversations.public_key_versions WHERE user_id = %s "
                "ORDER BY version DESC LIMIT 1",
                (caller.user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                # Durable registration evidence also survives missing bundle rows.
                # Missing storage must not become permission to replace an identity.
                cursor = await connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM conversations.key_directory_operations "
                    "WHERE user_id = %s AND request->>'kind' = 'register')",
                    (caller.user_id,),
                )
                history = await cursor.fetchone()
                if history is None:
                    raise PublicError(ERRORS[503])
                if history[0]:
                    raise self._conflict()
                return None
            if row[3] is not None:
                raise self._conflict()
            bundle = self._decode(row[2])
            if (
                bundle.user_id != caller.user_id
                or bundle.key_version != row[0]
                or bundle.protocol_id != row[1]
            ):
                raise PublicError(ERRORS[503])
            return bundle

    async def register_own_key(
        self, caller: CallerContext, payload: PublicKeyBundleRequest
    ) -> PublicKeyBundleView:
        """Allocate increasing own versions, retiring the active public bundle atomically."""
        if (
            payload.protocol_id != "open-e2ee-signal"
            or payload.protocol_version != "13.0.0"
        ):
            raise PublicError(
                ERRORS[422], (FieldError("body", "unsupported_protocol"),)
            )
        request = {"kind": "register", "body": payload.model_dump(mode="json")}
        async with self._transaction(caller) as connection:
            replay = await self._replay(
                connection, caller, payload.operation_id, request
            )
            if replay is not None:
                return PublicKeyBundleView.model_validate(replay)
            await self._lock(connection, f"key-account:{caller.user_id}")
            cursor = await connection.execute(
                "SELECT coalesce(max(version), 0) + 1 FROM conversations.public_key_versions WHERE user_id = %s",
                (caller.user_id,),
            )
            row = await cursor.fetchone()
            assert row is not None
            version = row[0]
            bundle = KeyBundle(
                user_id=caller.user_id,
                key_version=version,
                **payload.model_dump(exclude={"operation_id"}),
            )
            await connection.execute(
                "UPDATE conversations.public_key_versions SET retired_at = clock_timestamp() "
                "WHERE user_id = %s AND retired_at IS NULL",
                (caller.user_id,),
            )
            await connection.execute(
                "INSERT INTO conversations.public_key_versions "
                "(id, user_id, version, public_key_material, protocol_id) VALUES (%s, %s, %s, %s, %s)",
                (
                    uuid4(),
                    caller.user_id,
                    version,
                    bundle.model_dump_json().encode(),
                    payload.protocol_id,
                ),
            )
            result = PublicKeyBundleView(
                user_id=caller.user_id,
                protocol_id=payload.protocol_id,
                protocol_version=payload.protocol_version,
                key_version=version,
            )
            await self._save(
                connection,
                caller,
                payload.operation_id,
                request,
                result.model_dump(mode="json"),
            )
            return result

    async def read_member_keys(
        self, caller: CallerContext, conversation_id: UUID
    ) -> MemberKeyBundles:
        """Return both active bundles plus only historical versions referenced in this thread."""
        async with self._transaction(caller) as connection:
            peer = await self._peer(connection, caller, conversation_id)
            # Keep active/history selection coherent with either member rotating.
            for user_id in sorted((caller.user_id, peer)):
                await self._lock(connection, f"key-account:{user_id}")
            cursor = await connection.execute(
                "SELECT key.public_key_material FROM conversations.public_key_versions AS key "
                "WHERE key.user_id IN (%s, %s) AND (key.retired_at IS NULL OR EXISTS "
                "(SELECT 1 FROM conversations.encrypted_payloads AS payload "
                "JOIN conversations.entries AS entry ON entry.id = payload.entry_id "
                "WHERE entry.conversation_id = %s AND entry.content_deleted_at IS NULL "
                "AND key.id IN (payload.sender_key_version_id, payload.recipient_key_version_id))) "
                "ORDER BY key.user_id, key.version",
                (caller.user_id, peer, conversation_id),
            )
            bundles = [self._decode(row[0]) for row in await cursor.fetchall()]
            for user_id in (caller.user_id, peer):
                await self._active(connection, user_id)
            return MemberKeyBundles(members=bundles)

    @staticmethod
    async def _inventory(
        connection: AsyncConnection[Any], bundle_id: UUID, version: int
    ) -> OwnPreKeyInventory:
        cursor = await connection.execute(
            "SELECT count(*) FILTER (WHERE key_type = 'ecPreKey'), "
            "count(*) FILTER (WHERE key_type = 'kemOneTimePreKey') "
            "FROM conversations.public_prekeys WHERE bundle_id = %s AND NOT consumed",
            (bundle_id,),
        )
        row = await cursor.fetchone()
        assert row is not None
        return OwnPreKeyInventory(
            key_version=version, ec_one_time_count=row[0], kem_one_time_count=row[1]
        )

    async def read_own_inventory(self, caller: CallerContext) -> OwnPreKeyInventory:
        """Report own active counts only; serialize with replacement and reservation."""
        async with self._transaction(caller) as connection:
            await self._lock(connection, f"key-account:{caller.user_id}")
            key = await self._active(connection, caller.user_id)
            return await self._inventory(connection, key[0], key[1])

    async def publish_own_prekeys(
        self, caller: CallerContext, payload: PublicPreKeyBatchRequest
    ) -> PublicPreKeyBatchView:
        """Publish an all-or-none active-version batch; consumed IDs cannot be reused."""
        request = {"kind": "publish", "body": payload.model_dump(mode="json")}
        async with self._transaction(caller) as connection:
            replay = await self._replay(
                connection, caller, payload.operation_id, request
            )
            if replay is not None:
                return PublicPreKeyBatchView.model_validate(replay)
            await self._lock(connection, f"key-account:{caller.user_id}")
            key = await self._active(connection, caller.user_id)
            if key[1] != payload.key_version:
                raise self._conflict()
            for prekey in payload.prekeys:
                cursor = await connection.execute(
                    "INSERT INTO conversations.public_prekeys (bundle_id, key_type, key_id, material) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING key_id",
                    (
                        key[0],
                        prekey.key_type,
                        prekey.key_id,
                        Jsonb(prekey.model_dump(mode="json")),
                    ),
                )
                if await cursor.fetchone() is None:
                    raise self._conflict()
            inventory = await self._inventory(connection, key[0], key[1])
            result = PublicPreKeyBatchView(**inventory.model_dump())
            await self._save(
                connection,
                caller,
                payload.operation_id,
                request,
                result.model_dump(mode="json"),
            )
            return result

    async def consume_member_prekeys(
        self, caller: CallerContext, conversation_id: UUID, payload: PreKeyBundleRequest
    ) -> MemberPreKeyBundle:
        """Reserve each peer OTP at most once; exact retries reuse their stored reservation."""
        request = {"kind": "consume", "conversation_id": str(conversation_id)}
        async with self._transaction(caller) as connection:
            peer = await self._peer(connection, caller, conversation_id)
            replay = await self._replay(
                connection, caller, payload.operation_id, request
            )
            if replay is not None:
                return MemberPreKeyBundle.model_validate(replay)
            await self._lock(connection, f"key-account:{peer}")
            key = await self._active(connection, peer)
            bundle = self._decode(key[2])
            reserved: dict[str, Any] = {}
            for key_type, field in (
                ("ecPreKey", "ec_one_time_prekey"),
                ("kemOneTimePreKey", "kem_one_time_prekey"),
            ):
                cursor = await connection.execute(
                    "UPDATE conversations.public_prekeys SET consumed = true "
                    "WHERE bundle_id = %s AND key_type = %s AND key_id = "
                    "(SELECT key_id FROM conversations.public_prekeys WHERE bundle_id = %s "
                    "AND key_type = %s AND NOT consumed ORDER BY key_id LIMIT 1) RETURNING material",
                    (key[0], key_type, key[0], key_type),
                )
                row = await cursor.fetchone()
                reserved[field] = row[0] if row else None
            result = MemberPreKeyBundle(
                key_bundle=bundle, registration_id=bundle.registration_id, **reserved
            )
            await self._save(
                connection,
                caller,
                payload.operation_id,
                request,
                result.model_dump(mode="json"),
            )
            return result
