from er_save_manager.data.gestures import (
    GESTURE_LIST_EMPTY,
    merge_unlocked_gestures,
    unlocked_gestures,
)


def test_merge_only_changes_the_obtained_bit():
    # Bow not obtained (0), Polite Bow obtained (3), My Thanks not (4),
    # Wave obtained (15), 999 is not an editable gesture.
    stored = [0, 3, 4, 15, 999] + [GESTURE_LIST_EMPTY] * 59
    assert unlocked_gestures(stored) == {3, 15, 999}

    editable = {1, 3, 5, 15}
    assert merge_unlocked_gestures(stored, {3, 15}, editable) == stored

    out = merge_unlocked_gestures(stored, {1, 5}, editable)
    assert out[:6] == [1, 2, 5, 14, 999, GESTURE_LIST_EMPTY]
    assert len(out) == 64
