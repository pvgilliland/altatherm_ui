# SequenceProgramPage.py

import customtkinter as ctk
from functools import partial
from DoorSafety import DoorSafety
from hmi_consts import HMIColors, HMISizePos, LightOnly
from SequenceStructure import SequenceCollection
from CookingSequenceRunner import CookingSequenceManager
from SelectProgramPage import (
    load_program_into_sequence_collection,
    save_program_from_sequence_collection,
)
import logging

logger = logging.getLogger(__name__)


# ---------- Helpers ----------
def _sec_to_mmss(seconds: float) -> tuple[int, int]:
    seconds = int(round(seconds))
    return seconds // 60, seconds % 60


def _mmss_to_sec(m: int, s: int) -> float:
    return float(m * 60 + s)


# ---------- UI widgets ----------
class DualTextButton(ctk.CTkFrame):
    """Composite control showing power (left) and time (right). Forced-light colors."""

    def __init__(self, master, power, min, sec, height, command=None, **kwargs):
        super().__init__(
            master,
            border_width=2,
            border_color=LightOnly.ACCENT,
            fg_color=LightOnly.PILL_BG,
            **kwargs,
        )
        self.command = command
        self.power, self.min, self.sec = power, min, sec
        self.pack_propagate(False)
        self.configure(height=height)

        font = ctk.CTkFont(family="Arial", size=HMISizePos.s(13))

        self.left_label = ctk.CTkLabel(
            self,
            text=f"{self.power:03}",
            anchor="w",
            font=font,
            text_color=LightOnly.PILL_TEXT,
        )
        self.left_label.pack(
            side="left",
            padx=(HMISizePos.sx(6), HMISizePos.sx(4)),
            pady=HMISizePos.sy(2),
        )

        self.right_label = ctk.CTkLabel(
            self,
            text=f"{self.min:02}:{self.sec:02}",
            anchor="e",
            font=font,
            text_color=LightOnly.PILL_TEXT,
        )
        self.right_label.pack(
            side="right",
            padx=(HMISizePos.sx(4), HMISizePos.sx(6)),
            pady=HMISizePos.sy(2),
        )

        for w in (self, self.left_label, self.right_label):
            w.bind("<Button-1>", self._on_click)

    def _on_click(self, _e):
        if self.command:
            self.command()

    def set_values(self, power: int, minute: int, second: int):
        self.power, self.min, self.sec = power, minute, second
        self.left_label.configure(text=f"{power:03}")
        self.right_label.configure(text=f"{minute:02}:{second:02}")


class StepRowWidget(ctk.CTkFrame):
    """
    Row with vertically-centered content.

    - Outer frame: single background color (all rows identical)
    - Inner 'strip': the only thing that gets highlighted (HMIColors.color_blue)
    """

    def __init__(
        self,
        master,
        index=1,
        zone_icon=None,
        values=None,
        on_row_click=None,
        row_height=0,
        pill_height=0,
        base_color=None,
        **kwargs,
    ):
        self.base_color = base_color or LightOnly.ROW_ODD

        # Outer row frame (single row background only)
        super().__init__(master, height=row_height, fg_color=self.base_color, **kwargs)
        self.grid_propagate(False)

        self.on_row_click = on_row_click
        self.index = index
        values = values or [("000", "00:00")] * 4

        # Three-row grid to vertically center content
        self.grid_rowconfigure(0, weight=1)  # top spacer
        self.grid_rowconfigure(1, weight=0)  # content band
        self.grid_rowconfigure(2, weight=1)  # bottom spacer
        self.grid_columnconfigure(0, weight=1)

        # Highlight strip (only this changes color when selected)
        self.strip = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=HMISizePos.s(12),
        )
        self.strip.grid(
            row=1,
            column=0,
            sticky="we",
            padx=(HMISizePos.sx(18), HMISizePos.sx(18)),
        )
        self.strip.grid_columnconfigure(0, weight=1)

        # Content sits on the strip
        self.content = ctk.CTkFrame(self.strip, fg_color="transparent")
        self.content.grid(row=0, column=0, sticky="we", pady=HMISizePos.sy(1))

        # columns: [#, icon, btn1..4]
        self.content.grid_columnconfigure(1, minsize=HMISizePos.sx(32))  # icon
        for c in range(2, 6):
            self.content.grid_columnconfigure(c, weight=1)

        # Step number
        self.label_index = ctk.CTkLabel(
            self.content,
            text=str(index),
            width=HMISizePos.sx(24),
            anchor="center",
            font=ctk.CTkFont(family="Arial", size=HMISizePos.s(14), weight="bold"),
            text_color=LightOnly.ROW_TEXT,
        )
        self.label_index.grid(
            row=0, column=0, padx=(HMISizePos.sx(6), HMISizePos.sx(6))
        )

        # Icon
        self.icon_label = ctk.CTkLabel(self.content, image=zone_icon, text="")
        self.icon_label.grid(row=0, column=1, padx=(0, HMISizePos.sx(8)))

        # DualTextButtons
        self.dual_buttons = []
        for i, (top, bottom) in enumerate(values):
            m, s = map(int, bottom.split(":"))
            p = int(top)
            btn = DualTextButton(
                self.content,
                power=p,
                min=m,
                sec=s,
                width=HMISizePos.sx(128),
                height=pill_height,
                corner_radius=HMISizePos.s(16),
                command=partial(self.button_clicked, self.index, i),
            )
            btn.grid(
                row=0,
                column=2 + i,
                padx=(HMISizePos.sx(2), HMISizePos.sx(6)),
                sticky="we",
            )
            self.dual_buttons.append(btn)

        # Click handling (anywhere on the row/strip/content)
        for w in (
            self,
            self.strip,
            self.content,
            self.label_index,
            self.icon_label,
        ):
            w.bind("<Button-1>", lambda _e: self.row_clicked())

    def set_row_height(self, h: int, pill_h: int):
        self.configure(height=h)
        for btn in self.dual_buttons:
            btn.configure(height=pill_h)

    def row_clicked(self):
        if self.on_row_click:
            self.on_row_click(self.index, None)

    def highlight_row(self, active=True):
        # Highlight only the strip, keep the outer row background constant
        self.strip.configure(fg_color=HMIColors.color_blue if active else "transparent")

    def button_clicked(self, row_index, col_index):
        if self.on_row_click:
            self.on_row_click(row_index, col_index)


# ---------- Main Page ----------
class SequenceProgramPage(ctk.CTkFrame):
    def __init__(self, controller, shared_data):
        super().__init__(controller, fg_color=LightOnly.FG)
        self.controller, self.shared_data = controller, shared_data
        self.step_widgets, self.selected_row, self.programNumber = [], None, 0
        self.duplicate_btn = None

        self._header = None
        self._table = None
        self._footer = None

        # Compact layout targets (cap auto-resize so it doesn't "bounce back")
        self.DESIRED_ROW_H = HMISizePos.sy(44)
        self.MIN_ROW_H = HMISizePos.sy(38)
        self.DESIRED_PILL_H = HMISizePos.sy(30)
        self.MIN_PILL_H = HMISizePos.sy(26)

        self._build_ui()

    def _build_ui(self):
        # Layout: header (0), table (1), footer (2)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # ---------- Header ----------
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(
            row=0,
            column=0,
            sticky="we",
            padx=HMISizePos.PADDING,
            pady=(HMISizePos.sy(6), HMISizePos.sy(2)),
        )
        self._header.grid_columnconfigure(0, weight=1)

        self.program_label = ctk.CTkLabel(
            self._header,
            text="Program",
            anchor="w",
            font=ctk.CTkFont(family="Arial", size=HMISizePos.s(16), weight="bold"),
            text_color=LightOnly.ROW_TEXT,
        )
        self.program_label.grid(row=0, column=0, sticky="w")

        # ---------- Table ----------
        self._table = ctk.CTkFrame(self, fg_color="transparent")
        self._table.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=HMISizePos.PADDING,
            pady=(0, HMISizePos.sy(2)),
        )

        # col0: rows; col1: duplicate rail (reserve width so layout doesn't shift)
        self._table.grid_columnconfigure(0, weight=1)
        self._table.grid_columnconfigure(1, weight=0, minsize=HMISizePos.sx(120))

        # map to the desired icon order
        vals = [7, 5, 6, 4, 3, 1, 2, 0]
        d = dict(zip(range(8), vals))

        ROW_BASE_COLOR = LightOnly.ROW_ODD  # single background for all rows

        for i in range(8):
            row = StepRowWidget(
                self._table,
                index=i + 1,
                zone_icon=self.controller.zone_icons[d[i]],
                values=[("000", "00:00")] * 4,
                on_row_click=self._on_row_selected,
                row_height=self.DESIRED_ROW_H,
                pill_height=self.DESIRED_PILL_H,
                base_color=ROW_BASE_COLOR,
            )
            row.grid(row=i, column=0, sticky="we", padx=(0, HMISizePos.sx(6)))
            self.step_widgets.append(row)
            self._table.grid_rowconfigure(i, minsize=1)

        # Duplicate button (theme colors restored)
        self.duplicate_btn = ctk.CTkButton(
            self._table,
            text="Duplicate",
            width=HMISizePos.sx(104),
            height=HMISizePos.sy(38),
            font=ctk.CTkFont(family="Arial", size=HMISizePos.s(14), weight="bold"),
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=HMISizePos.s(16),
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            command=self._duplicate_selected_to_next,
        )

        # filler row keeps rows top-aligned
        self._table.grid_rowconfigure(8, weight=1)

        # ---------- Footer ----------
        self._footer = ctk.CTkFrame(self, fg_color="transparent")
        self._footer.grid(
            row=2,
            column=0,
            sticky="we",
            padx=HMISizePos.PADDING,
            pady=(HMISizePos.sy(2), HMISizePos.PADDING),
        )
        self._footer.grid_columnconfigure(0, weight=1)
        self._footer.grid_columnconfigure(1, weight=0)

        btn_font = ctk.CTkFont(family="Arial", size=HMISizePos.s(16), weight="bold")

        back_btn = ctk.CTkButton(
            self._footer,
            text="← Back",
            font=btn_font,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=HMISizePos.s(20),
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            command=self.go_back,
        )
        back_btn.grid(row=0, column=0, sticky="w")

        right_group = ctk.CTkFrame(self._footer, fg_color="transparent")
        right_group.grid(row=0, column=1, sticky="e")
        right_group.grid_columnconfigure(0, weight=0)
        right_group.grid_columnconfigure(1, weight=0)

        self.run_button_font = ctk.CTkFont(
            family="Arial", size=HMISizePos.s(16), weight="bold", overstrike=0
        )
        self.run_button = ctk.CTkButton(
            right_group,
            text="Run",
            font=self.run_button_font,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=HMISizePos.s(20),
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            command=self.on_run,
        )
        self.run_button.grid(row=0, column=0, padx=(0, HMISizePos.sx(8)))

        self.save_button = ctk.CTkButton(
            right_group,
            text="Save",
            font=btn_font,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=HMISizePos.s(20),
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            command=self.on_save,
        )
        self.save_button.grid(row=0, column=1)

        # initial selection & placement
        self._set_selected_row(1)

        # schedule sizing after layout + on resize
        self.after(0, self._resize_rows)
        self.bind("<Configure>", self._throttled_resize)

        DoorSafety.Instance().add_listener(self.on_door_change)

    def on_door_change(self, is_open: bool):
        print(f"[SequenceProgramPage.on_door_change] Door Open = {is_open}")
        btnState = "disabled" if is_open else "normal"
        btnColorBorder = (
            HMIColors.DISABLED_BORDER_COLOR if is_open else HMIColors.color_blue
        )
        btnText = "Run\n(door open)" if is_open else "Run"
        self.run_button_font.configure(overstrike=is_open)
        self.run_button.configure(
            state=btnState, border_color=btnColorBorder, text=btnText
        )

    # ---- throttled resize ----
    def _throttled_resize(self, _event):
        if hasattr(self, "_resize_job") and self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(50, self._resize_rows)

    def _measure_available_table_height(self) -> int:
        self.update_idletasks()
        page_h = self.winfo_height()
        if page_h <= 1:
            return 0
        header_h = self._header.winfo_height()
        footer_h = self._footer.winfo_height()
        table_pad_v = HMISizePos.sy(2)
        safety = 20
        return max(0, page_h - header_h - footer_h - table_pad_v - safety)

    def _resize_rows(self):
        self.update_idletasks()

        avail_h = self._measure_available_table_height()
        if avail_h <= 0:
            return

        rows = 8

        # Tight row spacing: force minimal gap
        gap = 1

        # Fit-to-height math, but cap to the compact desired row height (prevents "bounce back")
        fit_row_h = int((avail_h - (gap * 2 * rows)) / rows)

        row_h = min(self.DESIRED_ROW_H, fit_row_h)
        row_h = max(self.MIN_ROW_H, row_h)

        # Keep pills proportional, but also capped
        fit_pill_h = int(row_h * 0.70)
        pill_h = min(self.DESIRED_PILL_H, fit_pill_h)
        pill_h = max(self.MIN_PILL_H, pill_h)

        for i, row in enumerate(self.step_widgets):
            row.set_row_height(row_h, pill_h)
            row.grid_configure(pady=(gap, gap))
            self._table.grid_rowconfigure(i, minsize=row_h + gap * 2)

        if self.duplicate_btn.winfo_ismapped():
            self.duplicate_btn.grid_configure(padx=(HMISizePos.sx(4), 0))

    # ---------- Selection / Duplicate ----------
    def _on_row_selected(self, row_1based: int, col_index_or_none):
        self._set_selected_row(row_1based)
        if col_index_or_none is not None:
            self.shared_data["selected_row"] = row_1based
            self.shared_data["selected_col"] = col_index_or_none
            title = f"Zone {row_1based} • Step {col_index_or_none+1}"
            self.controller.show_PhaseTimePowerPage(title)

    def _set_selected_row(self, row_1based: int):
        if self.selected_row:
            self.selected_row.highlight_row(False)
        self.selected_row = self.step_widgets[row_1based - 1]
        self.selected_row.highlight_row(True)

        self.duplicate_btn.grid_forget()
        if row_1based < 8:
            self.duplicate_btn.grid(
                row=row_1based - 1, column=1, sticky="e", padx=(HMISizePos.sx(4), 0)
            )

    def _duplicate_selected_to_next(self):
        if not self.selected_row:
            return
        src_i = self.step_widgets.index(self.selected_row)
        dst_i = src_i + 1
        if dst_i >= len(self.step_widgets):
            return
        for j, btn in enumerate(self.step_widgets[src_i].dual_buttons):
            self.step_widgets[dst_i].dual_buttons[j].set_values(
                btn.power, btn.min, btn.sec
            )
        self._set_selected_row(dst_i + 1)

    # ---------- Navigation / Actions ----------
    def go_back(self):
        if self.controller:
            self.controller.show_HomePage()

    def on_run(self):
        try:
            self.sync_to_model()

            sc = SequenceCollection.Instance()
            zone_sequences = []
            for zone_idx in range(8):
                zone = sc.get_zone_sequence_by_index(zone_idx)
                if not zone:
                    continue
                steps = []
                for step in zone.steps:
                    duration = float(step.duration or 0)
                    power = int(step.power or 0)
                    if duration <= 0 or power <= 0:
                        continue
                    steps.append((duration, power))
                zone_name = zone.name or f"Zone{zone_idx+1}"
                if steps:
                    zone_sequences.append((zone_name, steps))

            if not zone_sequences:
                print("[Run] No non-empty steps found; nothing to run.")
                return

            mgr = CookingSequenceManager()

            def set_zone_output(zone_name: str, value: float, duration: float):
                try:
                    zone_id = int(zone_name.replace("Zone", ""))
                except Exception:
                    print(f"[HW] Bad zone name: {zone_name}")
                    return
                self.controller.serial_zone(zone_id, int(value))

            zone8_flag = False
            for zone_name, steps in zone_sequences:
                mgr.add_dac(zone_name, steps, set_zone_output)
                if zone_name == "Zone8":
                    zone8_flag = True

            if zone8_flag is False:
                mgr.add_dac("Zone8", [(0.0, 0)], set_zone_output)

            mgr.set_on_all_complete(lambda: self.controller.serial_all_zones_off())
            self.shared_data["sequence_manager"] = mgr

            def zone_total(steps):
                return sum(d for (d, _p) in steps)

            total_seconds = max(zone_total(steps) for _name, steps in zone_sequences)

            def on_stop_handler():
                try:
                    if hasattr(mgr, "stop_all"):
                        mgr.stop_all()
                    elif hasattr(mgr, "request_stop"):
                        mgr.request_stop()
                except Exception as e:
                    print("[Run] stop handler error:", e)

            logger.info("Program Cook Cycle Started")
            mgr.start_all()
            self.controller.show_CircularProgressPage(
                total_seconds, on_stop=on_stop_handler
            )
            print(
                f"[Run] Program {self.programNumber} started for {len(zone_sequences)} zones; "
                f"~{int(total_seconds)}s total."
            )

        except Exception as e:
            print("[Run] Failed to start program:", e)

    def on_save(self):
        try:
            self.sync_to_model()
            save_program_from_sequence_collection(self.programNumber)
            print(f"Saved program{self.programNumber}.alt")
        except Exception as e:
            print("Save failed:", e)

    # ---------- Model Sync ----------
    def sync_from_model(self):
        sc = SequenceCollection.Instance()
        for i, row in enumerate(self.step_widgets):
            zone = sc.get_zone_sequence_by_index(i)
            if not zone:
                continue
            for j, btn in enumerate(row.dual_buttons):
                step = zone.steps[j]
                m, s = _sec_to_mmss(step.duration)
                btn.set_values(int(step.power), int(m), int(s))

    def sync_to_model(self):
        sc = SequenceCollection.Instance()
        for i, row in enumerate(self.step_widgets):
            zone = sc.get_zone_sequence_by_index(i)
            if not zone:
                continue
            for j, btn in enumerate(row.dual_buttons):
                step = zone.steps[j]
                step.power = int(btn.power)
                step.duration = _mmss_to_sec(int(btn.min), int(btn.sec))

    def on_show(self, programNumber: int):
        self.programNumber = programNumber
        try:
            load_program_into_sequence_collection(programNumber)
            self.sync_from_model()
        except Exception as e:
            print("Program load failed:", e)
        self.program_label.configure(text=f"Program {programNumber}")
        self.sync_from_model()
