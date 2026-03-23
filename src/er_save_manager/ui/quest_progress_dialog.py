"""
Quest Progress Dialog
View and modify NPC quest progress via event flags.
Each quest step shows its completion state and can be applied individually.
"""

import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel, force_render_dialog


class QuestProgressDialog:
    """
    Dialog for viewing and modifying NPC quest progress.

    Reads/writes event flags via an accessor that has get_flag(id) -> bool
    and set_flag(id, state) methods.
    """

    @staticmethod
    def open(
        parent,
        event_flag_accessor,
        save_file,
        save_path,
        slot_idx,
        reload_callback,
        show_toast,
    ):
        from er_save_manager.data.quest_flags_db import QUEST_FLAGS

        dialog = ctk.CTkToplevel(parent)
        dialog.title("Quest Progress")
        width, height = 900, 650
        dialog.transient(parent)
        dialog.update_idletasks()
        parent.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.resizable(True, True)
        force_render_dialog(dialog)
        dialog.grab_set()

        # ---- Top bar ----
        top_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        top_frame.pack(fill=tk.X, padx=14, pady=(12, 0))

        ctk.CTkLabel(
            top_frame,
            text="Quest Progress",
            font=("Segoe UI", 15, "bold"),
        ).pack(side=tk.LEFT)

        search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(
            top_frame,
            textvariable=search_var,
            placeholder_text="Search NPCs or steps...",
            width=220,
        )
        search_entry.pack(side=tk.RIGHT)

        # ---- Main split layout ----
        split = ctk.CTkFrame(dialog, fg_color="transparent")
        split.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)
        split.columnconfigure(0, weight=0, minsize=200)
        split.columnconfigure(1, weight=1)
        split.rowconfigure(0, weight=1)

        # ---- NPC list (left panel) ----
        npc_list_frame = ctk.CTkScrollableFrame(split, width=195, corner_radius=8)
        npc_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        bind_mousewheel(npc_list_frame)

        # ---- Steps panel (right panel) ----
        steps_outer = ctk.CTkFrame(split, corner_radius=8)
        steps_outer.grid(row=0, column=1, sticky="nsew")
        steps_outer.rowconfigure(1, weight=1)
        steps_outer.columnconfigure(0, weight=1)

        npc_header = ctk.CTkLabel(
            steps_outer,
            text="Select an NPC",
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        )
        npc_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        steps_scroll = ctk.CTkScrollableFrame(
            steps_outer, corner_radius=0, fg_color="transparent"
        )
        steps_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        bind_mousewheel(steps_scroll)

        # ---- Bottom bar ----
        bottom = ctk.CTkFrame(dialog, fg_color="transparent")
        bottom.pack(fill=tk.X, padx=14, pady=(0, 12))

        apply_all_btn = ctk.CTkButton(
            bottom,
            text="Apply All Steps to Here",
            width=180,
            state="disabled",
        )
        apply_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        reset_btn = ctk.CTkButton(
            bottom,
            text="Reset All Quest Flags",
            width=160,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray25"),
            state="disabled",
        )
        reset_btn.pack(side=tk.LEFT)

        ctk.CTkButton(bottom, text="Close", command=dialog.destroy, width=100).pack(
            side=tk.RIGHT
        )

        # ---- State ----
        selected_npc = tk.StringVar(value="")
        npc_buttons = {}
        step_widgets = []  # list of (step_dict, completion_label, apply_btn)

        def _safe_get_flag(flag_id):
            try:
                return event_flag_accessor.get_flag(flag_id)
            except (ValueError, KeyError):
                return False

        def _step_is_complete(step):
            return all(
                bool(_safe_get_flag(f["id"])) == bool(f["value"]) for f in step["flags"]
            )

        def _count_complete(npc_name):
            steps = QUEST_FLAGS[npc_name]
            return sum(1 for s in steps if _step_is_complete(s)), len(steps)

        def _render_steps(npc_name):
            # Clear old widgets
            for w in steps_scroll.winfo_children():
                w.destroy()
            step_widgets.clear()

            steps = QUEST_FLAGS[npc_name]
            done, total = _count_complete(npc_name)
            npc_header.configure(text=f"{npc_name}  ({done}/{total} steps complete)")

            for i, step in enumerate(steps):
                complete = _step_is_complete(step)
                color = ("#f0fdf4", "#0f2318") if complete else ("#ffffff", "#1a1a2e")
                border = ("#86efac", "#166534") if complete else ("#e2e8f0", "#2d2d44")

                row_frame = ctk.CTkFrame(
                    steps_scroll,
                    corner_radius=6,
                    fg_color=color,
                    border_color=border,
                    border_width=1,
                )
                row_frame.pack(fill=tk.X, pady=3, padx=2)
                row_frame.columnconfigure(1, weight=1)

                # Step number + status indicator
                status_char = "✓" if complete else str(i + 1)
                status_color = (
                    ("#16a34a", "#4ade80") if complete else ("gray50", "gray60")
                )
                ctk.CTkLabel(
                    row_frame,
                    text=status_char,
                    font=("Segoe UI", 12, "bold"),
                    text_color=status_color,
                    width=28,
                ).grid(row=0, column=0, rowspan=2, padx=(8, 4), pady=6, sticky="n")

                # Description
                ctk.CTkLabel(
                    row_frame,
                    text=step["description"],
                    font=("Segoe UI", 11),
                    anchor="w",
                    justify="left",
                    wraplength=490,
                ).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(6, 0))

                # Location + flag count
                meta_parts = []
                if step["location"]:
                    meta_parts.append(step["location"])
                meta_parts.append(f"{len(step['flags'])} flag(s)")
                ctk.CTkLabel(
                    row_frame,
                    text="  |  ".join(meta_parts),
                    font=("Segoe UI", 10),
                    text_color=("gray50", "gray60"),
                    anchor="w",
                ).grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 6))

                # Apply button
                btn_text = "Applied" if complete else "Apply"
                btn_state = "disabled" if complete else "normal"
                apply_btn = ctk.CTkButton(
                    row_frame,
                    text=btn_text,
                    width=70,
                    state=btn_state,
                    command=lambda s=step, npc=npc_name: _apply_step(s, npc),
                )
                apply_btn.grid(row=0, column=2, rowspan=2, padx=8, pady=6)

                step_widgets.append((step, apply_btn))

            # Enable bottom buttons
            apply_all_btn.configure(
                state="normal",
                command=lambda: _apply_up_to_last_complete(npc_name),
            )
            reset_btn.configure(
                state="normal",
                command=lambda: _reset_quest(npc_name),
            )

        def _safe_set_flag(flag_id, value):
            try:
                event_flag_accessor.set_flag(flag_id, value)
            except (ValueError, KeyError):
                pass

        def _apply_step(step, npc_name):
            """Apply a single quest step's flags."""
            for f in step["flags"]:
                _safe_set_flag(f["id"], bool(f["value"]))
            _save_and_refresh(npc_name, f"Applied: {step['description'][:60]}")

        def _apply_up_to_last_complete(npc_name):
            """
            Apply all steps up to and including the last currently-complete step,
            effectively syncing the save to the furthest known progress point.
            Asks confirmation first.
            """
            steps = QUEST_FLAGS[npc_name]
            # Find furthest complete step index
            last_complete = -1
            for i, step in enumerate(steps):
                if _step_is_complete(step):
                    last_complete = i

            if last_complete < 0:
                # None complete — ask if user wants to apply all or just the first
                if not CTkMessageBox.askyesno(
                    "No Complete Steps",
                    f"No steps are currently complete for {npc_name}.\n\nApply the first step only?",
                    parent=dialog,
                ):
                    return
                last_complete = 0

            target = last_complete
            steps_to_apply = steps[: target + 1]
            if not CTkMessageBox.askyesno(
                "Apply Quest Progress",
                f'Apply {len(steps_to_apply)} step(s) for {npc_name} up to:\n\n"{steps[target]["description"][:80]}"\n\nA backup will be created.',
                parent=dialog,
            ):
                return

            for step in steps_to_apply:
                for f in step["flags"]:
                    _safe_set_flag(f["id"], bool(f["value"]))

            _save_and_refresh(
                npc_name, f"Applied {len(steps_to_apply)} quest step(s) for {npc_name}"
            )

        def _reset_quest(npc_name):
            """Reset all flags for this NPC's quest to 0."""
            if not CTkMessageBox.askyesno(
                "Reset Quest",
                f"Reset ALL event flags for {npc_name}'s quest to 0?\n\nThis will undo all tracked quest progress. A backup will be created.",
                parent=dialog,
            ):
                return

            steps = QUEST_FLAGS[npc_name]
            seen = set()
            for step in steps:
                for f in step["flags"]:
                    if f["id"] not in seen:
                        _safe_set_flag(f["id"], False)
                        seen.add(f["id"])

            _save_and_refresh(npc_name, f"Reset quest flags for {npc_name}")

        def _save_and_refresh(npc_name, toast_msg):
            """Write changes, recalculate checksums, save, and re-render."""
            from er_save_manager.backup.manager import BackupManager

            if save_path and save_path.is_file():
                try:
                    BackupManager(save_path).create_backup(
                        description=f"before_quest_edit_slot_{slot_idx + 1}",
                        operation="quest_progress_edit",
                        save=save_file,
                    )
                except Exception:
                    pass

            # Write event flags buffer back to raw data
            slot = save_file.character_slots[slot_idx]
            if hasattr(slot, "event_flags_offset") and slot.event_flags_offset > 0:
                off = slot.event_flags_offset
                size = 0x1BF99F
                save_file._raw_data[off : off + size] = slot.event_flags

            save_file.recalculate_checksums()
            if save_path and save_path.is_file():
                save_file.to_file(save_path)

            if reload_callback:
                reload_callback()

            if show_toast:
                show_toast(toast_msg, duration=2500)

            # Re-render step list with fresh flag states
            _render_steps(npc_name)
            _rebuild_npc_list(search_var.get())

        # ---- NPC button rendering ----
        def _rebuild_npc_list(query=""):
            for w in npc_list_frame.winfo_children():
                w.destroy()
            npc_buttons.clear()

            query = query.lower().strip()
            active = selected_npc.get()

            for npc_name in sorted(QUEST_FLAGS.keys()):
                if query and query not in npc_name.lower():
                    # Also check if any step description matches
                    steps = QUEST_FLAGS[npc_name]
                    if not any(
                        query in (s["description"] or "").lower() for s in steps
                    ):
                        continue

                done, total = _count_complete(npc_name)
                done / total if total else 0

                is_active = npc_name == active
                bg = ("#e0e7ff", "#1e1b4b") if is_active else "transparent"

                btn_frame = ctk.CTkFrame(npc_list_frame, fg_color=bg, corner_radius=6)
                btn_frame.pack(fill=tk.X, pady=2)

                ctk.CTkLabel(
                    btn_frame,
                    text=npc_name,
                    font=("Segoe UI", 12, "bold" if is_active else "normal"),
                    anchor="w",
                ).pack(fill=tk.X, padx=8, pady=(4, 0))

                ctk.CTkLabel(
                    btn_frame,
                    text=f"{done}/{total} steps",
                    font=("Segoe UI", 10),
                    text_color=("gray50", "gray60"),
                    anchor="w",
                ).pack(fill=tk.X, padx=8, pady=(0, 4))

                btn_frame.bind("<Button-1>", lambda e, n=npc_name: _select_npc(n))
                for child in btn_frame.winfo_children():
                    child.bind("<Button-1>", lambda e, n=npc_name: _select_npc(n))

                npc_buttons[npc_name] = btn_frame

        def _select_npc(npc_name):
            selected_npc.set(npc_name)
            _rebuild_npc_list(search_var.get())
            _render_steps(npc_name)

        def _on_search(*_):
            _rebuild_npc_list(search_var.get())

        search_var.trace_add("write", _on_search)
        _rebuild_npc_list()
