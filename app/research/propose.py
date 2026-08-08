"""Turns a question into a rule set, and a measured result into words.

The assistant is allowed two jobs here and no others. It may translate
"find me cheap gifts that sell fast" into thresholds our engine understands,
and it may describe a result the engine already computed.

It is never asked how a strategy performed. Every number in an explanation
is handed to it, and the prompt says so in the only terms a model reliably
respects: the data block is the whole world.
"""

import json
import re

from pydantic import ValidationError

from app.ai.client import AssistantUnavailable, OpenRouterClient

from .backtest import BacktestResult
from .strategy import Filters, Strategy

# A model told to return JSON will still wrap it in prose or a code fence
# often enough that parsing has to expect it.
JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

PROPOSE_SYSTEM = """You translate a trader's request into a strategy for Gift Trader, a market terminal for Telegram NFT gifts on TON.

Return ONLY a JSON object. No prose, no code fence, no explanation.

Schema, every field optional except name:
{
  "name": short string, in the user's language,
  "filters": {
    "min_discount_percent": number 0-99,
    "max_price_ton": number above 0,
    "min_price_ton": number 0 or above,
    "max_rarity_percent": number 0-100, share of the collection carrying the trait, SMALLER IS RARER,
    "max_hours_to_sell": number above 0, observed median time a listing survives,
    "min_closed_listings": integer 0 or above, evidence the gift trades at all,
    "marketplaces": list of tonnel, mrkt, getgems, portals, fragment
  },
  "hold_hours": integer 1-336,
  "exit_at": "floor" or "median",
  "require_sold": boolean
}

Rules:
- Rarity is a share, so rare means a SMALL max_rarity_percent. 1 is rarer than 10.
- Omit any field the request does not imply. Do not invent thresholds to look thorough.
- If the request implies a liquidity condition, also set min_closed_listings to at least 2, otherwise the rule is satisfied by gifts nobody has watched yet.
- Never output a performance figure. You are proposing a rule, not reporting a result."""

EXPLAIN_SYSTEM = """You are the analyst inside Gift Trader, a market terminal for Telegram NFT gifts on TON.

You are given a strategy and the result of a backtest our own engine ran over our own stored history. Explain it to a trader.

Rules you must never break:
1. Every number you write must appear in the DATA block. Never compute, round differently, extrapolate or invent one.
2. The out-of-sample half is the honest one. If it is weak or missing, say the strategy is unproven, no matter how good the other half looks.
3. Name the weakest part of the evidence: few trades, short history, unresolved entries, or a wide gap between the two halves.
4. Never promise profit. Past behaviour of a thin market is not a forecast.
5. Answer in the language the user writes in.

Four short sentences at most: what the rule buys, what happened, what is weak, whether it is worth arming."""


def _extract_json(text: str) -> dict:
    match = JSON_BLOCK.search(text)
    if match is None:
        raise AssistantUnavailable("модель вернула не JSON")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AssistantUnavailable(f"модель вернула сломанный JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssistantUnavailable("модель вернула не объект")
    return payload


async def propose_strategy(client: OpenRouterClient, request: str) -> Strategy:
    """Ask for a rule set, then hold it to the schema.

    Validation is the safety net: whatever the model comes up with, only
    fields the engine can actually execute survive, and a malformed answer
    becomes an error the user sees rather than a silent default.
    """
    reply = await client.complete(
        system=PROPOSE_SYSTEM,
        user=request.strip(),
        max_tokens=400,
        # Rule translation is not a place for creativity.
        temperature=0.0,
    )
    payload = _extract_json(reply.text)
    # Models like to volunteer a result. There is no result yet.
    payload.pop("performance", None)
    payload.pop("backtest", None)
    exit_at = payload.get("exit_at")
    try:
        filters = Filters.model_validate(payload.get("filters") or {})
        return Strategy(
            name=str(payload.get("name") or "Стратегия")[:120],
            filters=filters,
            hold_hours=int(payload.get("hold_hours") or 48),
            exit_at=exit_at if exit_at in ("floor", "median") else "floor",
            require_sold=bool(payload.get("require_sold", False)),
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise AssistantUnavailable(
            f"модель предложила условия, которые движок не принимает: {exc}"
        ) from exc


def result_block(result: BacktestResult) -> str:
    """The only numbers the assistant is allowed to repeat."""

    def block(title: str, metrics) -> str:
        if not metrics.trades:
            return f"{title}: сделок нет"
        return (
            f"{title}: сделок {metrics.trades}, в плюс {metrics.wins} "
            f"({metrics.win_rate}%), медиана {metrics.median_profit_percent}%, "
            f"среднее {metrics.mean_profit_percent}%, итог {metrics.total_profit_ton} TON, "
            f"лучшая {metrics.best_percent}%, худшая {metrics.worst_percent}%, "
            f"незакрытых входов {metrics.unresolved}"
        )

    return "\n".join(
        [
            f"СТРАТЕГИЯ: {result.strategy.summary()}",
            f"Окно: {result.window_days} дней, реальной истории {result.history_days} дней",
            block("ВСЕГО", result.overall),
            block("ПЕРВАЯ ПОЛОВИНА (на ней отбирали)", result.in_sample),
            block("ВТОРАЯ ПОЛОВИНА (проверка)", result.out_of_sample),
            f"Подтвердилась на проверке: {'да' if result.holds_up else 'нет'}",
            "Выход считается по преобладающей цене через hold_hours, за вычетом "
            "комиссии площадки и газа. Исчезновение лота с рынка не является "
            "доказательством цены продажи.",
        ]
    )


async def explain_result(client: OpenRouterClient, result: BacktestResult) -> str:
    reply = await client.complete(
        system=EXPLAIN_SYSTEM,
        user=f"DATA:\n{result_block(result)}",
        max_tokens=320,
    )
    return reply.text
