"""
Save-type tagging shared by the Equipment, Inventory, and Character loadout
systems. A loadout records whether it was captured on a Convergence and/or
Seamless Co-op save.
"""

from __future__ import annotations

from typing import Any


def detect_save_type(save_file, save_path) -> dict[str, bool]:
    """Return {"convergence": bool, "seamless": bool} for the given save."""
    convergence = (
        bool(getattr(save_file, "is_convergence", False)) if save_file else False
    )
    seamless = ".co2" in str(save_path or "").lower()
    return {"convergence": convergence, "seamless": seamless}


def confirm_convergence_mismatch(
    parent,
    tag: dict[str, Any] | None,
    save_file,
    save_path,
    extra_text: str = "",
    check_seamless: bool = False,
) -> bool:
    if not tag:
        return True

    current = detect_save_type(save_file, save_path)
    convergence_mismatch = bool(tag.get("convergence")) and not current.get(
        "convergence"
    )
    seamless_mismatch = (
        check_seamless and bool(tag.get("seamless")) and not current.get("seamless")
    )
    if not convergence_mismatch and not seamless_mismatch:
        return True

    if convergence_mismatch and seamless_mismatch:
        message = (
            "This loadout was created on a Convergence + Seamless Co-op save, "
            "but the current save is neither. Item IDs, effects, and Seamless "
            "Co-op-exclusive items may not match."
        )
    elif convergence_mismatch:
        message = (
            "This loadout was created on a Convergence save, but the current "
            "save is not Convergence. Item IDs and effects may not match."
        )
    else:
        message = (
            "This loadout may include Seamless Co-op-exclusive items, but the "
            "current save is not a Seamless Co-op save. Those items may not "
            "work correctly."
        )

    is_target_vanilla = not current.get("convergence") and not current.get("seamless")
    if check_seamless and is_target_vanilla:
        message += (
            "\n\nWarning: owning Convergence or Seamless Co-op-exclusive items "
            "on a vanilla save and playing online can get you banned."
        )

    if extra_text:
        message += f"\n\n{extra_text}"
    message += "\n\nContinue anyway?"

    from er_save_manager.ui.messagebox import CTkMessageBox

    return CTkMessageBox.askyesno("Loadout Type Mismatch", message, parent=parent)
