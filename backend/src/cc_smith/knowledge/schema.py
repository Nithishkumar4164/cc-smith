"""Card profile schema. Money is integer paise; percentage rates are basis points.

Every sourced element carries `src`: the official URL and the verbatim quote it was
extracted from. The quote check (knowledge.quotes) decides whether it is a fact.
"""

from typing import Literal

from pydantic import BaseModel, Field

Period = Literal[
    "statement_cycle",
    "calendar_month",
    "calendar_quarter",
    "statement_quarter",
    "anniversary_year",
    "calendar_year",
    "half_year",
]
Channel = Literal["online", "offline", "upi"]

PERIOD_MONTHS: dict[str, int] = {
    "statement_cycle": 1,
    "calendar_month": 1,
    "calendar_quarter": 3,
    "statement_quarter": 3,
    "anniversary_year": 12,
    "calendar_year": 12,
    "half_year": 6,
}


class Source(BaseModel):
    url: str
    quote: str


class Sourced(BaseModel):
    src: list[Source] = Field(min_length=1)


class Match(BaseModel):
    """Empty lists match anything. A rule matches when every non-empty list matches."""

    categories: list[str] = []
    merchants: list[str] = []
    channels: list[Channel] = []

    def specificity(self) -> int:
        return (2 if self.merchants else 0) + (1 if self.categories else 0)


class Rate(BaseModel):
    kind: Literal["pct", "per_spend"]
    bp: int | None = None
    points: int | None = None
    per_paise: int | None = None


class EarnRule(Sourced):
    id: str
    match: Match = Match()
    rate: Rate
    cap_ids: list[str] = []
    # A stacked rule earns on top of the best non-stacked rule (e.g. "5X" bonus over base).
    stacks: bool = False
    # Higher runs first among equally specific rules (spend tiers: first ₹1.5 lakh before the rest).
    priority: int = 0
    # User attributes the rule needs, e.g. "amazon_prime".
    requires: list[str] = []
    min_txn_paise: int | None = None
    note: str | None = None


class Cap(Sourced):
    id: str
    amount: int
    unit: Literal["paise", "points", "spend_paise"]
    period: Period
    # For spend caps: whether spend beyond the cap earns under the next applicable rule.
    spill: bool = True


class Exclusion(Sourced):
    categories: list[str] = []
    merchants: list[str] = []
    channels: list[Channel] = []
    except_merchants: list[str] = []
    # Empty = excluded from every rule; otherwise only from these rules.
    rule_ids: list[str] = []


class Fees(Sourced):
    joining_paise: int
    annual_paise: int
    waiver_spend_paise: int | None = None


class Currency(Sourced):
    kind: Literal["cashback", "points"]
    name: str
    # Value of one unit in paise, at the typical redemption route (B12: rank on typical).
    value_paise: int
    floor_paise: int | None = None


class Milestone(Sourced):
    spend_paise: int
    period: Period
    value_paise: int
    description: str


class Identity(Sourced):
    network: str | None = None
    upi_rupay: bool | None = None


class CardProfile(BaseModel):
    id: str
    name: str
    issuer: str
    identity: Identity | None = None
    fees: Fees | None = None
    currency: Currency | None = None
    earn_rules: list[EarnRule] = []
    caps: list[Cap] = []
    exclusions: list[Exclusion] = []
    min_txn_paise: int | None = None
    milestones: list[Milestone] = []
    min_txn_src: list[Source] = []

    def cap(self, cap_id: str) -> Cap:
        return next(c for c in self.caps if c.id == cap_id)

    def assessable(self) -> bool:
        return bool(self.earn_rules) and self.currency is not None


FIELDS = ("identity", "fees", "currency", "earn_rules", "caps", "exclusions", "min_txn", "milestones")
