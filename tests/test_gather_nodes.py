from er_save_manager.data.gather_nodes import GATHER_ONCE, get_gather_nodes
from er_save_manager.editors.world_geom import set_node_collected
from er_save_manager.parser.inventory_ops import SLOT_DATA_SIZE


def test_gather_nodes_load():
    for convergence in (False, True):
        nodes = get_gather_nodes(convergence)
        if not convergence:
            assert len({n.key for n in nodes}) == len(nodes)
        leaves = [n for n in nodes if n.items[0][2] == "Arteria Leaf"]
        assert leaves and all(n.source == GATHER_ONCE for n in leaves)
        assert any(
            n.item_label == "Rowa Fruit x1-5" and not n.non_respawning for n in nodes
        )
        assert all(n.grace_flag for n in nodes if n.map_id.startswith("m60_42_36"))


def _collected(slot):
    data = slot.world_geom_man2.parse_geom()
    return {(r.map_name, e.part_name) for r in data.records for e in r.entries}


def test_node_collect_round_trip(sanitized_save):
    idx = next(
        i for i, s in enumerate(sanitized_save.character_slots) if not s.is_empty()
    )
    before = bytes(sanitized_save._raw_data)
    slot = sanitized_save.character_slots[idx]
    visited = {r.map_name for r in slot.world_geom_man2.parse_geom().records}
    node = next(
        n
        for n in get_gather_nodes()
        if n.non_respawning and n.map_id in visited and n.key not in _collected(slot)
    )
    set_node_collected(sanitized_save, idx, node.map_id, node.part, True)
    assert node.key in _collected(sanitized_save.character_slots[idx])
    assert len(sanitized_save._raw_data) == len(before)
    set_node_collected(sanitized_save, idx, node.map_id, node.part, False)
    # Everything up to the slot's unused tail comes back unchanged
    used_end = slot.data_start + SLOT_DATA_SIZE - len(slot.rest)
    after = bytes(sanitized_save._raw_data)
    assert after[:used_end] == before[:used_end]
    assert (
        after[slot.data_start + SLOT_DATA_SIZE :]
        == before[slot.data_start + SLOT_DATA_SIZE :]
    )
