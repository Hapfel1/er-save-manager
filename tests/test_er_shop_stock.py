"""Elden Ring limited merchant stock data (data/shop_stock*.csv).

Restocking clears a purchase counter of bit_length(quantity) event flags, so
counters must have storage and must not overlap another row's counter.
"""

from __future__ import annotations

import pytest

from er_save_manager.data.shop_stock import bought, get_stock
from er_save_manager.parser.event_flags import EventFlags

DATASETS = pytest.mark.parametrize(
    "is_convergence", [False, True], ids=["vanilla", "convergence"]
)


@DATASETS
def test_counters_stored_and_disjoint(is_convergence):
    owner: dict[int, int] = {}
    for row in get_stock(is_convergence):
        assert row.quantity >= 1 and row.merchant and row.item_name
        for flag_id in row.counter_flags:
            assert EventFlags.has_flag(flag_id), flag_id
            assert owner.setdefault(flag_id, row.flag_id) == row.flag_id, flag_id


def test_counter_is_lsb_first_purchase_count():
    """Nomadic Merchant at Liurnia Lake Shore, Smithing Stone [1] x5: buying
    1, 2 and all 5 left bits 100, 010, 101 from flag 160490."""
    row = next(r for r in get_stock() if r.flag_id == 160490)
    assert (row.quantity, row.merchant, row.grace_flag) == (
        5,
        "Nomadic Merchant",
        76201,
    )
    assert list(row.counter_flags) == [160490, 160491, 160492]
    for bits, count in (((1, 0, 0), 1), ((0, 1, 0), 2), ((1, 0, 1), 5)):
        state = dict(zip(row.counter_flags, bits, strict=True))
        assert bought(row, state.get) == count
