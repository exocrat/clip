"""Install transaction-local SQL deadlines in one database round trip."""

IDENTITY_BOUNDS_SQL = "SELECT set_config('lock_timeout', '3s', true), set_config('statement_timeout', '5s', true)"
LISTING_READ_BOUNDS_SQL = "SELECT set_config('statement_timeout', '3s', true), set_config('lock_timeout', '1s', true)"

# Execute inside an existing transaction, before protected queries. The final
# true argument preserves SET LOCAL behavior: commit/rollback restores defaults.
# Keep this separate from the protected query so its statement timeout applies
# before parsing/executing that query, including any relation-lock wait.
