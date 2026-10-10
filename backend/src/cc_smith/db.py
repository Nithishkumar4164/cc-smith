"""One database, a schema per module by table prefix. SQLite for the hackathon; the
same Core tables run on Postgres in M1."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)

from cc_smith.config import settings

metadata = MetaData()


def now() -> datetime:
    return datetime.now(UTC)


def _ts(name: str = "created_at") -> Column:
    return Column(name, DateTime(timezone=True), nullable=False, default=now)


# knowledge
card = Table(
    "card", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("issuer", String, nullable=False),
    # active | speculative_launch | closed_to_new
    Column("status", String, nullable=False, default="active"),
    Column("origin", String, nullable=False, default="seed"),
    _ts(),
)
evidence = Table(
    "evidence", metadata,
    Column("id", String, primary_key=True),  # sha256 of the extracted text
    Column("url", String, nullable=False, index=True),
    Column("final_url", String),
    Column("http_status", Integer),
    Column("content_type", String),
    Column("text_path", String),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
)
card_field = Table(
    "card_field", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("card_id", ForeignKey("card.id"), nullable=False, index=True),
    Column("field", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("value", JSON),
    Column("refs", JSON, nullable=False),  # [{url, quote, evidence_id}]
    # published | superseded | rolled_back
    Column("status", String, nullable=False),
    Column("as_of", DateTime(timezone=True), nullable=False),
    Column("effective_from", DateTime(timezone=True), nullable=False),
    _ts("published_at"),
    UniqueConstraint("card_id", "field", "version"),
)
speculation = Table(
    "speculation", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("card_id", ForeignKey("card.id"), nullable=False, index=True),
    Column("field", String, nullable=False),
    Column("value", JSON),
    Column("refs", JSON, nullable=False),
    # news | forum | ads | ai_mode | user_report | quote_check_failed | range_check_failed | not_official
    Column("origin", String, nullable=False),
    # open | promoted | contradicted | expired
    Column("status", String, nullable=False, default="open"),
    Column("reason", Text),
    _ts("opened_at"),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)
knowledge_event = Table(
    "knowledge_event", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("card_id", String, nullable=False, index=True),
    Column("field", String),
    # published | as_of_bumped | speculation_added | promoted | contradicted | expired | demoted | rolled_back | card_added
    Column("event_type", String, nullable=False),
    Column("tier", String),  # fact | speculation
    Column("old", JSON),
    Column("new", JSON),
    Column("refs", JSON),
    Column("large_change", Boolean, default=False),
    _ts(),
)

offer = Table(
    "offer", metadata,
    Column("id", String, primary_key=True),
    Column("issuer", String, nullable=False),
    Column("card_ids", JSON, nullable=False),  # ["*"] = every card from the issuer
    Column("merchant_key", String, index=True),
    Column("merchant_name", String),
    Column("title", String, nullable=False),
    # instant_discount | cashback | bonus_points | emi | ltf | fyf | joining_waiver | annual_waiver | other
    Column("kind", String, nullable=False),
    Column("pct_bp", Integer),
    Column("max_paise", Integer),
    Column("min_txn_paise", Integer),
    Column("flat_paise", Integer),
    Column("spend_condition_paise", Integer),
    Column("spend_window_days", Integer),
    Column("channel", String, nullable=False, default="any"),
    Column("valid_from", String),
    Column("valid_to", String),
    Column("refs", JSON, nullable=False),
    # fact | speculation
    Column("tier", String, nullable=False),
    Column("reason", Text),
    _ts("as_of"),
)

# users
app_user = Table("app_user", metadata, Column("id", String, primary_key=True), _ts())
profile = Table(
    "profile", metadata,
    Column("user_id", ForeignKey("app_user.id"), primary_key=True),
    Column("data", JSON, nullable=False),  # income band, score band, preferences, flags
    Column("updated_at", DateTime(timezone=True), nullable=False, default=now),
)
holding = Table(
    "holding", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", ForeignKey("app_user.id"), nullable=False, index=True),
    Column("card_id", ForeignKey("card.id"), nullable=False),
    Column("last4", String),
    Column("statement_day", Integer),
    Column("renewal_month", Integer),
    # standard | ltf | fyf | custom — the user's own card may be fee-free even when the product is not.
    Column("fee_status", String, nullable=False, default="standard"),
    Column("annual_fee_paise", Integer),  # custom: what the user pays a year, GST included
    Column("fyf_until", String),  # ISO date the free first year ends
    Column("credit_limit_paise", Integer),
    # Cards in one pool share a single limit (most banks share across your cards with them).
    Column("pool_id", String),
    Column("balance_paise", Integer),  # outstanding the user entered, as of balance_as_of
    Column("balance_as_of", DateTime(timezone=True)),
    UniqueConstraint("user_id", "card_id"),
)
credit_pool = Table(
    "credit_pool", metadata,
    Column("user_id", ForeignKey("app_user.id"), primary_key=True),
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("limit_paise", Integer, nullable=False),
)
card_payment = Table(
    "card_payment", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", ForeignKey("app_user.id"), nullable=False, index=True),
    Column("card_id", String, nullable=False),
    Column("amount_paise", Integer, nullable=False),
    Column("ts", DateTime(timezone=True), nullable=False, default=now),
)
spend = Table(
    "spend", metadata,
    Column("user_id", ForeignKey("app_user.id"), primary_key=True),
    Column("key", String, primary_key=True),  # category or merchant key
    Column("monthly_paise", Integer, nullable=False),
)

# ledger
txn = Table(
    "txn", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", ForeignKey("app_user.id"), nullable=False, index=True),
    Column("card_id", String, nullable=False),
    Column("amount_paise", Integer, nullable=False),
    Column("merchant_key", String),
    Column("merchant_name", String),
    Column("category", String, nullable=False),
    Column("channel", String, nullable=False),
    Column("reward_paise", Integer, nullable=False, default=0),
    Column("cap_use", JSON, nullable=False, default=dict),
    Column("source", String, nullable=False, default="checkout"),
    Column("idempotency_key", String, unique=True),
    Column("superseded_by", Integer),
    Column("ts", DateTime(timezone=True), nullable=False, default=now),
)

# signals
launch_candidate = Table(
    "launch_candidate", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("dedupe_key", String, unique=True, nullable=False),
    Column("name", String, nullable=False),
    Column("issuer", String),
    Column("card_id", String),
    # speculative | profiled | known | rejected
    Column("status", String, nullable=False),
    Column("refs", JSON, nullable=False),
    Column("summary", Text),
    _ts("first_seen"),
)

# notify
owner_alert = Table(
    "owner_alert", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_id", Integer, unique=True),
    Column("payload", JSON, nullable=False),
    _ts(),
)

# ops
outbox = Table(
    "outbox", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("topic", String, nullable=False, index=True),
    Column("key", String, nullable=False),
    Column("payload", JSON, nullable=False),
    # pending | done | dead
    Column("status", String, nullable=False, default="pending"),
    Column("attempts", Integer, nullable=False, default=0),
    Column("last_error", Text),
    _ts(),
)
serp_cache = Table(
    "serp_cache", metadata,
    Column("key", String, primary_key=True),
    Column("engine", String, nullable=False),
    Column("params", JSON, nullable=False),
    Column("response", JSON, nullable=False),
    Column("search_id", String),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
)
credit_ledger = Table(
    "credit_ledger", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("flow", String, nullable=False),
    Column("engine", String, nullable=False),
    Column("search_id", String),
    Column("cached", Boolean, nullable=False),
    _ts("ts"),
)
run_state = Table(
    "run_state", metadata,
    Column("job", String, primary_key=True),
    Column("last_started", DateTime(timezone=True)),
    Column("last_finished", DateTime(timezone=True)),
    Column("status", String),
    Column("detail", JSON),
)


def make_engine(url: str | None = None):
    url = url or settings.database_url
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(url)
    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _fk(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
    metadata.create_all(eng)
    _add_missing_columns(eng)
    return eng


def _add_missing_columns(eng) -> None:
    """create_all never alters existing tables; add nullable columns introduced later."""
    with eng.begin() as c:
        for t in (holding,):
            have = {r[1] for r in c.exec_driver_sql(f"PRAGMA table_info({t.name})")} if eng.url.get_backend_name() == "sqlite" else None
            for col in t.columns:
                if have is not None and have and col.name not in have and col.nullable:
                    c.exec_driver_sql(f"ALTER TABLE {t.name} ADD COLUMN {col.name} {col.type.compile(eng.dialect)}")


_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


# capture (statement upload, phone notification events, Gmail alerts, credit reports).
# Only outcomes and links to ledger rows are kept here: no raw text, files or passwords (DR-9).
capture_event = Table(
    "capture_event", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", ForeignKey("app_user.id"), nullable=False, index=True),
    # notification | gmail | statement
    Column("source", String, nullable=False),
    Column("idempotency_key", String, nullable=False, unique=True),  # sha256(source:event id)
    # recorded | duplicate | unmatched_card | ignored
    Column("outcome", String, nullable=False),
    Column("reason", String),
    Column("card_id", String),
    Column("txn_id", Integer),  # the ledger row this event recorded or was matched to
    Column("payment_id", Integer),  # card_payment row for a repayment
    _ts(),
)
capture_state = Table(
    "capture_state", metadata,
    Column("user_id", ForeignKey("app_user.id"), primary_key=True),
    Column("source", String, primary_key=True),
    Column("last_sync_at", DateTime(timezone=True)),
    Column("cursor", JSON),  # gmail: {"history_id": "..."}
    Column("detail", JSON),
)
# Gmail OAuth tokens, Fernet-encrypted at rest with settings.capture_token_key. M1 moves
# this to a per-user KMS data key so erasure can crypto-shred it (DR-9).
gmail_account = Table(
    "gmail_account", metadata,
    Column("user_id", ForeignKey("app_user.id"), primary_key=True),
    Column("token_enc", Text),
    Column("pending_state", String),
    Column("pending_verifier_enc", Text),
    Column("connected_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=now),
)
