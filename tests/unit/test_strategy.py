"""Tests for the momentum + buy/sell-ratio strategy and the paper book."""

from mchpai_common.strategies import (
    Features,
    PaperBook,
    Position,
    StrategyParams,
    entry_signal,
    exit_signal,
)

P = StrategyParams()


def _f(price, buy_vol, sell_vol, buyers, age, prices):
    return Features(price=price, buy_vol=buy_vol, sell_vol=sell_vol, buyers=buyers,
                    age_s=age, prices=prices)


def test_entry_requires_ratio_and_momentum():
    rising = [1.0, 1.05, 1.1, 1.15, 1.2]
    strong = _f(1.2, buy_vol=4.0, sell_vol=1.0, buyers=5, age=30, prices=rising)
    assert entry_signal(strong, P) is True

    weak_ratio = _f(1.2, buy_vol=1.0, sell_vol=1.0, buyers=5, age=30, prices=rising)
    assert entry_signal(weak_ratio, P) is False

    flat = _f(1.0, buy_vol=4.0, sell_vol=1.0, buyers=5, age=30, prices=[1, 1, 1, 1, 1])
    assert entry_signal(flat, P) is False  # no momentum

    too_young = _f(1.2, buy_vol=4.0, sell_vol=1.0, buyers=5, age=2, prices=rising)
    assert entry_signal(too_young, P) is False


def test_exit_take_profit_and_stop():
    pos = Position("M", entry=1.0, size_sol=0.5, tokens=0.5, opened_ts=0, peak=1.0)
    tp = _f(1.5, 3, 1, 4, 60, [1.0, 1.5])
    do, reason = exit_signal(pos, tp, P)
    assert do and reason == "take_profit"

    sl = _f(0.75, 3, 1, 4, 60, [1.0, 0.75])
    do, reason = exit_signal(pos, sl, P)
    assert do and reason == "stop_loss"


def test_exit_sell_pressure_and_reversal():
    pos = Position("M", entry=1.0, size_sol=0.5, tokens=0.5, opened_ts=0, peak=1.1)
    pressure = _f(1.05, buy_vol=1.0, sell_vol=5.0, buyers=4, age=60, prices=[1.1, 1.05])
    do, reason = exit_signal(pos, pressure, P)
    assert do and reason in ("sell_pressure", "momentum_reversal", "trailing_stop")


def test_paperbook_round_trip_pnl():
    book = PaperBook(P, start_sol=10.0)
    rising = [1.0, 1.05, 1.1, 1.15, 1.2]
    # entry tick
    book.on_tick("M", _f(1.0, 4, 1, 5, 30, rising), ts=0)
    assert "M" in book.positions
    spent = book.start - book.cash
    assert spent > 0
    # exit at take-profit
    ev = book.on_tick("M", _f(2.0, 4, 1, 5, 90, [1.0, 2.0]), ts=10)
    assert ev and ev[0]["action"] == "sell"
    assert book.realized > 0           # profitable round trip
    assert book.stats()["trades"] == 1
    assert book.stats()["win_rate"] == 1.0


def test_paperbook_respects_max_positions():
    p = StrategyParams(max_positions=1)
    book = PaperBook(p, start_sol=10.0)
    rising = [1.0, 1.1, 1.2]
    book.on_tick("A", _f(1.2, 4, 1, 5, 30, rising), ts=0)
    book.on_tick("B", _f(1.2, 4, 1, 5, 30, rising), ts=0)
    assert len(book.positions) == 1   # second entry blocked
