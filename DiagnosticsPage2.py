import customtkinter as ctk
from typing import TYPE_CHECKING, Dict, Any, Optional
import logging

from hmi_consts import HMIColors, HMISizePos
from ui_bits import COLOR_FG, COLOR_BLUE, COLOR_NUMBERS

if TYPE_CHECKING:
    from MultiPageController import MultiPageController

logger = logging.getLogger("DiagnosticsPage2")


class DiagnosticsPage2(ctk.CTkFrame):
    RESOLUTION_BASED_VERT_PAD = {
        "800x480": 5,
        "1024x600": 7,
        "1280x800": 9,
    }

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
        val_font = ctk.CTkFont(family="Arial", size=20, weight="bold")

        VERTICAL_PAD = self.RESOLUTION_BASED_VERT_PAD.get(HMISizePos.SCREEN_RES, 7)
        LBL_COLOR = COLOR_BLUE
        VAL_COLOR = COLOR_NUMBERS

        # ----- Header -----
        header = ctk.CTkFrame(self, fg_color=COLOR_FG)
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            header,
            text="Diagnostics 2",
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

        outer = ctk.CTkFrame(body, fg_color=COLOR_FG)
        outer.pack(fill="both", expand=True, padx=10, pady=10)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(1, weight=1)

        leftCol = ctk.CTkFrame(outer, fg_color=COLOR_FG)
        rightCol = ctk.CTkFrame(outer, fg_color=COLOR_FG)
        leftCol.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        rightCol.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        leftCol.grid_columnconfigure(0, weight=0)
        leftCol.grid_columnconfigure(1, weight=1)
        rightCol.grid_columnconfigure(0, weight=0)
        rightCol.grid_columnconfigure(1, weight=1)

        # ----- Placeholder diagnostic fields -----
        self._value_labels = {}

        left_items = [
            ("Heater Current 1:", "N/A"),
            ("Heater Current 2:", "N/A"),
            ("Heater Current 3:", "N/A"),
            ("Heater Current 4:", "N/A"),
            ("Tray Present:", "Unknown"),
            ("Interlock Status:", "Unknown"),
        ]

        right_items = [
            ("Input 1:", "N/A"),
            ("Input 2:", "N/A"),
            ("Output 1:", "N/A"),
            ("Output 2:", "N/A"),
            ("Last Fault:", "None"),
            ("System State:", "Idle"),
        ]

        for row, (label_text, initial_val) in enumerate(left_items):
            lbl = ctk.CTkLabel(
                leftCol,
                text=label_text,
                font=lbl_font,
                text_color=LBL_COLOR,
            )
            lbl.grid(row=row, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)

            val = ctk.CTkLabel(
                leftCol,
                text=initial_val,
                font=val_font,
                text_color=VAL_COLOR,
            )
            val.grid(row=row, column=1, sticky="w", padx=10, pady=VERTICAL_PAD)
            self._value_labels[label_text] = val

        for row, (label_text, initial_val) in enumerate(right_items):
            lbl = ctk.CTkLabel(
                rightCol,
                text=label_text,
                font=lbl_font,
                text_color=LBL_COLOR,
            )
            lbl.grid(row=row, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)

            val = ctk.CTkLabel(
                rightCol,
                text=initial_val,
                font=val_font,
                text_color=VAL_COLOR,
            )
            val.grid(row=row, column=1, sticky="w", padx=10, pady=VERTICAL_PAD)
            self._value_labels[label_text] = val

        # ----- Optional notes / placeholder area -----
        notes_frame = ctk.CTkFrame(
            body,
            fg_color="transparent",
            border_width=2,
            border_color=COLOR_BLUE,
            corner_radius=8,
        )
        notes_frame.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            notes_frame,
            text="Additional Diagnostics / Reserved",
            font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
            text_color=COLOR_BLUE,
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.lblNotes = ctk.CTkLabel(
            notes_frame,
            text="Use this page for additional oven diagnostics, I/O states, currents, faults, or debug values.",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=COLOR_NUMBERS,
            justify="left",
            anchor="w",
        )
        self.lblNotes.pack(fill="x", padx=12, pady=(0, 8))

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

    def on_show(self):
        print("[DiagnosticsPage2] on_show")
        self.on_refresh()

    def on_hide(self):
        print("[DiagnosticsPage2] on_hide")

    def on_back(self):
        if hasattr(self.controller, "show_DiagnosticsPage"):
            self.controller.show_DiagnosticsPage()
        else:
            print("[DiagnosticsPage2] Controller missing show_DiagnosticsPage()")

    def on_refresh(self):
        print("[DiagnosticsPage2] Refreshed")

        # Placeholder values. Replace with real controller/serial values as needed.
        self._value_labels["Heater Current 1:"].configure(text="0.0 A")
        self._value_labels["Heater Current 2:"].configure(text="0.0 A")
        self._value_labels["Heater Current 3:"].configure(text="0.0 A")
        self._value_labels["Heater Current 4:"].configure(text="0.0 A")
        self._value_labels["Tray Present:"].configure(text="No")
        self._value_labels["Interlock Status:"].configure(text="OK")
        self._value_labels["Input 1:"].configure(text="Off")
        self._value_labels["Input 2:"].configure(text="Off")
        self._value_labels["Output 1:"].configure(text="Off")
        self._value_labels["Output 2:"].configure(text="Off")
        self._value_labels["Last Fault:"].configure(text="None")
        self._value_labels["System State:"].configure(text="Idle")


# ---- Standalone test harness ----
if __name__ == "__main__":

    class DummyController(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("DiagnosticsPage2 Test")
            self.geometry("1024x600")
            self.shared_data = {}

        def show_DiagnosticsPage(self):
            print("[DummyController] Returning to DiagnosticsPage")

    app = DummyController()
    page = DiagnosticsPage2(controller=app, shared_data=app.shared_data)
    page.pack(fill="both", expand=True)
    app.mainloop()
