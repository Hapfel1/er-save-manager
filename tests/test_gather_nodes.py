from er_save_manager.data.gather_nodes import GATHER_ONCE, get_gather_nodes


def test_gather_nodes_load():
    for convergence in (False, True):
        nodes = get_gather_nodes(convergence)
        if not convergence:
            assert len({n.key for n in nodes}) == len(nodes)
        leaves = [n for n in nodes if n.items[0][2] == "Arteria Leaf"]
        assert leaves and all(n.source == GATHER_ONCE for n in leaves)
        assert any(n.item_label == "Rowa Fruit x1-5" and not n.one_time for n in nodes)
        assert all(n.grace_flag for n in nodes if n.map_id.startswith("m60_42_36"))
