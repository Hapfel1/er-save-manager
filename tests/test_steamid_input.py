from er_save_manager.ui.tabs.steamid_patcher_tab import to_steamid64

ACCOUNT_64 = "76561198000233116"


def test_every_format_converts_to_the_same_steamid64():
    for text in (
        ACCOUNT_64,
        "[U:1:39967388]",
        "U:1:39967388",
        "39967388",
        "STEAM_0:0:19983694",
        "STEAM_1:0:19983694",
    ):
        assert to_steamid64(text, "F") == (ACCOUNT_64, None), text


def test_steamid2_low_bit():
    assert to_steamid64("STEAM_0:1:19983694", "F")[0] == "76561198000233117"


def test_invalid_input_is_refused_with_the_field_name():
    for text in (
        "",
        "0",
        "4294967296",
        "00000000000000000",
        "[U:0:5]",
        "STEAM_0:2:5",
        "765611980000000012",
        "name",
    ):
        value, error = to_steamid64(text, "New SteamID")
        assert value is None and error.startswith("New SteamID:"), text
