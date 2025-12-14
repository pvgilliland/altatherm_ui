# HomePage_admin.py (FULL UPDATE with capped scaling)
from __future__ import annotations

import os
from datetime import datetime
import customtkinter as ctk
from PIL import Image
from typing import TYPE_CHECKING, Optional, Dict, Any

from play_sound import play_click

if TYPE_CHECKING:
    from multipage_controller import MultiPageController
    from SerialService import SerialService

from hmi_consts import HMISizePos
from PeriodicTimer import PeriodicTimer

from ui_bits import COLOR_NUMBERS, COLOR_BLUE, COLOR_FG
from hmi_consts import ASSETS_DIR, SETTINGS_DIR, PROGRAMS_DIR


class HomePage_admin(ctk.CTkFrame):
    def __init__(
        self, parent, controller: "MultiPageController", shared_data: Dict[str, Any]
    ):
        super().__init__(parent, fg_color=COLOR_FG)
        self.controller: "MultiPageController" = controller
        self.shared_data: Dict[str, Any] = shared_data

        self.serial: Optional["SerialService"] = getattr(
            self.controller, "serial", None
        )

        self._build_ui()
        self.add_log("HMI Started")

        self.timer: PeriodicTimer = PeriodicTimer(1.0, self.my_task)
        self.timer.start()

    # ---------------- UI ----------------

    def _build_ui(self) -> None:
        # ---- helpers ----
        def cap(v: int, mx: int) -> int:
            return min(int(v), int(mx))

        def cs(x: int, mx: int) -> int:
            return cap(HMISizePos.s(x), mx)

        def csx(x: int, mx: int) -> int:
            return cap(HMISizePos.sx(x), mx)

        def csy(y: int, mx: int) -> int:
            return cap(HMISizePos.sy(y), mx)

        # Root grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # ----------------------------
        # Logo (top)
        # ----------------------------
        try:
            img = Image.open(f"{ASSETS_DIR}/logo.png")
            self.logo_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(csx(650, 650), csy(90, 90)),
            )
        except Exception as e:
            print(f"[HomePage_admin] Failed to load logo: {e}")
            self.logo_img = None

        self.logo_label = ctk.CTkLabel(
            self, image=self.logo_img, text="", fg_color="transparent"
        )
        self.logo_label.grid(
            row=0,
            column=0,
            pady=(csy(15, 20), csy(10, 16)),
            sticky="n",
        )

        # ----------------------------
        # Button area container (single column; rows contain their own centering grids)
        # ----------------------------
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(
            row=1,
            column=0,
            sticky="n",
            padx=csx(40, 60),
            pady=csy(20, 40),
        )
        button_frame.grid_rowconfigure(0, weight=1)
        button_frame.grid_rowconfigure(1, weight=1)
        button_frame.grid_columnconfigure(0, weight=1)

        # ----------------------------
        # Shared button sizing (IDENTICAL for all 5)
        # ----------------------------
        btn_w = csx(300, 300)
        btn_h = csy(240, 240)

        font_btn = ctk.CTkFont(
            family="Arial",
            size=cs(34, 32),
            weight="bold",
        )

        btn_kwargs = dict(
            font=font_btn,
            corner_radius=cs(26, 26),
            border_width=2,
            fg_color=COLOR_FG,
            text_color=COLOR_BLUE,
            border_color=COLOR_BLUE,
            hover_color=COLOR_NUMBERS,
            width=btn_w,
            height=btn_h,
        )

        pad_y = csy(18, 28)
        pad_x = csx(30, 45)

        # ----------------------------
        # Row 0 (TOP): 3 buttons centered, NOT constrained by 3 equal columns
        # [flex][btn][gap][btn][gap][btn][flex]
        # ----------------------------
        top_row = ctk.CTkFrame(button_frame, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="nsew")
        top_row.grid_rowconfigure(0, weight=1)
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=0)
        top_row.grid_columnconfigure(2, weight=0)
        top_row.grid_columnconfigure(3, weight=0)
        top_row.grid_columnconfigure(4, weight=0)
        top_row.grid_columnconfigure(5, weight=0)
        top_row.grid_columnconfigure(6, weight=1)

        top_gap = csx(55, 75)

        self.manual_button = ctk.CTkButton(
            top_row, text="Manual", command=self.on_manual, **btn_kwargs
        )
        self.configure_button = ctk.CTkButton(
            top_row, text="Configure", command=self.on_configure, **btn_kwargs
        )
        self.fan_delay_button = ctk.CTkButton(
            top_row, text="Fan Delay", command=self.on_fan_delay, **btn_kwargs
        )

        self.manual_button.grid(
            row=0, column=1, padx=(pad_x, top_gap // 2), pady=pad_y, sticky="n"
        )
        self.configure_button.grid(
            row=0, column=3, padx=(top_gap // 2, top_gap // 2), pady=pad_y, sticky="n"
        )
        self.fan_delay_button.grid(
            row=0, column=5, padx=(top_gap // 2, pad_x), pady=pad_y, sticky="n"
        )

        # ----------------------------
        # Row 1 (BOTTOM): 2 buttons centered and closer together
        # [flex][btn][gap][btn][flex]
        # ----------------------------
        bottom_row = ctk.CTkFrame(button_frame, fg_color="transparent")
        bottom_row.grid(row=1, column=0, sticky="nsew")
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

        center_gap = csx(60, 80)

        self.diagnostics_button.grid(
            row=0, column=1, padx=(pad_x, center_gap // 2), pady=pad_y, sticky="n"
        )
        self.exit_admin_button.grid(
            row=0, column=3, padx=(center_gap // 2, pad_x), pady=pad_y, sticky="n"
        )

        # ----------------------------
        # Log textbox (start hidden)
        # ----------------------------
        self.log_textbox = ctk.CTkTextbox(
            self,
            width=csx(750, 900),
            height=csy(120, 150),
            corner_radius=cs(10, 12),
            fg_color=COLOR_FG,
            border_width=2,
            border_color=COLOR_BLUE,
            font=("Courier New", cs(14, 16), "normal"),
            text_color=COLOR_NUMBERS,
        )
        self.log_textbox.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=csx(20, 40),
            pady=(0, csx(20, 40)),
        )
        self.log_textbox.configure(state="disabled")
        self.log_textbox.grid_remove()

        # Secret hotspot
        self._add_secret_exit_hotspot(csx, csy)

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

    def _add_secret_exit_hotspot(self, csx, csy) -> None:
        """
        Invisible hot-corner (top-left). Double-click to exit the app.
        """
        size_w = csx(75, 90)
        size_h = csy(75, 90)

        self._exit_hotspot = ctk.CTkLabel(
            self,
            text="",
            fg_color="transparent",
            width=size_w,
            height=size_h,
        )
        self._exit_hotspot.place(relx=0, rely=0, anchor="nw")
        self._exit_hotspot.bind("<Double-Button-1>", self._on_secret_exit)

    def _on_secret_exit(self, _event=None) -> None:
        try:
            if hasattr(self.controller, "on_close"):
                try:
                    self.controller.on_close()
                except Exception:
                    pass
            self.controller.destroy()
        except Exception:
            os._exit(0)

    # Kept for compatibility (not currently used)
    def _on_serial_line(self, line: str) -> None:
        print("[HomePage]: " + line)
