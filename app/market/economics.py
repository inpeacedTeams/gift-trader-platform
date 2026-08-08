"""What trading actually costs.

Every screen that shows profit has to subtract the same things: the venue's
cut of the sale and the gas spent moving the gift. When those numbers lived
in the arbitrage repository, other features copied them, and copies drift.
One module, one answer.

Nothing here is guessed per gift: these are published marketplace terms. A
venue we have no entry for falls back to the market standard rather than to
zero, because assuming a free sale is the expensive mistake.
"""

from decimal import Decimal

# Seller side fees, in percent. Buying costs the listed price.
DEFAULT_FEES: dict[str, Decimal] = {
    "tonnel": Decimal("5"),
    "getgems": Decimal("5"),
    "portals": Decimal("5"),
    "fragment": Decimal("5"),
    "mrkt": Decimal("5"),
}
# Used for venues not listed above, and for an unknown venue.
DEFAULT_SELL_FEE = Decimal("5")
# Network cost of a transfer, paid on the way in.
DEFAULT_GAS_TON = Decimal("0.1")


def sell_fee_percent(marketplace: str | None) -> Decimal:
    return DEFAULT_FEES.get((marketplace or "").lower(), DEFAULT_SELL_FEE)


def net_proceeds(marketplace: str | None, price: Decimal) -> Decimal:
    """What the seller receives for a sale at this price on this venue."""
    return price - price * sell_fee_percent(marketplace) / Decimal(100)
