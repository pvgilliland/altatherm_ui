import customtkinter as ctk
from typing import TYPE_CHECKING, Dict, Any, Optional
import logging
import time

from SerialService import SerialService
from hmi_consts import HMIColors, HMISizePos
from ui_bits import COLOR_FG, COLOR_BLUE
from LabeledIntInput import LabeledIntInput
from Settings import Settings

if TYPE_CHECKING:
    from MultiPageController import MultiPageController

logger = logging.getLogger("DiagnosticsPage2")


class DiagnosticsPage2(ctk.CTkFrame):
    def __init__(
        self, controller: "MultiPageController", shared_data: Dict[str, Any], **kwargs
    ):
        super().__init__(controller, fg_color=COLOR_FG, **kwargs)

        self.controller = controller
        self.shared_data = shared_data

        self.rfid_serial: Optional[SerialService] = getattr(
            self.controller, "rfid_serial", None
        )

        
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        btn_font = ctk.CTkFont(family="Arial", size=18, weight="bold")
        lbl_font = ctk.CTkFont(family="Arial", size=20, weight="bold")
        small_btn_font = ctk.CTkFont(family="Arial", size=24, weight="bold")
        log_lbl_font = ctk.CTkFont(family="Arial", size=24, weight="bold")

        # ----- Header -----
        header = ctk.CTkFrame(self, fg_color=COLOR_FG)
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            header,
            text="(Diag 2) Cookpack Algorithm / RFID Testing",
            text_color=COLOR_BLUE,
            font=("Arial", 20, "bold"),
        ).pack(pady=(4, 8))

        ctk.CTkFrame(header, height=2, fg_color=COLOR_BLUE).pack(
            fill="x", padx=2, pady=(0, 6)
        )

        # ----- Body -----
        body = ctk.CTkFrame(
            self,
            fg_color=COLOR_FG,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BLUE,
        )
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)

        left_frame = ctk.CTkFrame(body, fg_color=COLOR_FG)
        left_frame.grid(row=0, column=0, sticky="nw", padx=(10, 10), pady=10)

        right_frame = ctk.CTkFrame(body, fg_color=COLOR_FG)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=10)

        # Left side uses one sequential row per control.
        # Keep these rows compact. Do not give them vertical weight,
        # otherwise Tk spreads the controls over the full body height.
        left_frame.grid_columnconfigure(0, weight=0)
        for row_index in range(6):
            left_frame.grid_rowconfigure(row_index, weight=0)

        # Right side log area expands. Only the textbox row gets vertical weight,
        # so the RFID log grows to use nearly all remaining body height.
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=0)
        right_frame.grid_rowconfigure(1, weight=0)
        right_frame.grid_rowconfigure(2, weight=0)
        right_frame.grid_rowconfigure(3, weight=1)
        right_frame.grid_rowconfigure(4, weight=0)

        left_row_pady = (6, 6)

        # ----- Left side controls -----
        self.tset_input = LabeledIntInput(
            left_frame,
            label="TSET (°C):",
            initial=60,
            min_val=25,
            max_val=300,
            step=1,
            big_step=5,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=80,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.tset_input.grid(row=0, column=0, sticky="w", padx=10, pady=left_row_pady)

        self.thys_input = LabeledIntInput(
            left_frame,
            label="THYS (°C):",
            initial=25,
            min_val=0,
            max_val=100,
            step=1,
            big_step=5,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=80,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.thys_input.grid(row=1, column=0, sticky="w", padx=10, pady=left_row_pady)

        self.top_zones_correction_factor_input = LabeledIntInput(
            left_frame,
            label="Top Zones Correction Factor (%):     ",
            initial=0,
            min_val=0,
            max_val=100,
            step=1,
            big_step=5,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=80,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.top_zones_correction_factor_input.grid(
            row=2, column=0, sticky="w", padx=10, pady=left_row_pady
        )

        self.bottom_zones_correction_factor_input = LabeledIntInput(
            left_frame,
            label="Bottom Zones Correction Factor (%):",
            initial=0,
            min_val=0,
            max_val=100,
            step=1,
            big_step=5,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=80,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.bottom_zones_correction_factor_input.grid(
            row=3, column=0, sticky="w", padx=10, pady=left_row_pady
        )

        self.tc_input = LabeledIntInput(
            left_frame,
            label="tC (sec):",
            initial=300,
            min_val=10,
            max_val=8835,
            step=1,
            big_step=30,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=100,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.tc_input.grid(row=4, column=0, sticky="w", padx=10, pady=left_row_pady)

        self.enable_cook_algorithm_checkbox = ctk.CTkCheckBox(
            left_frame,
            text="Enable Cookpack Algorithm",
            font=lbl_font,
            text_color=COLOR_BLUE,
            fg_color=COLOR_BLUE,
            hover_color=HMIColors.color_numbers,
            border_color=COLOR_BLUE,
            checkmark_color=COLOR_FG,
        )
        self.enable_cook_algorithm_checkbox.grid(
            row=5, column=0, sticky="w", padx=10, pady=left_row_pady
        )

        # ----- Right side RFID controls -----
        self.use_rfid_checkbox = ctk.CTkCheckBox(
            right_frame,
            text="Enable RFID Reader",
            font=lbl_font,
            text_color=COLOR_BLUE,
            fg_color=COLOR_BLUE,
            hover_color=HMIColors.color_numbers,
            border_color=COLOR_BLUE,
            checkmark_color=COLOR_FG,
        )
        self.use_rfid_checkbox.grid(
            row=0, column=0, sticky="w", padx=10, pady=(4, 4)
        )

        button_row = ctk.CTkFrame(right_frame, fg_color=COLOR_FG)
        button_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 4))

        self.is_tag_present_btn = ctk.CTkButton(
            button_row,
            text="Is Tag Present?",
            command=self.on_is_tag_present,
            font=small_btn_font,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=18,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=230,
            height=48,
        )
        self.is_tag_present_btn.grid(row=0, column=0, sticky="w", padx=(0, 20))

        self.get_last_read_btn = ctk.CTkButton(
            button_row,
            text="Get Last Read",
            command=self.on_get_last_read,
            font=small_btn_font,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=18,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=230,
            height=48,
        )
        self.get_last_read_btn.grid(row=0, column=1, sticky="w")

        self.log_label = ctk.CTkLabel(
            right_frame,
            text="Communication Log",
            text_color=HMIColors.color_blue,
            font=log_lbl_font,
        )
        self.log_label.grid(row=2, column=0, sticky="w", padx=10, pady=(2, 2))

        self.serial_log_textbox = ctk.CTkTextbox(
            right_frame,
            fg_color="black",
            text_color="white",
            border_width=0,
            corner_radius=0,
            font=("Consolas", 16),
            wrap="word",
        )
        self.serial_log_textbox.grid(
            row=3, column=0, sticky="nsew", padx=10, pady=(0, 4)
        )

        self.clear_log_btn = ctk.CTkButton(
            right_frame,
            text="Clear",
            command=self.on_clear_log,
            font=small_btn_font,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=12,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=100,
            height=48,
        )
        self.clear_log_btn.grid(row=4, column=0, sticky="e", padx=10, pady=(0, 4))

        # ----- Footer -----
        footer = ctk.CTkFrame(self, fg_color=COLOR_FG)
        footer.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        back_btn = ctk.CTkButton(
            footer,
            text="← Back",
            command=self.on_back,
            font=btn_font,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=20,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
        )
        back_btn.pack(side="left", padx=10, pady=6)

        refresh_btn = ctk.CTkButton(
            footer,
            text="Refresh",
            command=self.on_refresh,
            font=btn_font,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=20,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
        )
        refresh_btn.pack(side="right", padx=10, pady=6)

    def _clamp(self, val: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, val))

    def save_settings(self):
        try:
            s = Settings.Instance()

            s.tset = self._clamp(int(self.tset_input.get()), 25, 300)
            s.thys = self._clamp(int(self.thys_input.get()), 0, 100)
            s.top_zones_correction_factor = self._clamp(
                int(self.top_zones_correction_factor_input.get()), 0, 100
            )
            s.bottom_zones_correction_factor = self._clamp(
                int(self.bottom_zones_correction_factor_input.get()), 0, 100
            )
            s.tc = self._clamp(int(self.tc_input.get()), 10, 8835)
            s.enable_cook_algorithm = bool(self.enable_cook_algorithm_checkbox.get())
            s.use_rfid = bool(self.use_rfid_checkbox.get())

            s.save()

            self.shared_data["tset"] = s.tset
            self.shared_data["thys"] = s.thys
            self.shared_data["top_zones_correction_factor"] = (
                s.top_zones_correction_factor
            )
            self.shared_data["bottom_zones_correction_factor"] = (
                s.bottom_zones_correction_factor
            )
            self.shared_data["tc"] = s.tc
            self.shared_data["enable_cook_algorithm"] = s.enable_cook_algorithm
            self.shared_data["use_rfid"] = s.use_rfid

        except Exception as e:
            print(f"[DiagnosticsPage2] Failed to save settings: {e}")

    def on_show(self):
        print("[DiagnosticsPage2] on_show")

        try:
            s = Settings.Instance()
            s.load()

            self.tset_input.set(int(s.tset))
            self.thys_input.set(int(s.thys))
            self.top_zones_correction_factor_input.set(
                int(s.top_zones_correction_factor)
            )
            self.bottom_zones_correction_factor_input.set(
                int(s.bottom_zones_correction_factor)
            )
            self.tc_input.set(int(s.tc))

            if s.enable_cook_algorithm:
                self.enable_cook_algorithm_checkbox.select()
            else:
                self.enable_cook_algorithm_checkbox.deselect()

            if s.use_rfid:
                self.use_rfid_checkbox.select()
            else:
                self.use_rfid_checkbox.deselect()

            self.shared_data["tset"] = s.tset
            self.shared_data["thys"] = s.thys
            self.shared_data["top_zones_correction_factor"] = (
                s.top_zones_correction_factor
            )
            self.shared_data["bottom_zones_correction_factor"] = (
                s.bottom_zones_correction_factor
            )
            self.shared_data["tc"] = s.tc
            self.shared_data["enable_cook_algorithm"] = s.enable_cook_algorithm
            self.shared_data["use_rfid"] = s.use_rfid

            if self.rfid_serial:
                try:
                    self.rfid_serial.add_listener(self._on_serial_line)
                    self._append_log("[DiagnosticsPage2] RFID listener attached")
                except Exception as e:
                    self._append_log(f"[DiagnosticsPage2] add_listener failed: {e}")
            else:
                self._append_log("[DiagnosticsPage2] No controller.rfid_serial found")

        except Exception as e:
            print(f"[DiagnosticsPage2] Failed to load settings: {e}")

    def on_hide(self):
        print("[DiagnosticsPage2] on_hide")
        self.save_settings()
        self._remove_serial_listener_safe()

    def _remove_serial_listener_safe(self):
        try:
            if self.rfid_serial:
                self.rfid_serial.remove_listener(self._on_serial_line)
        except Exception:
            pass

    def _on_serial_line(self, line: str) -> None:
        print(f"RFID: {line}")
        self._append_log(f"Recvd: {line}")

        # if "N=1" in line:
        #     self._append_log(f"A new tag has entered the reader's RF field")
        # if "E=1" in line:
        #     self._append_log(f"An error when reading the tag's data")

    def _append_log(self, text: str) -> None:
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.serial_log_textbox.insert("end", f"[{timestamp}] {text}\n")
            self.serial_log_textbox.see("end")
        except Exception as e:
            print(f"[DiagnosticsPage2] Log append failed: {e}")

    def on_clear_log(self):
        try:
            self.serial_log_textbox.delete("1.0", "end")
        except Exception as e:
            print(f"[DiagnosticsPage2] Clear log failed: {e}")

    def on_is_tag_present(self):
        msg = "Q\r"
        if self.rfid_serial:
            self.rfid_serial.send(msg)
            self._append_log("Sent: Q")
        else:
            self._append_log("RFID reader not present")

    def on_get_last_read(self):
        msg = "D\r"
        if self.rfid_serial:
            self.rfid_serial.send(msg)
            self._append_log("Sent: D")
        else:
            self._append_log("RFID reader not present")

    def on_back(self):
        self.save_settings()

        if hasattr(self.controller, "show_DiagnosticsPage"):
            self.controller.show_DiagnosticsPage()
        else:
            print("[DiagnosticsPage2] Controller missing show_DiagnosticsPage()")

    def on_refresh(self):
        self.save_settings()
        self._append_log("Settings refreshed")

        print(
            f"[DiagnosticsPage2] Refreshed, "
            f"TSET={self.shared_data.get('tset')}, "
            f"THYS={self.shared_data.get('thys')}, "
            f"Top Zones Correction Factor={self.shared_data.get('top_zones_correction_factor')}, "
            f"Bottom Zones Correction Factor={self.shared_data.get('bottom_zones_correction_factor')}, "
            f"tC={self.shared_data.get('tc')}, "
            f"Enable Cook Algorithm={self.shared_data.get('enable_cook_algorithm')}, "
            f"Use RFID={self.shared_data.get('use_rfid')}"
        )

    def get_tset(self):
        return int(self.shared_data.get("tset", 60))

    def get_thys(self):
        return int(self.shared_data.get("thys", 5))

    def get_top_zones_correction_factor(self):
        return int(self.shared_data.get("top_zones_correction_factor", 80))

    def get_bottom_zones_correction_factor(self):
        return int(self.shared_data.get("bottom_zones_correction_factor", 80))

    def get_tc(self):
        return int(self.shared_data.get("tc", 240))

    def get_enable_cook_algorithm(self):
        return bool(self.shared_data.get("enable_cook_algorithm", False))

    def get_use_rfid(self):
        return bool(self.shared_data.get("use_rfid", False))