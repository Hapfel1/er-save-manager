
# Item Spawning Implementation

This document describes the current approach for adding items to a character's inventory in the save editor. The process is designed to match the in-game data structures and maintain save file integrity.

## Overview

Item spawning involves updating several interconnected structures in the save file:

- The gaitem map (item registry)
- The inventory array (actual item slots)
- Various counters and indices (acquisition order, item count)

All item types (weapons, armor, talismans, consumables, gems) are represented by entries in the gaitem map and referenced by handle in the inventory.

## Steps for Adding an Item

1. **Classify the Item**
   - Determine the item category from the item ID (weapon, armor, talisman, consumable, gem).
   - This determines the handle prefix and the size of the gaitem entry.

2. **Find an Empty Gaitem Slot**
   - Locate the first available slot in the gaitem map (all empty slots are 8 bytes initially).

3. **Generate a Gaitem Handle**
   - Use the category to determine the handle prefix.
   - The handle is constructed using the category and the slot index or recycled lower bits.

4. **Create and Populate the Gaitem Entry**
   - Set the handle, item ID, and any extended fields (upgrade level, reinforcement type, gem handle, etc.).
   - The structure and fields depend on the item type.

5. **Update the Gaitem Map**
   - Replace the empty slot with the new gaitem entry. This expands the slot to 16 or 21 bytes as needed.

6. **Find an Empty Inventory Slot**
   - Locate the next available slot in the inventory array (held or storage).

7. **Create and Populate the Inventory Entry**
   - Reference the gaitem handle, set the quantity, and assign the next acquisition index.

8. **Update Counters**
   - Increment the item count and acquisition index counter in the inventory structure.

9. **Rebuild the Slot**
   - Serialize the entire character slot using the slot rebuild system. This ensures all offsets and sizes are correct after expanding the gaitem map.

10. **Write and Save**
    - Write the rebuilt slot back to the save file, recalculate checksums, and save.

## Notes

- The implementation uses the same data structures and allocation logic as the game, including handle generation and slot expansion.
- All items are referenced by handle in the inventory, and the gaitem map is the authoritative registry for item properties.
- The acquisition index is used for sorting and tracking the order in which items were obtained.
- The slot rebuild step is critical for maintaining save file integrity, as adding items changes the size of the gaitem map and shifts subsequent data.

## Limitations

- The game performs additional validation on load. Items added offline may be removed if required internal state or flags are missing.
- This implementation does not currently set any event flags or additional state beyond the save file structures described above.

## References

- See `src/er_save_manager/parser/er_types.py` for gaitem structure definitions.
- See `src/er_save_manager/parser/equipment.py` for inventory structures.
- See `src/er_save_manager/parser/slot_rebuild.py` for slot serialization logic.
- See `src/er_save_manager/ui/editors/inventory_editor.py` for the item addition implementation.

