"""
Event Flags Tab (customtkinter version)
Event flag viewer and editor
"""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.backup.manager import BackupManager
from er_save_manager.data.boss_data import (
    BOSS_CATEGORIES,
    BOSSES,
    get_boss_flags,
    get_bosses_by_category,
)
from er_save_manager.data.event_flags_db import (
    CATEGORIES,
    get_category_flags,
    get_flag_name,
    get_subcategories,
    is_convergence,
)
from er_save_manager.data.summoning_pools_data import (
    SUMMONING_POOL_FLAGS_BASE,
    SUMMONING_POOL_FLAGS_DLC,
)
from er_save_manager.parser.event_flags import EventFlags
from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.pending import StageError, guard_before_write
from er_save_manager.ui.popups import reopenable
from er_save_manager.ui.toast import notify
from er_save_manager.ui.tooltip import MULTI_SELECT_TIP, add_tooltip
from er_save_manager.ui.utils import (
    bind_mousewheel,
    patch_combo_scroll,
    pick_file,
)


class EventFlagsTab:
    """Tab for event flag viewing and management (customtkinter version)"""

    class _EventFlagAccessor:
        """get/set on the event flags of the loaded character.

        Every call reads slot.event_flags of the slot get_slot returns, so
        flags written by other tabs (map graces, NPCs, bosses, item spawns)
        are seen and never overwritten by an older copy.
        """

        def __init__(self, get_slot):
            self._get_slot = get_slot

        @property
        def slot(self):
            return self._get_slot()

        def get_flag(self, flag_id: int) -> bool:
            return EventFlags.get_flag(self.slot.event_flags, flag_id)

        def set_flag(self, flag_id: int, state: bool) -> None:
            slot = self.slot
            if not isinstance(slot.event_flags, bytearray):
                slot.event_flags = bytearray(slot.event_flags)
            EventFlags.set_flag(slot.event_flags, flag_id, state)

        def sync_raw(self, save_file) -> None:
            """Copy the slot's event flags into the save's raw data, which
            is what gets written to disk."""
            slot = self.slot
            offset = getattr(slot, "event_flags_offset", 0)
            if offset > 0:
                save_file._raw_data[offset : offset + len(slot.event_flags)] = (
                    slot.event_flags
                )

    def __init__(
        self,
        parent,
        get_save_file_callback,
        get_save_path_callback,
        reload_callback,
        show_toast_callback,
    ):
        self.show_toast = show_toast_callback
        """
        Initialize event flags tab

        Args:
            parent: Parent widget
            get_save_file_callback: Function that returns current save file
            get_save_path_callback: Function that returns save file path
            reload_callback: Function to reload save file
        """
        self.parent = parent
        self.get_save_file = get_save_file_callback
        self.get_save_path = get_save_path_callback
        self.reload_save = reload_callback

        self.current_slot = None
        self.category_var = None
        self.subcategory_var = None
        self.search_var = None
        # flag_id -> state the user set that differs from the save, written
        # on Apply. Flags without an entry show the slot's current state.
        self.flag_states = {}
        self.flag_rows = {}  # flag_id -> tree row of every displayed flag
        self.current_event_flags = None
        self._search_after_id = None
        self._fit_job = None
        self._flag_row_px = None

    def _clear_flag_view(self):
        """Empty the flag list."""
        self.flags_tree.delete(*self.flags_tree.get_children())
        self.flag_rows.clear()

    def _reset_filters(self):
        """Clear category, subcategory and search selections."""
        self.category_var.set("")
        self.subcategory_var.set("")
        self.subcat_combo.configure(values=[], state="disabled")
        self.search_var.set("")

    def refresh(self):
        """A new save: drop the old character's flags."""
        self._refresh_subcategory_filter()

    def _refresh_subcategory_filter(self):
        """Re-apply convergence filtering to the subcategory dropdown.

        Loading a save does not trigger on_category_changed on its own, so a
        category selected for a previously loaded save can leave
        Convergence-only subcategories in the dropdown after a
        non-Convergence save loads.
        """
        if not hasattr(self, "category_var"):
            return

        category = self.category_var.get()
        if not category:
            return

        subcats = get_subcategories(category, include_convergence=self._is_cnv_save())
        if subcats:
            self.subcat_combo.configure(values=["All", *subcats], state="readonly")
            if self.subcategory_var.get() not in [*subcats, "All"]:
                self.subcategory_var.set("All")
        else:
            self.subcat_combo.configure(values=[], state="disabled")
            self.subcategory_var.set("")

    def setup_ui(self):
        """Setup the event flags tab UI"""
        main_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(main_frame)
        self._main_frame = main_frame
        main_frame._parent_canvas.bind(
            "<Configure>", lambda _e: self._schedule_fit_flag_list(), add="+"
        )

        ctk.CTkLabel(
            main_frame,
            text="Event Flags",
            font=("Inter", 18, "bold"),
        ).pack(pady=(15, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            main_frame,
            text="View and edit event flags and respawn bosses",
            font=("Inter", 11),
            text_color=("gray50", "gray70"),
        ).pack(pady=(0, 12), padx=15, anchor="w")

        # Rows wrap onto more lines when the window is too narrow for them
        slot_frame = ds.FlowRow(main_frame)
        slot_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        ctk.CTkButton(
            slot_frame,
            text="Advanced...",
            command=self.open_advanced_editor,
            width=110,
        )

        ctk.CTkButton(
            slot_frame,
            text="Unlock All in Category",
            command=self.unlock_all_in_category,
            width=160,
        )

        ctk.CTkButton(
            slot_frame,
            text="Export Flags...",
            command=self.export_flags,
            width=120,
        )

        ctk.CTkButton(
            slot_frame,
            text="Import Flags...",
            command=self.import_flags,
            width=120,
        )

        slot_frame.add(*slot_frame.winfo_children())

        # Row 2: secondary tools
        tools_row = ds.FlowRow(main_frame)
        tools_row.pack(fill=tk.X, padx=15, pady=(6, 6))

        ctk.CTkButton(
            tools_row,
            text="Boss Respawn...",
            command=self.open_boss_respawn,
            width=140,
        )

        ctk.CTkButton(
            tools_row,
            text="Boss Status...",
            command=self.open_boss_status,
            width=130,
        )

        ctk.CTkButton(
            tools_row,
            text="NPC Revival...",
            command=self.open_npc_revival,
            width=130,
        )

        ctk.CTkButton(
            tools_row,
            text="Quest Progress...",
            command=self.open_quest_progress,
            width=145,
        )

        ctk.CTkButton(
            tools_row,
            text="Summoning Pools...",
            command=self.open_summoning_pools,
            width=155,
        )

        ctk.CTkButton(
            tools_row,
            text="Sites of Grace...",
            command=self.open_grace_dialog,
            width=140,
        )
        tools_row.add(*tools_row.winfo_children())

        # Row 3: item and merchant checklists
        items_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        items_row.pack(fill=tk.X, padx=15, pady=(0, 20))

        ctk.CTkButton(
            items_row,
            text="Item Pickups...",
            command=self.open_item_pickups,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkButton(
            items_row,
            text="Merchant Restock...",
            command=self.open_merchant_restock,
            width=150,
        ).pack(side=tk.LEFT)

        filter_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        filter_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            filter_frame,
            text="Browse by category",
            font=("Inter", 12, "bold"),
        ).pack(pady=(10, 8), padx=12, anchor="w")

        cat_inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        cat_inner.pack(fill=tk.X, padx=12, pady=(0, 12))

        ctk.CTkLabel(cat_inner, text="Category:").pack(side=tk.LEFT, padx=(0, 8))
        self.category_var = tk.StringVar(value="")
        cat_combo = ctk.CTkComboBox(
            cat_inner,
            variable=self.category_var,
            values=["", *CATEGORIES],
            state="readonly",
            width=260,
            command=self.on_category_changed,
        )
        patch_combo_scroll(cat_combo)
        cat_combo.pack(side=tk.LEFT, padx=(0, 20))

        ctk.CTkLabel(cat_inner, text="Subcategory:").pack(side=tk.LEFT, padx=(0, 8))
        self.subcategory_var = tk.StringVar(value="")
        self.subcat_combo = ctk.CTkComboBox(
            cat_inner,
            variable=self.subcategory_var,
            state="readonly",
            width=260,
            command=self.on_subcategory_changed,
        )
        patch_combo_scroll(self.subcat_combo)
        self.subcat_combo.pack(side=tk.LEFT)

        search_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        search_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            search_frame,
            text="Search flags",
            font=("Inter", 12, "bold"),
        ).pack(pady=(10, 8), padx=12, anchor="w")

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(fill=tk.X, padx=12, pady=(0, 12))

        ctk.CTkLabel(search_inner, text="Search:").pack(side=tk.LEFT, padx=(0, 8))
        self.search_var = tk.StringVar(value="")
        self.search_var.trace_add("write", self.on_search_changed)
        search_entry = ctk.CTkEntry(
            search_inner, textvariable=self.search_var, width=320
        )
        search_entry.pack(side=tk.LEFT, padx=(0, 12))

        ctk.CTkLabel(
            search_inner,
            text="(Search by flag ID or name)",
            text_color=("gray50", "gray70"),
        ).pack(side=tk.LEFT, padx=(0, 12))

        ctk.CTkButton(
            search_inner, text="Clear", command=self.clear_search, width=90
        ).pack(side=tk.LEFT)

        flags_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        flags_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        ctk.CTkLabel(
            flags_frame,
            text="Event Flags",
            font=("Inter", 12, "bold"),
        ).pack(pady=(10, 8), padx=12, anchor="w")

        # A Treeview holds the full flag set without slowing down, where one
        # checkbox widget per flag took seconds to build on a broad search.
        tree_frame, self.flags_tree = ds.themed_tree(
            flags_frame,
            columns=("state", "flag_id", "name", "location"),
            show="headings",
            selectmode="extended",
            height=20,
        )
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))
        # The tab sits in a scrollable frame whose wheel bindings would scroll
        # the page instead of the list, so a tag ahead of them handles the
        # wheel over the list and stops the event there.
        wheel_tag = "EventFlagTreeWheel"
        self.flags_tree.bindtags((wheel_tag, *self.flags_tree.bindtags()))
        self.flags_tree.bind_class(
            wheel_tag,
            "<MouseWheel>",
            lambda e: self._scroll_tree(-1 if e.delta > 0 else 1),
        )
        self.flags_tree.bind_class(
            wheel_tag, "<Button-4>", lambda _e: self._scroll_tree(-1)
        )
        self.flags_tree.bind_class(
            wheel_tag, "<Button-5>", lambda _e: self._scroll_tree(1)
        )
        self.flags_tree.heading("state", text="State")
        self.flags_tree.heading("flag_id", text="Flag ID")
        self.flags_tree.heading("name", text="Name")
        self.flags_tree.heading("location", text="Category")
        self.flags_tree.column("state", width=60, anchor="center", stretch=False)
        self.flags_tree.column("flag_id", width=110, anchor="w", stretch=False)
        self.flags_tree.column("name", width=420, anchor="w")
        self.flags_tree.column("location", width=260, anchor="w")
        self.flags_tree.tag_configure("on", foreground=palette.pick(palette.GREEN_TEXT))
        self.flags_tree.bind("<Button-1>", self._on_tree_click)
        self.flags_tree.bind("<space>", self._toggle_selected)
        # Map, grace, boss and NPC edits elsewhere write flags straight to the
        # slot; showing the tab or pointing at the list picks them up.
        self.flags_tree.bind("<Enter>", self._refresh_rows, add="+")
        self.parent.bind("<Map>", self._refresh_rows, add="+")

        ctk.CTkLabel(
            flags_frame,
            text="Click a State cell to toggle a flag, or select rows and press Space.",
            text_color=("gray50", "gray70"),
        ).pack(padx=12, anchor="w")

        action_frame = ctk.CTkFrame(flags_frame, fg_color="transparent")
        action_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            action_frame,
            text="Select a category or search for flags",
            text_color=("gray50", "gray70"),
        )
        self.status_label.pack(side=tk.LEFT)

    def load_slot(self, slot_idx: int) -> None:
        """Load the event flags of the character in slot_idx; -1 or an empty
        slot clears the tab. Reloading the same slot (after Apply All) keeps
        the shown category or search."""
        save_file = self.get_save_file()
        same_slot = slot_idx == self.current_slot
        self.flag_states.clear()
        self.current_event_flags = None
        self.current_slot = None
        if not hasattr(self, "flags_tree"):
            return
        self._clear_flag_view()
        slot = (
            save_file.characters[slot_idx]
            if save_file is not None and 0 <= slot_idx < 10
            else None
        )
        if (
            slot is None
            or slot.is_empty()
            or slot_idx not in save_file.get_active_slots()
            or not getattr(slot, "event_flags", None)
        ):
            self._reset_filters()
            self.status_label.configure(text="No character loaded.")
            return

        self.current_slot = slot_idx
        self.current_event_flags = self._EventFlagAccessor(
            lambda: self.get_save_file().characters[slot_idx]
        )
        if not same_slot:
            self._reset_filters()
        if self.search_var.get().strip():
            self._run_search(self.search_var.get().strip().lower())
        elif self.category_var.get():
            if self.subcategory_var.get():
                self.on_subcategory_changed()
            else:
                self.display_flags(self.category_var.get(), None)
        else:
            self.status_label.configure(text="Select a category or search for flags")

    def on_category_changed(self, choice=None):
        """Handle category selection"""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        category = self.category_var.get()
        if not category:
            return

        # Update subcategories, hiding Convergence-only ones for other saves
        subcats = get_subcategories(category, include_convergence=self._is_cnv_save())
        if subcats:
            self.subcat_combo.configure(values=["All", *subcats], state="readonly")
            self.subcategory_var.set("All")
            self.on_subcategory_changed()
        else:
            self.subcat_combo.configure(values=[], state="disabled")
            self.subcategory_var.set("")
            self.display_flags(category, None)

    def on_subcategory_changed(self, choice=None):
        """Handle subcategory selection"""
        if self.current_event_flags is None:
            return

        category = self.category_var.get()
        subcategory = self.subcategory_var.get()

        if category and subcategory:
            self.display_flags(category, None if subcategory == "All" else subcategory)

    def _is_cnv_save(self) -> bool:
        """Return True if the loaded save is a Convergence save."""
        save_file = self.get_save_file()
        return bool(save_file and save_file.is_convergence)

    def _filter_flags(self, flags):
        """Drop Convergence-only flags unless the loaded save is a Convergence save."""
        if self._is_cnv_save():
            return flags
        return [f for f in flags if not is_convergence(f)]

    def display_flags(self, category, subcategory):
        """Display the flags of a category, or of one of its subcategories."""
        self._clear_flag_view()
        self.flags_tree.configure(displaycolumns=("state", "flag_id", "name"))

        flags = self._filter_flags(get_category_flags(category, subcategory))
        for flag_id in flags:
            self._insert_flag_row(flag_id, get_flag_name(flag_id))

        label = f"{category} > {subcategory}" if subcategory else category
        self.status_label.configure(text=f"Showing {len(flags)} flags in {label}")

    def _insert_flag_row(self, flag_id, name, location=""):
        """Add a flag to the list, showing its pending state if it has one."""
        state = self._shown_state(flag_id)
        self.flag_rows[flag_id] = self.flags_tree.insert(
            "",
            "end",
            values=("ON" if state else "OFF", flag_id, name, location),
            tags=("on",) if state else (),
        )

    def _shown_state(self, flag_id) -> bool:
        """Pending state of a flag, else its current state in the slot."""
        state = self.flag_states.get(flag_id)
        if state is None:
            state = self.current_event_flags.get_flag(flag_id)
        return state

    def _show_row_state(self, flag_id, state):
        row = self.flag_rows.get(flag_id)
        if row is not None:
            self.flags_tree.set(row, "state", "ON" if state else "OFF")
            self.flags_tree.item(row, tags=("on",) if state else ())

    def _set_flag_state(self, flag_id, state):
        """Record a pending state and update the flag's row if it is shown.
        A state equal to the slot's drops the pending entry."""
        if state == self.current_event_flags.get_flag(flag_id):
            self.flag_states.pop(flag_id, None)
        else:
            self.flag_states[flag_id] = state
        self._show_row_state(flag_id, state)

    def _refresh_rows(self, _event=None):
        """Show the slot's current state on rows without a pending state;
        other tabs write flags directly to the slot."""
        if self.current_event_flags is None or not self.flag_rows:
            return
        for flag_id, row in self.flag_rows.items():
            state = self._shown_state(flag_id)
            if (self.flags_tree.set(row, "state") == "ON") != state:
                self._show_row_state(flag_id, state)

    def _toggle_rows(self, rows):
        # Toggles what the row shows, so a row not yet refreshed after another
        # tab's write still flips to the state the user expects.
        for row in rows:
            flag_id = int(self.flags_tree.set(row, "flag_id"))
            shown = self.flags_tree.set(row, "state") == "ON"
            self._set_flag_state(flag_id, not shown)

    def _on_tree_click(self, event):
        """Toggle a flag when its State cell is clicked."""
        if self.flags_tree.identify_region(event.x, event.y) != "cell":
            return
        # "#1" is the first displayed column, which is always State.
        if self.flags_tree.identify_column(event.x) != "#1":
            return
        row = self.flags_tree.identify_row(event.y)
        if row:
            self._toggle_rows([row])

    # Fewest rows the flag list shrinks to on a short window. Below that the
    # page scrolls instead.
    _MIN_FLAG_ROWS = 8

    def _schedule_fit_flag_list(self):
        if self._fit_job is None:
            self._fit_job = self.flags_tree.after(50, self._fit_flag_list)

    def _row_pixels(self):
        """Height of one flag row, measured once since the theme sets no
        fixed row height and the font decides it."""
        if self._flag_row_px is None:
            tree = self.flags_tree
            rows = int(tree.cget("height"))
            heights = []
            for probe in (10, 20):
                tree.configure(height=probe)
                tree.update_idletasks()
                heights.append(tree.winfo_reqheight())
            tree.configure(height=rows)
            self._flag_row_px = max(1, (heights[1] - heights[0]) // 10)
        return self._flag_row_px

    def _fit_flag_list(self):
        """Give the flag list the height left over in the window, so the list
        fills the tab and scrolls instead of the page."""
        self._fit_job = None
        viewport = self._main_frame._parent_canvas.winfo_height()
        if viewport <= 1:
            return
        # A few pixels of slack keep the page scrollbar from flickering on.
        spare = viewport - self._main_frame.winfo_reqheight() - 4
        rows = int(self.flags_tree.cget("height"))
        fitted = max(self._MIN_FLAG_ROWS, rows + spare // self._row_pixels())
        if fitted != rows:
            self.flags_tree.configure(height=fitted)

    def _scroll_tree(self, units):
        self.flags_tree.yview_scroll(units * 3, "units")
        return "break"

    def _toggle_selected(self, _event=None):
        self._toggle_rows(self.flags_tree.selection())
        return "break"

    def on_search_changed(self, *args):
        """Debounce search input - cancel pending callback and reschedule."""
        if self._search_after_id is not None:
            self.flags_tree.after_cancel(self._search_after_id)
            self._search_after_id = None

        if self.current_event_flags is None:
            return

        query = self.search_var.get().strip().lower()
        if not query:
            self._clear_flag_view()
            self.status_label.configure(text="Select a category or search for flags")
            return

        self._search_after_id = self.flags_tree.after(
            300, lambda: self._run_search(query)
        )

    def _run_search(self, query: str):
        """Execute search across all documented flags."""
        self._search_after_id = None
        if self.search_var.get().strip().lower() != query:
            return

        self._clear_flag_view()

        results = []
        for category in CATEGORIES:
            subcats = get_subcategories(category)
            if subcats:
                for subcat in subcats:
                    flags = self._filter_flags(get_category_flags(category, subcat))
                    for flag_id in flags:
                        flag_name = get_flag_name(flag_id)
                        if query in str(flag_id).lower() or query in flag_name.lower():
                            results.append((flag_id, flag_name, category, subcat))
            else:
                flags = self._filter_flags(get_category_flags(category, None))
                for flag_id in flags:
                    flag_name = get_flag_name(flag_id)
                    if query in str(flag_id).lower() or query in flag_name.lower():
                        results.append((flag_id, flag_name, category, None))

        self.flags_tree.configure(
            displaycolumns=("state", "flag_id", "name", "location")
        )
        for flag_id, flag_name, category, subcategory in results:
            if flag_id in self.flag_rows:
                continue
            location = f"{category} > {subcategory}" if subcategory else category
            self._insert_flag_row(flag_id, flag_name, location)

        self.status_label.configure(text=f"Found {len(self.flag_rows)} matching flags")

    def clear_search(self):
        """Clear search field"""
        self.search_var.set("")
        self._clear_flag_view()
        self.status_label.configure(text="Select a category or search for flags")

    def unlock_all_in_category(self):
        """Unlock all flags in current category"""
        if not self.flag_rows:
            notify(self.parent, "No flags are currently displayed.", "warning")
            return

        result = CTkMessageBox.askyesno(
            "Enable Shown Flags",
            f"Set all {len(self.flag_rows)} displayed flags to ON?\n\n"
            f"This will affect only the flags currently visible.",
            parent=self.parent,
        )

        if result:
            for flag_id in self.flag_rows:
                self._set_flag_state(flag_id, True)

            notify(
                self.parent,
                f"Enabled all {len(self.flag_rows)} displayed flags.\n\nClick Apply All to save.",
                "success",
            )

    def flag_changes(self) -> int:
        """Pending flags whose state differs from the save."""
        if self.current_event_flags is None:
            return 0
        return sum(
            1
            for flag_id, state in self.flag_states.items()
            if self.current_event_flags.get_flag(flag_id) != state
        )

    def flag_details(self):
        if self.current_event_flags is None:
            return []
        rows = []
        for flag_id, state in self.flag_states.items():
            saved = self.current_event_flags.get_flag(flag_id)
            if saved != state:
                name = get_flag_name(flag_id)
                if name != f"Flag {flag_id}":
                    name = f"{name} ({flag_id})"
                rows.append((name, "On" if saved else "Off", "On" if state else "Off"))
        return rows

    def discard_flags(self) -> None:
        if self.current_event_flags is None:
            return
        for flag_id in list(self.flag_states):
            self._set_flag_state(flag_id, self.current_event_flags.get_flag(flag_id))

    def prepare_flags(self):
        """Return the function that writes the changed flags into the
        in-memory save (Apply All in the main window)."""
        if self.current_event_flags is None or self.current_slot is None:
            raise StageError("No event flags loaded.")
        save_file = self.get_save_file()
        accessor = self.current_event_flags
        states = dict(self.flag_states)

        def commit() -> None:
            for flag_id, new_state in states.items():
                accessor.set_flag(flag_id, new_state)
            accessor.sync_raw(save_file)

        return commit

    def export_flags(self):
        """Export all set event flags to a JSON file."""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        import json

        save_path = self.get_save_path()
        initial_dir = str(save_path.parent) if save_path else None
        slot_num = (self.current_slot + 1) if self.current_slot is not None else 1

        out_path = pick_file(
            title="Export Event Flags",
            initialdir=initial_dir,
            initialfile=f"flags_slot{slot_num}.json",
            save=True,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not out_path:
            return

        try:
            set_flags = []
            seen: set[int] = set()

            for category in CATEGORIES:
                subcats = get_subcategories(category)
                if subcats:
                    for subcat in subcats:
                        for flag_id in get_category_flags(category, subcat):
                            if flag_id in seen:
                                continue
                            seen.add(flag_id)
                            try:
                                if self.current_event_flags.get_flag(flag_id):
                                    set_flags.append(
                                        {
                                            "id": flag_id,
                                            "name": get_flag_name(flag_id),
                                        }
                                    )
                            except Exception:
                                pass
                else:
                    for flag_id in get_category_flags(category, None):
                        if flag_id in seen:
                            continue
                        seen.add(flag_id)
                        try:
                            if self.current_event_flags.get_flag(flag_id):
                                set_flags.append(
                                    {
                                        "id": flag_id,
                                        "name": get_flag_name(flag_id),
                                    }
                                )
                        except Exception:
                            pass

            data = {
                "slot": slot_num,
                "count": len(set_flags),
                "flags": set_flags,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.show_toast(f"Exported {len(set_flags)} set flags", duration=2500)

        except Exception as e:
            CTkMessageBox.showerror(
                "Export Failed", f"Could not export flags:\n{e}", parent=self.parent
            )

    def import_flags(self):
        """Apply flags from a JSON file. Entries with "state": false are cleared; others are set.
        Backward compatible: entries without a "state" field default to true."""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        import json

        save_path = self.get_save_path()
        initial_dir = str(save_path.parent) if save_path else None

        in_path = pick_file(
            title="Import Event Flags",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not in_path:
            return

        try:
            with open(in_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            CTkMessageBox.showerror(
                "Import Failed", f"Could not read file:\n{e}", parent=self.parent
            )
            return

        if not isinstance(data, dict) or not isinstance(data.get("flags"), list):
            CTkMessageBox.showerror(
                "Invalid File",
                'The file needs a "flags" list, as written by Export.',
                parent=self.parent,
            )
            return

        flag_ops, skipped = self._parse_import_entries(data["flags"])
        skipped_text = self._skipped_entries_text(skipped)

        missing = sum(1 for flag_id, _ in flag_ops if not EventFlags.has_flag(flag_id))
        flag_ops = [op for op in flag_ops if EventFlags.has_flag(op[0])]
        if not flag_ops:
            notify(
                self.parent,
                "No valid flag IDs found in file."
                + (
                    f"\n\n{missing} flag(s) are in blocks that do not exist in "
                    "Elden Ring saves and were skipped."
                    if missing
                    else ""
                )
                + skipped_text,
                "info",
            )
            return

        set_count = sum(1 for _, s in flag_ops if s)
        unset_count = len(flag_ops) - set_count
        summary = f"Set {set_count}" + (f", unset {unset_count}" if unset_count else "")
        if missing:
            summary = (
                f"{missing} flag(s) are in blocks that do not exist in Elden Ring "
                f"saves and will be skipped.\n\n{summary}"
            )
        result = CTkMessageBox.askyesno(
            "Confirm Import",
            f"{summary} flags on Slot {self.current_slot + 1}?{skipped_text}",
            parent=self.parent,
        )
        if not result:
            return
        # The import writes the file and reloads it, which would drop
        # unapplied edits after the write.
        if not guard_before_write("import the flags"):
            return

        save_file = self.get_save_file()

        try:
            backup_mgr = BackupManager(save_path)
            backup_mgr.create_backup(
                description=f"Before flag import (Slot {self.current_slot + 1})",
                operation="flag_import",
                save=save_file,
            )
        except PermissionError:
            CTkMessageBox.showwarning(
                "Backup Skipped",
                "Could not create backup (permission denied). Proceeding.",
                parent=self.parent,
            )

        applied = 0
        for flag_id, state in flag_ops:
            try:
                self.current_event_flags.set_flag(flag_id, state)
                applied += 1
            except Exception:
                pass

        self.current_event_flags.sync_raw(save_file)

        save_file.recalculate_checksums()
        save_file.save(self.get_save_path())
        self.reload_save()
        self._refresh_rows()

        self.show_toast(f"Imported {applied} flags", duration=2500)

    @staticmethod
    def _parse_import_entries(entries: list) -> tuple[list[tuple[int, bool]], list]:
        """Split import entries into (flag_id, state) pairs and the entries
        that are skipped. "state" must be true or false and defaults to true
        (exports list set flags without it); "id" must be an integer."""
        flag_ops: list[tuple[int, bool]] = []
        skipped: list = []
        for entry in entries:
            flag_id = entry.get("id") if isinstance(entry, dict) else None
            if isinstance(flag_id, str) and flag_id.strip().isdigit():
                flag_id = int(flag_id)
            state = entry.get("state", True) if isinstance(entry, dict) else None
            if (
                isinstance(flag_id, int)
                and not isinstance(flag_id, bool)
                and isinstance(state, bool)
            ):
                flag_ops.append((flag_id, state))
            else:
                skipped.append(entry)
        return flag_ops, skipped

    @staticmethod
    def _skipped_entries_text(skipped: list, limit: int = 8) -> str:
        """Message part listing skipped import entries, empty when none."""
        if not skipped:
            return ""
        import json

        lines = []
        for entry in skipped[:limit]:
            text = json.dumps(entry, ensure_ascii=False)
            lines.append(text if len(text) <= 60 else text[:57] + "...")
        if len(skipped) > limit:
            lines.append(f"and {len(skipped) - limit} more")
        count = "1 entry is" if len(skipped) == 1 else f"{len(skipped)} entries are"
        return (
            f'\n\n{count} skipped ("id" must be a whole number, "state" true '
            "or false):\n" + "\n".join(lines)
        )

    @reopenable
    def open_advanced_editor(self):
        """Open advanced flag editor dialog"""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, "Advanced Event Flag Editor")
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        ds.button_row(main, [{"text": "Close", "command": dialog.destroy}])
        ds.header(main, "Advanced Event Flag Editor", font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main,
            text="Check or toggle a single flag by ID.",
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(anchor="w", pady=(2, 10))

        input_frame = ds.box(main, pady=(0, 12))
        ctk.CTkLabel(input_frame, text="Flag ID", font=ds.FONT).pack(
            side=tk.LEFT, padx=(12, 8), pady=10
        )

        flag_id_var = tk.StringVar(value="")
        flag_entry = ctk.CTkEntry(
            input_frame, textvariable=flag_id_var, width=150, height=32, font=ds.FONT
        )
        flag_entry.pack(side=tk.LEFT, padx=(0, 12), pady=10)

        def missing_flag_message(flag_id: int) -> str:
            return (
                f"Flag {flag_id} is in block {flag_id // EventFlags.FLAG_DIVISOR}, "
                "which does not exist in Elden Ring saves. The game never reads "
                "it, so it cannot be set."
            )

        def toggle_flag():
            try:
                flag_id = int(flag_id_var.get())
            except ValueError:
                CTkMessageBox.showerror(
                    "Invalid Flag ID", "Invalid flag ID.", parent=dialog
                )
                return
            if not EventFlags.has_flag(flag_id):
                CTkMessageBox.showwarning(
                    "Flag Not In Save", missing_flag_message(flag_id), parent=dialog
                )
                return

            # The toggle writes the file and reloads it, which would drop
            # unapplied edits after the write.
            if not guard_before_write("toggle the flag"):
                return

            try:
                save_file = self.get_save_file()
                save_path = self.get_save_path()

                if not save_path or not save_path.is_file():
                    CTkMessageBox.showerror(
                        "Invalid Save Path",
                        "Could not locate save file.",
                        parent=dialog,
                    )
                    return

                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        description=f"Before advanced flag toggle {flag_id} (Slot {self.current_slot + 1})",
                        operation="advanced_flag_toggle",
                        save=save_file,
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied). Proceeding.",
                        parent=dialog,
                    )

                current = self.current_event_flags.get_flag(flag_id)
                new_state = not current
                self.current_event_flags.set_flag(flag_id, new_state)
                self.current_event_flags.sync_raw(save_file)

                save_file.recalculate_checksums()
                save_file.save(save_path)
                self.reload_save()

                self.show_toast(
                    f"Flag {flag_id} set to {'ON' if new_state else 'OFF'}",
                    duration=2000,
                )
            except Exception as e:
                CTkMessageBox.showerror(
                    "Toggle Failed", f"Failed to toggle flag: {e}", parent=dialog
                )

        def check_flag():
            try:
                flag_id = int(flag_id_var.get())
                if not EventFlags.has_flag(flag_id):
                    CTkMessageBox.showwarning(
                        "Flag Not In Save", missing_flag_message(flag_id), parent=dialog
                    )
                    return
                state = self.current_event_flags.get_flag(flag_id)
                flag_name = get_flag_name(flag_id)
                notify(
                    dialog,
                    f"Flag {flag_id}: {flag_name}\n\nState: {'ON' if state else 'OFF'}",
                    "info",
                )
            except ValueError:
                CTkMessageBox.showerror(
                    "Invalid Flag ID", "Invalid flag ID.", parent=dialog
                )
            except Exception as e:
                CTkMessageBox.showerror(
                    "Flag Check Failed", f"Failed to check flag: {e}", parent=dialog
                )

        ds.button(input_frame, "Toggle", toggle_flag, width=90).pack(
            side=tk.RIGHT, padx=(0, 12), pady=10
        )
        ds.button(input_frame, "Check", check_flag, primary=False, width=90).pack(
            side=tk.RIGHT, padx=(0, 8), pady=10
        )
        flag_entry.bind("<Return>", lambda _e: check_flag())

        ctk.CTkLabel(main, text="Warning", font=ds.BOLD, text_color=ds.WARNING).pack(
            anchor="w"
        )
        notes = ds.box(main, pady=(4, 0))
        for i, line in enumerate(
            (
                "Changing unknown flags may break your save.",
                "A backup is made before every toggle.",
                "Use the category browser for documented flags.",
                "Flag IDs are listed in event_flags_db.py in the source code.",
            )
        ):
            ctk.CTkLabel(notes, text=f"•  {line}", font=ds.FONT).pack(
                anchor="w", padx=12, pady=(8 if i == 0 else 2, 8 if i == 3 else 2)
            )
        ds.finish(dialog, self.parent, min_width=480)
        flag_entry.focus_set()

    @reopenable
    def open_boss_status(self):
        """Boss status dialog - defeated/alive for all tracked bosses."""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, "Boss Status")
        dialog.resizable(True, True)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        ds.button_row(main, [{"text": "Close", "command": dialog.destroy}])
        ds.header(main, "Boss Status", font=ds.TITLE_LARGE)

        all_entries: list[tuple[str, str, str]] = []
        for boss_name, data in BOSSES.items():
            flags = data.get("flags", [])
            # Only flags[0] is the documented encounter "Defeated" trigger flag.
            # Remaining flags are side effects (stat counters, reward pickups,
            # grace unlocks) and are not reliable defeat indicators on their own.
            defeated = bool(flags) and self.current_event_flags.get_flag(flags[0])
            all_entries.append(
                (
                    boss_name,
                    data.get("category", ""),
                    "Defeated" if defeated else "Alive",
                )
            )

        defeated_count = sum(1 for _, _, s in all_entries if s == "Defeated")
        total_count = len(all_entries)

        filter_frame = ds.box(main, pady=(10, 8))

        ctk.CTkLabel(filter_frame, text="Show", font=ds.FONT).pack(
            side=tk.LEFT, padx=(12, 8), pady=10
        )
        status_filter_var = tk.StringVar(value="All")
        patch_combo_scroll(
            ctk.CTkComboBox(
                filter_frame,
                variable=status_filter_var,
                values=["All", "Defeated", "Alive"],
                state="readonly",
                width=130,
                font=ds.FONT,
                dropdown_font=ds.FONT,
                command=lambda _v: _refresh(),
            )
        ).pack(side=tk.LEFT, padx=(0, 20), pady=10)

        ctk.CTkLabel(filter_frame, text="Region", font=ds.FONT).pack(
            side=tk.LEFT, padx=(0, 8), pady=10
        )
        region_filter_var = tk.StringVar(value="All")
        patch_combo_scroll(
            ctk.CTkComboBox(
                filter_frame,
                variable=region_filter_var,
                values=["All", *BOSS_CATEGORIES],
                state="readonly",
                width=260,
                font=ds.FONT,
                dropdown_font=ds.FONT,
                command=lambda _v: _refresh(),
            )
        ).pack(side=tk.LEFT, pady=10)

        summary_label = ctk.CTkLabel(main, text="", font=ds.FONT)
        summary_label.pack(anchor="w", pady=(0, 4))

        tree_frame, tree = ds.themed_tree(
            main,
            columns=("status", "boss", "region"),
            show="headings",
            selectmode="none",
        )
        tree.heading("status", text="Status")
        tree.heading("boss", text="Boss")
        tree.heading("region", text="Region")
        tree.column("status", width=90, anchor="w", stretch=False)
        tree.column("boss", width=330, anchor="w")
        tree.column("region", width=230, anchor="w")

        tree.tag_configure("defeated", foreground=palette.pick(palette.RED_TEXT))
        tree.tag_configure("alive", foreground=palette.pick(palette.GREEN_TEXT))
        tree_frame.pack(fill=tk.BOTH, expand=True)
        # Tracks current sort: col -> ascending bool
        sort_state: dict[str, bool] = {}

        def _sort(col: str):
            asc = not sort_state.get(col, False)
            sort_state[col] = asc
            rows = [(tree.set(iid, col), iid) for iid in tree.get_children()]
            rows.sort(key=lambda x: x[0].lower(), reverse=not asc)
            for i, (_, iid) in enumerate(rows):
                tree.move(iid, "", i)

        tree.heading("status", text="Status", command=lambda: _sort("status"))
        tree.heading("boss", text="Boss", command=lambda: _sort("boss"))
        tree.heading("region", text="Region", command=lambda: _sort("region"))

        def _refresh():
            tree.delete(*tree.get_children())
            s_filter = status_filter_var.get()
            r_filter = region_filter_var.get()
            shown = 0
            for boss_name, category, status in all_entries:
                if r_filter != "All" and category != r_filter:
                    continue
                if s_filter != "All" and status != s_filter:
                    continue
                tag = "defeated" if status == "Defeated" else "alive"
                tree.insert(
                    "", "end", values=(status, boss_name, category), tags=(tag,)
                )
                shown += 1
            summary_label.configure(
                text=f"{defeated_count} / {total_count} bosses defeated  -  showing {shown}"
            )
            sort_state.clear()

        _refresh()
        ds.finish(dialog, self.parent, width=720, height=640)

    @reopenable
    def open_boss_respawn(self):
        """Open boss respawn dialog"""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, "Boss Respawn / Kill")
        dialog.resizable(True, True)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))

        ds.header(main, "Boss Respawn / Kill", font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main,
            text="Clear defeat flags to respawn a boss, or set them to mark it defeated.",
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(anchor="w", pady=(2, 10))

        cat_frame = ds.box(main, pady=(0, 8))
        ctk.CTkLabel(cat_frame, text="Category", font=ds.FONT).pack(
            side=tk.LEFT, padx=(12, 8), pady=10
        )

        boss_category_var = tk.StringVar(value=BOSS_CATEGORIES[0])
        cat_combo = ctk.CTkComboBox(
            cat_frame,
            variable=boss_category_var,
            values=BOSS_CATEGORIES,
            state="readonly",
            width=300,
            font=ds.FONT,
            dropdown_font=ds.FONT,
        )
        patch_combo_scroll(cat_combo)
        cat_combo.pack(side=tk.LEFT, pady=10)

        boss_frame = ctk.CTkScrollableFrame(main, fg_color=ds.BOX, corner_radius=8)
        boss_frame.pack(fill=tk.BOTH, expand=True)
        bind_mousewheel(boss_frame)

        boss_vars = {}

        def populate_bosses(*_args):
            for widget in boss_frame.winfo_children():
                widget.destroy()
            boss_vars.clear()

            category = boss_category_var.get()
            bosses_in_cat = get_bosses_by_category(category)

            for boss_name in bosses_in_cat:
                flags = get_boss_flags(boss_name)
                if not flags:
                    continue

                is_defeated = self.current_event_flags.get_flag(flags[0])
                var = tk.BooleanVar(value=False)
                boss_vars[boss_name] = (flags, var)

                item_frame = ctk.CTkFrame(boss_frame, fg_color="transparent")
                item_frame.pack(fill=tk.X, pady=1, padx=4)
                ctk.CTkCheckBox(
                    item_frame, text=boss_name, variable=var, font=ds.FONT
                ).pack(side=tk.LEFT, padx=8, pady=3)
                ctk.CTkLabel(
                    item_frame,
                    text="Defeated" if is_defeated else "Alive",
                    font=ds.SMALL,
                    text_color=ds.ERROR if is_defeated else ds.FOUND,
                ).pack(side=tk.RIGHT, padx=12)

        cat_combo.configure(command=populate_bosses)
        populate_bosses()

        def respawn_selected():
            """Respawn selected bosses"""
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path",
                    "Could not locate the save file to back up. Load a valid save (.sl2) first.",
                )
                return

            count = 0
            for flags, var in boss_vars.values():
                if var.get():  # user explicitly selected this boss
                    is_defeated_now = self.current_event_flags.get_flag(flags[0])
                    if is_defeated_now:
                        for flag_id in flags:
                            self.current_event_flags.set_flag(flag_id, False)
                        count += 1

            if count == 0:
                notify(
                    dialog,
                    "No valid selections. Select defeated bosses to respawn.",
                    "warning",
                )
                return

            save_file = self.get_save_file()

            if save_path and save_path.is_file():
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        description=f"Before boss respawn (Slot {self.current_slot + 1})",
                        operation="respawn_boss",
                        save=save_file,
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied)."
                        " Continuing without backup.",
                    )
            else:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup because the save path is not a file."
                    " Proceeding without backup.",
                )

            # Write to raw data and recalculate checksums
            slot = save_file.character_slots[self.current_slot]

            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                absolute_offset = slot.event_flags_offset
                event_flags_size = 0x1BF99F
                save_file._raw_data[
                    absolute_offset : absolute_offset + event_flags_size
                ] = slot.event_flags

            save_file.recalculate_checksums()
            save_file.save(self.get_save_path())
            self.reload_save()

            # Teleport to Roundtable Hold
            try:
                from er_save_manager.fixes.teleport import TeleportFix

                teleport = TeleportFix("roundtable")
                result = teleport.apply(save_file, self.current_slot)
                if result.applied:
                    save_file.recalculate_checksums()
                    save_file.save(self.get_save_path())
                    self.reload_save()
            except Exception as e:
                CTkMessageBox.showwarning(
                    "Teleport Failed",
                    f"Could not teleport to Roundtable Hold: {e}",
                    parent=dialog,
                )

            self.show_toast("Boss respawned successfully", duration=2500)
            dialog.destroy()

        def respawn_all():
            """Respawn all bosses in category"""
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path",
                    "Could not locate the save file to back up. Load a valid save (.sl2) first.",
                    parent=dialog,
                )
                return

            result = CTkMessageBox.askyesno(
                "Respawn All Bosses",
                f"Respawn ALL bosses in {boss_category_var.get()}?\n\n"
                f"This will reset {len(boss_vars)} boss(es).",
                parent=dialog,
            )

            if not result:
                return

            count = 0
            for flags, _var in boss_vars.values():
                for flag_id in flags:
                    self.current_event_flags.set_flag(flag_id, False)
                count += 1

            save_file = self.get_save_file()

            save_path = self.get_save_path()
            if save_path and save_path.is_file():
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        description=f"Before respawn all ({boss_category_var.get()}, Slot {self.current_slot + 1})",
                        operation="respawn_all_bosses",
                        save=save_file,
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied)."
                        " Continuing without backup.",
                        parent=dialog,
                    )
            else:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup because the save path is not a file."
                    " Proceeding without backup.",
                    parent=dialog,
                )

            # Write to raw data and recalculate checksums
            slot = save_file.character_slots[self.current_slot]

            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                absolute_offset = slot.event_flags_offset
                event_flags_size = 0x1BF99F
                save_file._raw_data[
                    absolute_offset : absolute_offset + event_flags_size
                ] = slot.event_flags

            save_file.recalculate_checksums()
            save_file.save(self.get_save_path())
            self.reload_save()

            # Teleport to Roundtable Hold
            try:
                from er_save_manager.fixes.teleport import TeleportFix

                teleport = TeleportFix("roundtable")
                result = teleport.apply(save_file, self.current_slot)
                if result.applied:
                    save_file.recalculate_checksums()
                    save_file.save(self.get_save_path())
                    self.reload_save()
            except Exception as e:
                CTkMessageBox.showwarning(
                    "Teleport Failed",
                    f"Could not teleport to Roundtable Hold: {e}",
                    parent=dialog,
                )

            self.show_toast(
                f"Respawned all {count} bosses in {boss_category_var.get()}",
                duration=2500,
            )
            dialog.destroy()

        def kill_selected():
            """Kill selected bosses (set defeat flags true)"""
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path",
                    "Could not locate the save file to back up. Load a valid save (.sl2) first.",
                )
                return

            count = 0
            for flags, var in boss_vars.values():
                if var.get():  # user explicitly selected this boss
                    is_defeated_now = self.current_event_flags.get_flag(flags[0])
                    if not is_defeated_now:
                        for flag_id in flags:
                            self.current_event_flags.set_flag(flag_id, True)
                        count += 1

            if count == 0:
                notify(
                    dialog,
                    "No valid selections. Select alive bosses to kill.",
                    "warning",
                )
                return

            save_file = self.get_save_file()

            if save_path and save_path.is_file():
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        description=f"Before boss kill (Slot {self.current_slot + 1})",
                        operation="kill_boss",
                        save=save_file,
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied)."
                        " Continuing without backup.",
                    )
            else:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup because the save path is not a file."
                    " Proceeding without backup.",
                )

            # Write to raw data and recalculate checksums
            slot = save_file.character_slots[self.current_slot]

            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                absolute_offset = slot.event_flags_offset
                event_flags_size = 0x1BF99F
                save_file._raw_data[
                    absolute_offset : absolute_offset + event_flags_size
                ] = slot.event_flags

            save_file.recalculate_checksums()
            save_file.save(self.get_save_path())
            self.reload_save()

            # Teleport to Roundtable Hold to force area reload so the game
            # re-evaluates NPC spawn conditions against the new flag state
            try:
                from er_save_manager.fixes.teleport import TeleportFix

                teleport = TeleportFix("roundtable")
                result = teleport.apply(save_file, self.current_slot)
                if result.applied:
                    save_file.recalculate_checksums()
                    save_file.save(self.get_save_path())
                    self.reload_save()
            except Exception as e:
                CTkMessageBox.showwarning(
                    "Teleport Failed",
                    f"Could not teleport to Roundtable Hold: {e}",
                    parent=dialog,
                )

            self.show_toast("Boss killed successfully", duration=2500)
            dialog.destroy()

        def kill_all():
            """Kill all bosses in category (set all defeat flags true)"""
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path",
                    "Could not locate the save file to back up. Load a valid save (.sl2) first.",
                    parent=dialog,
                )
                return

            result = CTkMessageBox.askyesno(
                "Kill All Bosses",
                f"Kill ALL bosses in {boss_category_var.get()}?\n\n"
                f"This will mark {len(boss_vars)} boss(es) as defeated.",
                parent=dialog,
            )

            if not result:
                return

            count = 0
            for flags, _var in boss_vars.values():
                for flag_id in flags:
                    self.current_event_flags.set_flag(flag_id, True)
                count += 1

            save_file = self.get_save_file()

            save_path = self.get_save_path()
            if save_path and save_path.is_file():
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        description=f"Before kill all ({boss_category_var.get()}, Slot {self.current_slot + 1})",
                        operation="kill_all_bosses",
                        save=save_file,
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied)."
                        " Continuing without backup.",
                        parent=dialog,
                    )
            else:
                CTkMessageBox.showwarning(
                    "Backup Skipped",
                    "Could not create backup because the save path is not a file."
                    " Proceeding without backup.",
                    parent=dialog,
                )

            # Write to raw data and recalculate checksums
            slot = save_file.character_slots[self.current_slot]

            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                absolute_offset = slot.event_flags_offset
                event_flags_size = 0x1BF99F
                save_file._raw_data[
                    absolute_offset : absolute_offset + event_flags_size
                ] = slot.event_flags

            save_file.recalculate_checksums()
            save_file.save(self.get_save_path())
            self.reload_save()

            # Teleport to Roundtable Hold to force area reload so the game
            # re-evaluates NPC spawn conditions against the new flag state
            try:
                from er_save_manager.fixes.teleport import TeleportFix

                teleport = TeleportFix("roundtable")
                result = teleport.apply(save_file, self.current_slot)
                if result.applied:
                    save_file.recalculate_checksums()
                    save_file.save(self.get_save_path())
                    self.reload_save()
            except Exception as e:
                CTkMessageBox.showwarning(
                    "Teleport Failed",
                    f"Could not teleport to Roundtable Hold: {e}",
                    parent=dialog,
                )

            self.show_toast(
                f"Killed all {count} bosses in {boss_category_var.get()}",
                duration=2500,
            )
            dialog.destroy()

        # Kill on the left, respawn and close on the right
        ds.button(
            btn_frame, "Kill Selected", kill_selected, primary=False, width=110
        ).pack(side=tk.LEFT)
        ds.button(
            btn_frame, "Kill All in Category", kill_all, primary=False, width=150
        ).pack(side=tk.LEFT, padx=(8, 0))
        ds.button(btn_frame, "Close", dialog.destroy, primary=False).pack(side=tk.RIGHT)
        ds.button(
            btn_frame, "Respawn All in Category", respawn_all, primary=False, width=180
        ).pack(side=tk.RIGHT, padx=(0, 8))
        ds.button(btn_frame, "Respawn Selected", respawn_selected, width=140).pack(
            side=tk.RIGHT, padx=(0, 8)
        )
        ds.finish(dialog, self.parent, width=860, height=600)

    @reopenable
    def open_npc_revival(self):
        """Open NPC revival dialog"""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.data.npc_data import (
            get_all_npcs,
            get_npc_location,
            get_npc_state,
            revive_npc,
        )
        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, "NPC Revival")
        dialog.resizable(True, True)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))

        ds.header(main, "NPC Revival", font=ds.TITLE_LARGE)
        ctk.CTkLabel(
            main,
            text="Revive dead NPCs. Quest progress is not restored.",
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(anchor="w", pady=(2, 10))

        tree_frame, tree = ds.themed_tree(
            main,
            columns=("npc", "location", "status"),
            show="headings",
            selectmode="extended",
        )
        tree.heading("npc", text="NPC")
        tree.heading("location", text="Location")
        tree.heading("status", text="Status")
        tree.column("npc", width=260, anchor="w")
        tree.column("location", width=300, anchor="w")
        tree.column("status", width=90, anchor="w", stretch=False)
        for status, color in (
            ("Dead", palette.RED_TEXT),
            ("Hostile", palette.WARNING_TEXT),
            ("Alive", palette.GREEN_TEXT),
        ):
            tree.tag_configure(status, foreground=palette.pick(color))
        tree_frame.pack(fill=tk.BOTH, expand=True)
        add_tooltip(tree, MULTI_SELECT_TIP)
        for npc_name in get_all_npcs():
            location = get_npc_location(npc_name)
            state = get_npc_state(self.current_event_flags, npc_name)
            if not state:
                continue

            is_dead = state["dead"]
            is_aggro = state["aggro_absolvable"] or state["aggro_permanent"]

            if is_dead:
                status = "Dead"
            elif is_aggro:
                status = "Hostile"
            elif state["vanished"]:
                status = "Vanished"
            else:
                status = "Alive"

            tree.insert(
                "",
                "end",
                iid=npc_name,
                values=(npc_name, location, status),
                tags=(status,),
            )

        def revive_selected():
            """Revive selected NPCs"""
            save_path = self.get_save_path()
            if not save_path or not save_path.is_file():
                CTkMessageBox.showerror(
                    "Invalid Save Path",
                    "Could not locate save file. Load a valid save first.",
                    parent=dialog,
                )
                return

            count = 0
            for npc_name in tree.selection():
                if revive_npc(self.current_event_flags, npc_name):
                    count += 1

            if count == 0:
                notify(dialog, "No NPCs selected for revival.", "warning")
                return

            save_file = self.get_save_file()
            if save_path:
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        description=f"Before NPC revival (Slot {self.current_slot + 1})",
                        operation="npc_revival",
                        save=save_file,
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied).",
                        parent=dialog,
                    )

            # Write to raw data and save
            slot = save_file.character_slots[self.current_slot]
            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                absolute_offset = slot.event_flags_offset
                event_flags_size = 0x1BF99F
                save_file._raw_data[
                    absolute_offset : absolute_offset + event_flags_size
                ] = slot.event_flags

            save_file.recalculate_checksums()
            save_file.save(self.get_save_path())
            self.reload_save()

            self.show_toast(f"Revived {count} NPC(s)", duration=2500)
            dialog.destroy()

        ds.button(btn_frame, "Close", dialog.destroy, primary=False).pack(side=tk.RIGHT)
        ds.button(btn_frame, "Revive Selected", revive_selected, width=130).pack(
            side=tk.RIGHT, padx=(0, 8)
        )
        ds.finish(dialog, self.parent, width=760, height=600)

    @reopenable
    def open_quest_progress(self):
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui.quest_progress_dialog import QuestProgressDialog

        QuestProgressDialog.open(
            self.parent,
            self.current_event_flags,
            self.get_save_file(),
            self.get_save_path(),
            self.current_slot,
            self.reload_save,
            self.show_toast,
        )

    @reopenable
    def open_grace_dialog(self):
        """Open the sites of grace unlock/lock dialog."""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui.grace_dialog import GraceDialog

        GraceDialog.open(
            self.parent,
            self.current_event_flags,
            self.get_save_file(),
            self.get_save_path(),
            self.current_slot,
            self.reload_save,
            self.show_toast,
        )

    @reopenable
    def open_item_pickups(self):
        """Open the collected/missed item pickup checklist."""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui.item_pickups_dialog import ItemPickupsDialog

        ItemPickupsDialog.open(
            self.parent,
            self.current_event_flags,
            self.get_save_file(),
            self.get_save_path(),
            self.current_slot,
            self.reload_save,
            self.show_toast,
        )

    @reopenable
    def open_merchant_restock(self):
        """Open the limited merchant stock restock dialog."""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui.merchant_restock_dialog import MerchantRestockDialog

        MerchantRestockDialog.open(
            self.parent,
            self.current_event_flags,
            self.get_save_file(),
            self.get_save_path(),
            self.current_slot,
            self.reload_save,
            self.show_toast,
        )

    @reopenable
    def open_summoning_pools(self):
        """Open the summoning pool enable/disable dialog."""
        if self.current_event_flags is None:
            notify(self.parent, "Load event flags for a character first.", "warning")
            return

        from er_save_manager.ui import dialog_style as ds

        dialog = ds.create(self.parent, "Summoning Pools")
        dialog.resizable(True, True)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))

        header = ds.header(main, "Summoning Pools", font=ds.TITLE_LARGE)
        sel_frame = ctk.CTkFrame(header, fg_color="transparent")
        sel_frame.pack(side=tk.RIGHT)
        ctk.CTkLabel(
            main,
            text="Enable or disable summoning pool activation flags.",
            font=ds.SMALL,
            text_color=ds.MUTED,
        ).pack(anchor="w", pady=(2, 10))

        tree_frame, tree = ds.themed_tree(
            main,
            columns=("flag", "status"),
            show="tree headings",
            selectmode="extended",
        )
        tree.heading("#0", text="Pool")
        tree.heading("flag", text="Flag")
        tree.heading("status", text="Status")
        tree.column("#0", width=420, anchor="w")
        tree.column("flag", width=110, anchor="w", stretch=False)
        tree.column("status", width=90, anchor="w", stretch=False)
        tree.tag_configure("active", foreground=palette.pick(palette.GREEN_TEXT))
        tree_frame.pack(fill=tk.BOTH, expand=True)
        add_tooltip(tree, MULTI_SELECT_TIP)
        # Row iids are the flag ids; group rows use these keys
        groups = {
            "base": ("Base Game", SUMMONING_POOL_FLAGS_BASE),
            "dlc": ("Shadow of the Erdtree (DLC)", SUMMONING_POOL_FLAGS_DLC),
        }
        for key, (title, pools) in groups.items():
            tree.insert("", "end", iid=key, text=title, open=True)
            for flag_id, label in pools:
                is_active = self.current_event_flags.get_flag(flag_id)
                tree.insert(
                    key,
                    "end",
                    iid=str(flag_id),
                    text=label,
                    values=(flag_id, "Active" if is_active else "Inactive"),
                    tags=("active",) if is_active else (),
                )

        def select_group(group: str) -> None:
            tree.selection_add(tree.get_children(group))

        def select_all() -> None:
            for key in groups:
                tree.selection_add(tree.get_children(key))

        def unselect_all() -> None:
            tree.selection_set(())

        for text, cmd in (
            ("Base", lambda: select_group("base")),
            ("DLC", lambda: select_group("dlc")),
            ("All", select_all),
            ("None", unselect_all),
        ):
            ds.button(sel_frame, text, cmd, primary=False, width=60, height=26).pack(
                side=tk.LEFT, padx=(6, 0)
            )

        def _apply(state: bool) -> None:
            selected = [int(iid) for iid in tree.selection() if iid not in groups]
            if not selected:
                notify(dialog, "No pools selected.", "warning")
                return

            action = "Enable" if state else "Disable"
            result = CTkMessageBox.askyesno(
                "Change Summoning Pools",
                f"{action} {len(selected)} summoning pool flags on Slot {self.current_slot + 1}?\n\n"
                "A backup will be created automatically.",
                parent=dialog,
            )
            if not result:
                return

            save_file = self.get_save_file()
            save_path = self.get_save_path()

            if save_path and save_path.is_file():
                try:
                    backup_mgr = BackupManager(save_path)
                    backup_mgr.create_backup(
                        description=f"Before summoning pool {action.lower()} (Slot {self.current_slot + 1})",
                        operation="summoning_pools",
                        save=save_file,
                    )
                except PermissionError:
                    CTkMessageBox.showwarning(
                        "Backup Skipped",
                        "Could not create backup (permission denied). Continuing without backup.",
                        parent=dialog,
                    )

            for flag_id in selected:
                self.current_event_flags.set_flag(flag_id, state)

            slot = save_file.character_slots[self.current_slot]
            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                absolute_offset = slot.event_flags_offset
                event_flags_size = 0x1BF99F
                save_file._raw_data[
                    absolute_offset : absolute_offset + event_flags_size
                ] = slot.event_flags

            save_file.recalculate_checksums()
            save_file.save(self.get_save_path())
            self.reload_save()

            self.show_toast(
                f"{action}d {len(selected)} summoning pool flags on Slot {self.current_slot + 1}",
                duration=2500,
            )
            dialog.destroy()

        ds.button(btn_frame, "Close", dialog.destroy, primary=False).pack(side=tk.RIGHT)
        ds.button(
            btn_frame,
            "Disable Selected",
            lambda: _apply(False),
            primary=False,
            width=140,
        ).pack(side=tk.RIGHT, padx=(0, 8))
        ds.button(btn_frame, "Enable Selected", lambda: _apply(True), width=140).pack(
            side=tk.RIGHT, padx=(0, 8)
        )
        ds.finish(dialog, self.parent, width=720, height=640)
