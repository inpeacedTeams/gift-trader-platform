"""Message text for portfolio rules.

Split out so gift and portfolio notifications read the same way; the raw
rule_type used to leak into the message body.
"""

from decimal import Decimal


def format_ton(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    return f"{Decimal(value).normalize():f} TON"


def portfolio_message(rule_type: str, total: Decimal, change: Decimal, threshold: Decimal) -> str:
    if rule_type == "portfolio_value_above":
        head = "📈 Портфель выше порога"
        detail = f"Порог: выше {format_ton(threshold)}"
    elif rule_type == "portfolio_value_below":
        head = "📉 Портфель ниже порога"
        detail = f"Порог: ниже {format_ton(threshold)}"
    else:
        head = "📉 Портфель просел" if change < 0 else "📈 Портфель вырос"
        detail = f"Порог: движение от {threshold}%"
    return "\n".join(
        [
            head,
            "",
            f"Сейчас: {format_ton(total)}",
            f"Изменение: {change:+.2f}%",
            "",
            detail,
        ]
    )
