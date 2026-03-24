import customtkinter as ctk
from typing import TYPE_CHECKING, Dict, Any
import logging
import json
import os

from hmi_consts import HMIColors, HMISizePos, SETTINGS_DIR
from ui_bits import COLOR_FG, COLOR_BLUE
from LabeledIntInput import LabeledIntInput

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

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        btn_font = ctk.CTkFont(family="Arial", size=18, weight="bold")
        lbl_font = ctk.CTkFont(family="Arial", size=20, weight="bold")

        # ----- Header -----
        header = ctk.CTkFrame(self, fg_color=COLOR_FG)
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            header,
            text="Cook Algorithm",
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
        body.grid_columnconfigure(0, weight=1)

        # TSET
        self.tset_input = LabeledIntInput(
            body,
            label="TSET (°C):",
            initial=60,
            min_val=25,
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
        self.tset_input.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        # THYS
        self.thys_input = LabeledIntInput(
            body,
            label="THYS (°C):",
            initial=25,
            min_val=25,
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
        self.thys_input.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        # Top Zones Correction Factor
        self.top_zones_correction_factor_input = LabeledIntInput(
            body,
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
            row=2, column=0, sticky="w", padx=20, pady=(0, 10)
        )

        # Bottom Zones Correction Factor
        self.bottom_zones_correction_factor_input = LabeledIntInput(
            body,
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
            row=3, column=0, sticky="w", padx=20, pady=(0, 10)
        )

        # tC
        self.tc_input = LabeledIntInput(
            body,
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
        self.tc_input.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 10))

        # Enable Cook Algorithm
        self.enable_cook_algorithm_checkbox = ctk.CTkCheckBox(
            body,
            text="Enable Cook Algorithm",
            font=lbl_font,
            text_color=COLOR_BLUE,
            fg_color=COLOR_BLUE,
            hover_color=HMIColors.color_numbers,
            border_color=COLOR_BLUE,
            checkmark_color=COLOR_FG,
        )
        self.enable_cook_algorithm_checkbox.grid(
            row=5, column=0, sticky="w", padx=20, pady=(0, 20)
        )

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

    # ----- Settings helpers -----
    def _load_settings_dict(self) -> dict:
        path = os.path.join(SETTINGS_DIR, "settings.alt")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    def _clamp(self, val: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, val))

    def _load_tset(self, default=60):
        data = self._load_settings_dict()
        try:
            return self._clamp(int(data.get("tset", default)), 25, 100)
        except Exception:
            return default

    def _load_thys(self, default=25):
        data = self._load_settings_dict()
        try:
            return self._clamp(int(data.get("thys", default)), 25, 100)
        except Exception:
            return default

    def _load_top_zones_correction_factor(self, default=0):
        data = self._load_settings_dict()
        try:
            return self._clamp(
                int(data.get("top_zones_correction_factor", default)), 0, 100
            )
        except Exception:
            return default

    def _load_bottom_zones_correction_factor(self, default=0):
        data = self._load_settings_dict()
        try:
            return self._clamp(
                int(data.get("bottom_zones_correction_factor", default)), 0, 100
            )
        except Exception:
            return default

    def _load_tc(self, default=300):
        data = self._load_settings_dict()
        try:
            return self._clamp(int(data.get("tc", default)), 10, 8835)
        except Exception:
            return default

    def _load_enable_cook_algorithm(self, default=False):
        data = self._load_settings_dict()
        try:
            return bool(data.get("enable_cook_algorithm", default))
        except Exception:
            return default

    def save_settings(self):
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            path = os.path.join(SETTINGS_DIR, "settings.alt")

            data = self._load_settings_dict()

            tset = self._clamp(int(self.tset_input.get()), 25, 100)
            thys = self._clamp(int(self.thys_input.get()), 25, 100)
            top_zones_correction_factor = self._clamp(
                int(self.top_zones_correction_factor_input.get()), 0, 100
            )
            bottom_zones_correction_factor = self._clamp(
                int(self.bottom_zones_correction_factor_input.get()), 0, 100
            )
            tc = self._clamp(int(self.tc_input.get()), 10, 8835)
            enable_cook_algorithm = bool(self.enable_cook_algorithm_checkbox.get())

            data["tset"] = tset
            data["thys"] = thys
            data["top_zones_correction_factor"] = top_zones_correction_factor
            data["bottom_zones_correction_factor"] = bottom_zones_correction_factor
            data["tc"] = tc
            data["enable_cook_algorithm"] = enable_cook_algorithm

            with open(path, "w") as f:
                json.dump(data, f, indent=2)

            # Share globally
            self.shared_data["tset"] = tset
            self.shared_data["thys"] = thys
            self.shared_data["top_zones_correction_factor"] = (
                top_zones_correction_factor
            )
            self.shared_data["bottom_zones_correction_factor"] = (
                bottom_zones_correction_factor
            )
            self.shared_data["tc"] = tc
            self.shared_data["enable_cook_algorithm"] = enable_cook_algorithm

            print(
                "[DiagnosticsPage2] Saved "
                f"TSET={tset}, "
                f"THYS={thys}, "
                f"Top Zones Correction Factor={top_zones_correction_factor}, "
                f"Bottom Zones Correction Factor={bottom_zones_correction_factor}, "
                f"tC={tc}, "
                f"Enable Cook Algorithm={enable_cook_algorithm}"
            )

        except Exception as e:
            print(f"[DiagnosticsPage2] Failed to save settings: {e}")

    def on_show(self):
        print("[DiagnosticsPage2] on_show")
        try:
            tset = self._load_tset()
            thys = self._load_thys()
            top_zones_correction_factor = self._load_top_zones_correction_factor()
            bottom_zones_correction_factor = self._load_bottom_zones_correction_factor()
            tc = self._load_tc()
            enable_cook_algorithm = self._load_enable_cook_algorithm()

            self.tset_input.set(tset)
            self.thys_input.set(thys)
            self.top_zones_correction_factor_input.set(top_zones_correction_factor)
            self.bottom_zones_correction_factor_input.set(
                bottom_zones_correction_factor
            )
            self.tc_input.set(tc)

            if enable_cook_algorithm:
                self.enable_cook_algorithm_checkbox.select()
            else:
                self.enable_cook_algorithm_checkbox.deselect()

            # Share immediately
            self.shared_data["tset"] = tset
            self.shared_data["thys"] = thys
            self.shared_data["top_zones_correction_factor"] = (
                top_zones_correction_factor
            )
            self.shared_data["bottom_zones_correction_factor"] = (
                bottom_zones_correction_factor
            )
            self.shared_data["tc"] = tc
            self.shared_data["enable_cook_algorithm"] = enable_cook_algorithm

        except Exception as e:
            print(f"[DiagnosticsPage2] Failed to load settings: {e}")

    def on_hide(self):
        self.save_settings()

    def on_back(self):
        self.save_settings()

        if hasattr(self.controller, "show_DiagnosticsPage"):
            self.controller.show_DiagnosticsPage()
        else:
            print("[DiagnosticsPage2] Controller missing show_DiagnosticsPage()")

    def on_refresh(self):
        self.save_settings()
        print(
            f"[DiagnosticsPage2] Refreshed, "
            f"TSET={self.shared_data.get('tset')}, "
            f"THYS={self.shared_data.get('thys')}, "
            f"Top Zones Correction Factor={self.shared_data.get('top_zones_correction_factor')}, "
            f"Bottom Zones Correction Factor={self.shared_data.get('bottom_zones_correction_factor')}, "
            f"tC={self.shared_data.get('tc')}, "
            f"Enable Cook Algorithm={self.shared_data.get('enable_cook_algorithm')}"
        )

    # Optional helpers
    def get_tset(self):
        return int(self.shared_data.get("tset", self._load_tset()))

    def get_thys(self):
        return int(self.shared_data.get("thys", self._load_thys()))

    def get_top_zones_correction_factor(self):
        return int(
            self.shared_data.get(
                "top_zones_correction_factor",
                self._load_top_zones_correction_factor(),
            )
        )

    def get_bottom_zones_correction_factor(self):
        return int(
            self.shared_data.get(
                "bottom_zones_correction_factor",
                self._load_bottom_zones_correction_factor(),
            )
        )

    def get_tc(self):
        return int(self.shared_data.get("tc", self._load_tc()))

    def get_enable_cook_algorithm(self):
        return bool(
            self.shared_data.get(
                "enable_cook_algorithm",
                self._load_enable_cook_algorithm(),
            )
        )
