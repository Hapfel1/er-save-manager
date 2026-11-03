"""
Dark Souls Remastered PS4 userdata folder -> PC save.

Character slots are the PC decrypted slot layout on both platforms.
userdata0010 holds the PC system data plus a PS4 key config block and an
undecoded tail; only the PC part (_ps_system_view) goes into the PC file.
The undecoded tail has no PC source, so a PC save cannot be turned into a
new PS4 folder. DSR saves hold no SteamID.
"""

from __future__ import annotations

from er_save_manager.games import bnd4
from er_save_manager.games.DSR import save as dsr

_VERSION = bytes(8)


def to_pc_bytes(save: dsr.DSRSave) -> bytes:
    if not save.is_ps:
        raise ValueError("The save is already a PC save.")
    plaintexts = []
    for i in range(dsr.CHARACTER_SLOTS):
        char = save.characters[i]
        plaintexts.append(bytes(char.get_raw()) if char else save.slot_plaintext(i))
    plaintexts.append(bytes(save.system_data))
    entries = []
    for i, plaintext in enumerate(plaintexts):
        # The stored 16 bytes are both the IV and the MD5 of the ciphertext,
        # as save_to_file writes them; the IV only shapes the random head.
        ciphertext = dsr._encrypt(save._ps[i].iv, plaintext)
        entries.append(dsr._md5(ciphertext) + ciphertext)
    data = bnd4.build(entries, _VERSION)
    if len(data) != dsr.FILE_SIZE:
        raise ValueError(f"PC save built to {len(data):#x} bytes.")
    return data
