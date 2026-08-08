"""Strategy research: rules in, measured history out.

The division of labour in this package is deliberate and worth stating once.
The engine computes, the assistant talks. `backtest` and `discovery` never
call a model, and the model is never asked for a number: it may name a
strategy and describe one that the engine already measured.

A language model asked "how did this strategy do" will answer with a
plausible percentage every single time, and it will be wrong in a way that
looks exactly like being right.
"""

from .strategy import Filters, Strategy

__all__ = ["Filters", "Strategy"]
