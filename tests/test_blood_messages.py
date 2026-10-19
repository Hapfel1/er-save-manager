"""NetMan chunk 6 message reading, protect and delete."""

import struct

from er_save_manager.editors.blood_messages import BloodMessageEditor, message_lines
from er_save_manager.fixes.netman import NETMAN_SIZE, netman_problems


def _own_entry(template, word, conj=0, template2=0, word2=0, gesture=0xFF):
    body = bytearray(600)
    body[0x0C:0x10] = bytes([0, 0, 42, 60])  # m60_42_00_00 as [DD CC BB AA]
    struct.pack_into("<3f", body, 0x24, 1.0, 2.0, 3.0)
    struct.pack_into(
        "<HBBHHHH", body, 0x34, template, gesture, 0, word, conj, template2, word2
    )
    body[0xB8:0xBC] = b"FACE"
    name = "Tester".encode("utf-16-le")
    body[0x1D8 : 0x1D8 + len(name)] = name
    return struct.pack("<II", 0, 600) + bytes(body)


def _insert_own(save, slot_index, entry):
    """Put an own message at the start of chunk 6; returns the original region."""
    start = save.character_slots[slot_index].net_man_offset
    region = bytes(save._raw_data[start : start + NETMAN_SIZE])
    pos = 4
    while True:
        ctype, version, size = struct.unpack_from("<HHI", region, pos)
        if ctype == 6:
            break
        pos += 8 + size
    header = struct.pack("<HHI", 6, version, size + len(entry))
    new = region[:pos] + header + entry + region[pos + 8 :]
    new = new[:NETMAN_SIZE]
    assert netman_problems(new) == []
    save._raw_data[start : start + NETMAN_SIZE] = new
    return region


def _first_slot_with_messages(save):
    for i, slot in enumerate(save.character_slots):
        if not slot.is_empty() and BloodMessageEditor(save, i).messages():
            return i
    raise AssertionError("fixture has no messages")


def test_message_text():
    assert message_lines(10000, 30001) == ["enemy ahead"]
    assert message_lines(10015, 30001) == ["enemy, O enemy"]
    assert message_lines(10003, 30003, 50003, 10007, 33017) == [
        "be wary of strong foe",
        "therefore seek brief respite",
    ]
    # 50009 attaches a comma to the first phrase
    assert message_lines(10003, 37010, 50009, 10004, 33002) == [
        "be wary of up,",
        "try ranged battle",
    ]


def test_cached_messages_read(sanitized_save_readonly):
    i = _first_slot_with_messages(sanitized_save_readonly)
    messages = BloodMessageEditor(sanitized_save_readonly, i).messages()
    assert all(not m.is_own for m in messages)
    assert all("[" not in m.text for m in messages)


def test_protect_and_delete_own_message(sanitized_save):
    i = _first_slot_with_messages(sanitized_save)
    entry = _own_entry(10003, 30003, 50003, 10007, 33017, gesture=20)
    original = _insert_own(sanitized_save, i, entry)
    editor = BloodMessageEditor(sanitized_save, i)
    before = editor.messages()
    own = [m for m in before if m.is_own]
    assert len(own) == 1
    msg = own[0]
    assert msg.lines == ["be wary of strong foe", "therefore seek brief respite"]
    assert msg.gesture_name == "Point Forwards"
    assert msg.author == "Tester"
    assert msg.map_str == "m60_42_00_00"
    assert not msg.protected

    ok, _ = editor.set_protected(msg, True)
    assert ok
    protected = [m for m in editor.messages() if m.is_own][0]
    assert protected.protected

    ok, _ = editor.delete(protected)
    assert ok
    start = sanitized_save.character_slots[i].net_man_offset
    assert bytes(sanitized_save._raw_data[start : start + NETMAN_SIZE]) == original
    assert len(editor.messages()) == len(before) - 1


def test_cached_message_not_editable(sanitized_save):
    i = _first_slot_with_messages(sanitized_save)
    editor = BloodMessageEditor(sanitized_save, i)
    msg = editor.messages()[0]
    raw = bytes(sanitized_save._raw_data)
    assert editor.delete(msg)[0] is False
    assert editor.set_protected(msg, True)[0] is False
    assert bytes(sanitized_save._raw_data) == raw


def test_stale_message_refused(sanitized_save):
    i = _first_slot_with_messages(sanitized_save)
    _insert_own(sanitized_save, i, _own_entry(10000, 30001))
    editor = BloodMessageEditor(sanitized_save, i)
    msg = [m for m in editor.messages() if m.is_own][0]
    assert editor.delete(msg)[0]
    assert editor.delete(msg)[0] is False
