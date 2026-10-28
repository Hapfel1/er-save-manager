"""
Quest Progress Dialog
View and modify NPC quest progress via event flags.
Each quest step shows its completion state and can be applied individually.
"""

import contextlib
import tkinter as tk

import customtkinter as ctk

from er_save_manager.ui import dialog_style as ds
from er_save_manager.ui import palette
from er_save_manager.ui.messagebox import CTkMessageBox
from er_save_manager.ui.utils import bind_mousewheel


def last_complete_index(steps, is_complete) -> int:
    """Index of the furthest step whose flags all match, -1 if none."""
    return max((i for i, s in enumerate(steps) if is_complete(s)), default=-1)


def steps_up_to(steps, target: int, is_complete) -> list[dict]:
    """Steps after the furthest complete one up to and including target, in
    table order. A table whose map events build on the previous state (DS3)
    needs every step in between applied, not only the target."""
    start = last_complete_index(steps, is_complete) + 1
    return steps[min(start, target) : target + 1]


def is_tracked(step) -> bool:
    """A step that only clears flags matches a quest that never reached it
    as well, so its state cannot be read from the save."""
    return any(f["value"] for f in step["flags"])


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
        quest_flags=None,
        commit=None,
        apply_steps_between=False,
        undo=False,
        apply_all=True,
    ):
        """quest_flags: NPC -> steps table (default: the Elden Ring table).
        commit(description): backs up and writes the save for games other
        than Elden Ring; raises on failure. A failure it already reported
        (write_failed, which reloads the save) is raised chained to the
        original error (raise ... from exc): the dialog, now editing a
        stale save, then closes without a second message. Without commit
        the Elden Ring slot buffer is written back. apply_steps_between: Apply also applies the
        steps between the furthest complete step and the chosen one.
        undo: applied steps get an Undo button that clears the flags they
        set, for tables whose steps are independent flags (DS2).
        apply_all: show Apply All Steps to Here; it re-applies every step up
        to the furthest complete one, which only helps a table whose steps
        keep their flags as the quest moves on (Elden Ring)."""
        if quest_flags is None:
            from er_save_manager.data.quest_flags_db import QUEST_FLAGS

            quest_flags = QUEST_FLAGS
        QUEST_FLAGS = quest_flags

        dialog = ds.create(parent, "Quest Progress")
        dialog.resizable(True, True)
        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        # ---- Bottom bar (packed first so a short window shrinks the lists) ----
        bottom = ctk.CTkFrame(main, fg_color="transparent")
        bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        apply_all_btn = ds.button(
            bottom, "Apply All Steps to Here", None, width=180, state="disabled"
        )
        if apply_all:
            apply_all_btn.pack(side=tk.LEFT, padx=(0, 8))
        reset_btn = ds.button(
            bottom,
            "Reset All Quest Flags",
            None,
            primary=False,
            width=160,
            state="disabled",
        )
        reset_btn.pack(side=tk.LEFT)
        ds.button(bottom, "Close", dialog.destroy, primary=False).pack(side=tk.RIGHT)

        # ---- Header ----
        top_frame = ctk.CTkFrame(main, fg_color="transparent")
        top_frame.pack(fill=tk.X)
        ctk.CTkLabel(top_frame, text="Quest Progress", font=ds.TITLE_LARGE).pack(
            side=tk.LEFT
        )
        search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(
            top_frame,
            textvariable=search_var,
            placeholder_text="Search NPCs or steps...",
            width=240,
            height=32,
            font=ds.FONT,
        )
        search_entry.pack(side=tk.RIGHT)

        # ---- Main split layout ----
        split = ctk.CTkFrame(main, fg_color="transparent")
        split.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        split.columnconfigure(0, weight=0, minsize=240)
        split.columnconfigure(1, weight=1)
        split.rowconfigure(0, weight=1)

        # ---- NPC list (left panel) ----
        npc_box, npc_tree = ds.themed_tree(
            split, columns=("npc", "steps"), show="headings", selectmode="browse"
        )
        npc_tree.heading("npc", text="NPC")
        npc_tree.heading("steps", text="Steps")
        npc_tree.column("npc", width=170, anchor="w")
        npc_tree.column("steps", width=60, anchor="e", stretch=False)
        npc_tree.tag_configure("done", foreground=palette.pick(palette.GREEN_TEXT))
        npc_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # ---- Steps panel (right panel) ----
        steps_outer = ctk.CTkFrame(split, corner_radius=8, fg_color=ds.BOX)
        steps_outer.grid(row=0, column=1, sticky="nsew")
        steps_outer.rowconfigure(1, weight=1)
        steps_outer.columnconfigure(0, weight=1)

        npc_header = ctk.CTkLabel(
            steps_outer, text="Select an NPC", font=ds.TITLE, anchor="w"
        )
        npc_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        steps_scroll = ctk.CTkScrollableFrame(
            steps_outer, corner_radius=0, fg_color="transparent"
        )
        steps_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        bind_mousewheel(steps_scroll)

        # ---- State ----
        selected_npc = tk.StringVar(value="")
        step_widgets = []  # (step_dict, apply_btn)

        def _safe_get_flag(flag_id):
            try:
                return event_flag_accessor.get_flag(flag_id)
            except (ValueError, KeyError):
                return False

        def _step_is_complete(step):
            return is_tracked(step) and all(
                bool(_safe_get_flag(f["id"])) == bool(f["value"]) for f in step["flags"]
            )

        def _count_complete(npc_name):
            steps = QUEST_FLAGS[npc_name]
            done = sum(1 for s in steps if _step_is_complete(s))
            return done, sum(1 for s in steps if is_tracked(s))

        def _render_steps(npc_name):
            for w in steps_scroll.winfo_children():
                w.destroy()
            step_widgets.clear()

            steps = QUEST_FLAGS[npc_name]
            done, total = _count_complete(npc_name)
            npc_header.configure(text=f"{npc_name}  ({done}/{total} steps complete)")

            for i, step in enumerate(steps):
                complete = _step_is_complete(step)
                row_frame = ctk.CTkFrame(steps_scroll, corner_radius=8, fg_color=ds.ROW)
                row_frame.pack(fill=tk.X, pady=3, padx=2)
                row_frame.columnconfigure(1, weight=1)

                # Step number, or a check mark once every flag of the step is set
                ctk.CTkLabel(
                    row_frame,
                    text="✓" if complete else str(i + 1),
                    font=ds.BOLD,
                    text_color=ds.FOUND if complete else ds.MUTED,
                    width=28,
                ).grid(row=0, column=0, rowspan=2, padx=(8, 4), pady=8, sticky="n")

                ctk.CTkLabel(
                    row_frame,
                    text=step["description"],
                    font=ds.FONT,
                    anchor="w",
                    justify="left",
                    wraplength=470,
                ).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(8, 0))

                meta_parts = []
                if step["location"]:
                    meta_parts.append(step["location"])
                meta_parts.append(f"{len(step['flags'])} flag(s)")
                if not is_tracked(step):
                    meta_parts.append("not tracked")
                ctk.CTkLabel(
                    row_frame,
                    text="  |  ".join(meta_parts),
                    font=ds.SMALL,
                    text_color=ds.MUTED,
                    anchor="w",
                ).grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 8))

                if undo and complete:
                    apply_btn = ds.button(
                        row_frame,
                        "Undo",
                        lambda s=step, npc=npc_name: _undo_step(s, npc),
                        primary=False,
                        width=80,
                    )
                else:
                    apply_btn = ds.button(
                        row_frame,
                        "Applied" if complete else "Apply",
                        lambda idx=i, npc=npc_name: _apply_step(idx, npc),
                        primary=not complete,
                        width=80,
                        state="disabled" if complete else "normal",
                    )
                apply_btn.grid(row=0, column=2, rowspan=2, padx=8, pady=8)

                step_widgets.append((step, apply_btn))

            apply_all_btn.configure(
                state="normal",
                command=lambda: _apply_up_to_last_complete(npc_name),
            )
            reset_btn.configure(
                state="normal",
                command=lambda: _reset_quest(npc_name),
            )

        def _safe_set_flag(flag_id, value):
            with contextlib.suppress(ValueError, KeyError):
                event_flag_accessor.set_flag(flag_id, value)

        def _apply_step(index, npc_name):
            """Apply a quest step's flags, after the steps in between when
            apply_steps_between is set."""
            steps = QUEST_FLAGS[npc_name]
            step = steps[index]
            chain = (
                steps_up_to(steps, index, _step_is_complete)
                if apply_steps_between
                else [step]
            )
            for s in chain:
                for f in s["flags"]:
                    _safe_set_flag(f["id"], bool(f["value"]))
            if len(chain) > 1:
                toast = f"Applied {len(chain)} steps up to: {step['description'][:50]}"
            else:
                toast = f"Applied: {step['description'][:60]}"
            _save_and_refresh(npc_name, toast)

        def _undo_step(step, npc_name):
            """Clear the flags a step sets."""
            for f in step["flags"]:
                if f["value"]:
                    _safe_set_flag(f["id"], False)
            _save_and_refresh(npc_name, f"Undid: {step['description'][:60]}")

        def _apply_up_to_last_complete(npc_name):
            """
            Apply all steps up to and including the last currently-complete step,
            effectively syncing the save to the furthest known progress point.
            Asks confirmation first.
            """
            steps = QUEST_FLAGS[npc_name]
            last_complete = -1
            for i, step in enumerate(steps):
                if _step_is_complete(step):
                    last_complete = i

            if last_complete < 0:
                # None complete - ask if user wants to apply all or just the first
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
                f"Reset ALL event flags for {npc_name}'s quest to 0?\n\nThis will undo all tracked quest progress. A backup will be created. Some steps may stay applied even if you reset all flags. This is because those steps only use flags that the game clears back to 0, so they're indistinguishable from never happened in a save.",
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

            if commit is not None:
                try:
                    commit(toast_msg)
                except Exception as exc:
                    if exc.__cause__ is not None:
                        dialog.destroy()
                    else:
                        CTkMessageBox.showerror("Save Failed", str(exc), parent=dialog)
                    return
                if show_toast:
                    show_toast(toast_msg, duration=2500)
                _render_steps(npc_name)
                _rebuild_npc_list(search_var.get())
                return

            if save_path and save_path.is_file():
                with contextlib.suppress(Exception):
                    BackupManager(save_path).create_backup(
                        description=f"before_quest_edit_slot_{slot_idx + 1}",
                        operation="quest_progress_edit",
                        save=save_file,
                    )

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
            npc_tree.delete(*npc_tree.get_children())
            query = query.lower().strip()
            for npc_name in sorted(QUEST_FLAGS.keys()):
                if query and query not in npc_name.lower():
                    # Also check if any step description matches
                    steps = QUEST_FLAGS[npc_name]
                    if not any(
                        query in (s["description"] or "").lower() for s in steps
                    ):
                        continue
                done, total = _count_complete(npc_name)
                npc_tree.insert(
                    "",
                    "end",
                    iid=npc_name,
                    values=(npc_name, f"{done}/{total}"),
                    tags=("done",) if total and done == total else (),
                )
            active = selected_npc.get()
            if npc_tree.exists(active):
                npc_tree.selection_set(active)
                npc_tree.see(active)

        def _select_npc(npc_name):
            if npc_name == selected_npc.get():
                return
            selected_npc.set(npc_name)
            _render_steps(npc_name)

        npc_tree.bind(
            "<<TreeviewSelect>>",
            lambda _e: npc_tree.selection() and _select_npc(npc_tree.selection()[0]),
        )

        def _on_search(*_):
            _rebuild_npc_list(search_var.get())

        search_var.trace_add("write", _on_search)
        _rebuild_npc_list()
        ds.finish(dialog, parent, width=920, height=660)
