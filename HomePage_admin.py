# HomePage.py (IntelliSense-enhanced)
from __future__ import annotations

import os
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
from typing import TYPE_CHECKING, Optional, Dict, Any

from play_sound import play_click

# Only import these for the type checker to avoid circular imports at runtime
if TYPE_CHECKING:
    from MultiPageController import MultiPageController
    from SerialService import SerialService

from hmi_consts import HMIColors, HMISerial, HMISizePos
from PeriodicTimer import PeriodicTimer

# from ReusableDialog import ReusableDialog

# Use the same colors as TimePowerPage for a consistent look
from ui_bits import COLOR_NUMBERS, COLOR_BLUE, COLOR_FG
from hmi_consts import ASSETS_DIR, SETTINGS_DIR, PROGRAMS_DIR


class HomePage_admin(ctk.CTkFrame):
    def __init__(
        self, parent, controller: "MultiPageController", shared_data: Dict[str, Any]
    ):
        # Match TimePowerPage background
        super().__init__(parent, fg_color=COLOR_FG)
        self.controller: "MultiPageController" = controller
        self.shared_data: Dict[str, Any] = shared_data

        # Serial: use the shared SerialService owned by controller (no direct pyserial here)
        self.serial: Optional["SerialService"] = getattr(
            self.controller, "serial", None
        )

        self._build_ui()
        self.add_log("HMI Started")

        # Keep your existing periodic timer hook (no serial dependency)
        self.timer: PeriodicTimer = PeriodicTimer(1.0, self.my_task)  # 1.0 sec
        self.timer.start()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        # Root grid: logo (row 0), button area (row 1), optional log (row 2)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(
            1, weight=1
        )  # <-- allow button area to expand (big cards)
        self.grid_rowconfigure(2, weight=0)

        # ----------------------------
        # Logo (top)
        # ----------------------------
        try:
            img = Image.open(f"{ASSETS_DIR}/logo.png")
            self.logo_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(
                    HMISizePos.sx(650),
                    HMISizePos.sy(90),
                ),  # bigger like your reference
            )
        except Exception as e:
            print(f"[HomePage_admin] Failed to load logo: {e}")
            self.logo_img = None

        self.logo_label = ctk.CTkLabel(
            self, image=self.logo_img, text="", fg_color="transparent"
        )
        self.logo_label.grid(
            row=0, column=0, pady=(HMISizePos.sy(15), HMISizePos.sy(10)), sticky="n"
        )

        # ----------------------------
        # Button area container (RESPONSIVE GRID)
        # ----------------------------
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(
            row=1,
            column=0,
            sticky="n",  # keep the block anchored near top-center like your screenshot
            padx=HMISizePos.sx(40),
            pady=HMISizePos.sy(20),
        )

        # 3 columns x 2 rows, responsive inside the block (this creates big "cards")
        for r in range(2):
            button_frame.grid_rowconfigure(r, weight=1, uniform="row")
        for c in range(3):
            button_frame.grid_columnconfigure(c, weight=1, uniform="col")

        # --- Card sizing (IMPORTANT) ---
        # Don’t use HMISizePos.BTN_WIDTH/BTN_HEIGHT (those are giving you pills) :contentReference[oaicite:1]{index=1}
        btn_w = HMISizePos.sx(360)
        btn_h = HMISizePos.sy(240)

        font_btn = ctk.CTkFont(family="Arial", size=HMISizePos.s(34), weight="bold")

        btn_kwargs = dict(
            font=font_btn,
            corner_radius=HMISizePos.s(26),
            border_width=2,
            fg_color=COLOR_FG,  # outlined-card look (same fill as background)
            text_color=COLOR_BLUE,
            border_color=COLOR_BLUE,
            hover_color=COLOR_NUMBERS,
            width=btn_w,
            height=btn_h,
        )

        # --- Row 0 (top): Manual | Configure | Fan Delay ---
        self.manual_button = ctk.CTkButton(
            button_frame, text="Manual", command=self.on_manual, **btn_kwargs
        )
        self.configure_button = ctk.CTkButton(
            button_frame, text="Configure", command=self.on_configure, **btn_kwargs
        )
        self.fan_delay_button = ctk.CTkButton(
            button_frame, text="Fan Delay", command=self.on_fan_delay, **btn_kwargs
        )

        pad_x = HMISizePos.sx(30)
        pad_y = HMISizePos.sy(18)

        self.manual_button.grid(row=0, column=0, padx=pad_x, pady=pad_y, sticky="nsew")
        self.configure_button.grid(
            row=0, column=1, padx=pad_x, pady=pad_y, sticky="nsew"
        )
        self.fan_delay_button.grid(
            row=0, column=2, padx=pad_x, pady=pad_y, sticky="nsew"
        )

        # --- Row 1 (bottom): centered pair using a nested frame ---
        bottom_row = ctk.CTkFrame(button_frame, fg_color="transparent")
        bottom_row.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # Inner grid: [stretch][Diagnostics][gap][Exit][stretch]
        bottom_row.grid_rowconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(1, weight=0)
        bottom_row.grid_columnconfigure(2, weight=0)
        bottom_row.grid_columnconfigure(3, weight=0)
        bottom_row.grid_columnconfigure(4, weight=1)

        self.diagnostics_button = ctk.CTkButton(
            bottom_row, text="Diagnostics", command=self.on_diagnostics, **btn_kwargs
        )
        self.exit_admin_button = ctk.CTkButton(
            bottom_row, text="Exit Admin", command=self.on_exit_admin, **btn_kwargs
        )

        mid_gap = HMISizePos.sx(70)

        self.diagnostics_button.grid(
            row=0, column=1, padx=(0, mid_gap), pady=pad_y, sticky="nsew"
        )
        self.exit_admin_button.grid(
            row=0, column=3, padx=(mid_gap, 0), pady=pad_y, sticky="nsew"
        )

        # ----------------------------
        # Log textbox (keep your existing behavior; start hidden)
        # ----------------------------
        self.log_textbox = ctk.CTkTextbox(
            self,
            width=HMISizePos.sx(750),
            height=HMISizePos.sy(120),
            corner_radius=HMISizePos.s(10),
            fg_color=COLOR_FG,
            border_width=2,
            border_color=COLOR_BLUE,
            font=("Courier New", HMISizePos.s(14), "normal"),
            text_color=COLOR_NUMBERS,
        )
        self.log_textbox.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=HMISizePos.PADDING,
            pady=(0, HMISizePos.PADDING),
        )
        self.log_textbox.configure(state="disabled")
        self.log_textbox.grid_remove()

        # Secret hotspot
        self._add_secret_exit_hotspot()

    # ------------- Log helpers -------------
    def show_log(self, show: bool) -> None:
        if show:
            self.log_textbox.grid()
        else:
            self.log_textbox.grid_remove()

    def add_log(self, message: str) -> None:
        if not hasattr(self, "log_textbox") or self.log_textbox is None:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("1.0", full_message)
        self.log_textbox.configure(state="disabled")

    def _on_serial_line(self, line: str) -> None:
        """Called (UI-thread safe) when SerialService reads a full line."""
        print("[HomePage]: " + line)

    # ------------- UI callbacks -------------
    def on_manual(self) -> None:
        play_click()
        self.controller.show_TimePowerPage()

    def on_configure(self) -> None:
        play_click()
        self.controller.show_SelectProgramPage()

    def on_fan_delay(self) -> None:
        play_click()
        self.controller.show_TimePage()

    def on_diagnostics(self) -> None:
        play_click()
        self.controller.show_DiagnosticsPage()

    def on_exit_admin(self) -> None:
        play_click()
        self.controller.exit_admin_mode()
        self.controller.show_HomePage()

    # ------------- Lifecycle -------------
    def on_close(self) -> None:
        if self.serial:
            try:
                self.serial.remove_listener(self._on_serial_line)
            except Exception:
                pass
        self.destroy()

    # ------------- Periodic work -------------
    def my_task(self) -> None:
        pass

    def _add_secret_exit_hotspot(self) -> None:
        """
        Invisible hot-corner (top-left). Double-click to exit the app.
        """
        size_w = HMISizePos.sx(75)
        size_h = HMISizePos.sy(75)

        self._exit_hotspot = ctk.CTkLabel(
            self,
            text="",
            fg_color="transparent",  # invisible but clickable
            width=size_w,
            height=size_h,
        )
        # Do NOT pass width/height to place() for CTk widgets
        self._exit_hotspot.place(relx=0, rely=0, anchor="nw")
        self._exit_hotspot.bind("<Double-Button-1>", self._on_secret_exit)

    def _on_secret_exit(self, _event=None) -> None:
        """
        Safely tear down the app. If the controller is a CTk root window,
        destroy it; as a last resort, hard-exit the process.
        """
        try:
            # Prefer graceful shutdown
            if hasattr(self.controller, "on_close"):
                try:
                    self.controller.on_close()  # if your controller defines cleanup
                except Exception:
                    pass
            self.controller.destroy()
        except Exception:
            # Fallback: force exit if something blocks destroy (rare)
            os._exit(0)
