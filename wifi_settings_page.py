"""
wifi_settings_page.py

Step-by-step Wi-Fi connection workflow page.

Uses original wifi_manager implementation:
    from wifi_manager import CommandResult, WifiNetwork, get_wifi_manager

Behavior:
    - Step 1: Turn Wi-Fi On
    - Step 2: Find Networks
    - Step 3: Select Network
    - Step 4: Enter Password
    - Step 5: Connect to Wi-Fi
    - When connected, automatically opens SoftwareUpdatePage
"""

from __future__ import annotations

import threading
import time
import customtkinter as ctk

from software_update_page import SoftwareUpdatePage
from wifi_manager import CommandResult, WifiNetwork, get_wifi_manager


try:
    from hmi_consts import HMIColors, HMISizePos
except Exception:
    class HMIColors:
        color_blue = "#2d6cdf"
        color_fg = "#eafaff"
        color_numbers = "#1457c9"
        TEXTBOX_BG_COLOR = "#f7f7ff"

    class HMISizePos:
        SCREEN_RES = "1280x800"
        BTN_HEIGHT = 84

        @classmethod
        def sx(cls, v):
            return int(v)

        @classmethod
        def sy(cls, v):
            return int(v)


try:
    from ui_bits import COLOR_FG, COLOR_BLUE, COLOR_NUMBERS
except Exception:
    COLOR_FG = HMIColors.color_fg
    COLOR_BLUE = HMIColors.color_blue
    COLOR_NUMBERS = HMIColors.color_numbers


GREEN = "#1f8a2e"
GREEN_LIGHT = "#eaffea"
GREEN_BORDER = "#65b96a"

WARNING = "#b36b00"
WARNING_LIGHT = "#fff7e6"
WARNING_BORDER = "#e0a22d"

WHITE = "#ffffff"
CARD_BG = "#f4ffff"
TEXT_DARK = "#1f2937"
BORDER_BLUE = COLOR_BLUE


class WifiSettingsPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, fg_color=COLOR_FG)

        self.controller = controller
        self.wifi = get_wifi_manager()

        self.network_rows: list[ctk.CTkFrame] = []
        self.networks: list[WifiNetwork] = []

        self.selected_ssid = ctk.StringVar(value="")
        self.show_password_var = ctk.BooleanVar(value=False)

        self._connected = False
        self._opening_update_page = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_ui()
        self.update_wifi_status_threaded()

    # ============================================================
    # Styles
    # ============================================================

    def _font(self, size: int, bold: bool = True):
        return ctk.CTkFont(family="Arial", size=size, weight="bold" if bold else "normal")

    def _outline_button_style(self) -> dict:
        return {
            "fg_color": COLOR_FG,
            "hover_color": "#d6ecff",
            "border_color": COLOR_BLUE,
            "border_width": 1,
            "text_color": COLOR_BLUE,
            "corner_radius": 14,
            "font": self._font(17),
        }

    # ============================================================
    # Build UI
    # ============================================================

    def _build_ui(self):
        self._build_header()
        self._build_status_banner()
        self._build_main_area()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_FG)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Connect to the Internet to Download Updates",
            text_color=COLOR_BLUE,
            font=self._font(30),
        ).grid(row=0, column=0)

        ctk.CTkLabel(
            header,
            text=(
                "Follow the steps below. When connected to the Internet, "
                "the Software Update page will open automatically."
            ),
            text_color=COLOR_BLUE,
            font=self._font(18),
        ).grid(row=1, column=0, pady=(4, 8))

        ctk.CTkFrame(header, height=2, fg_color=COLOR_BLUE).grid(
            row=2, column=0, sticky="ew"
        )

    def _build_status_banner(self):
        self.status_banner = ctk.CTkFrame(
            self,
            fg_color=WARNING_LIGHT,
            border_color=WARNING_BORDER,
            border_width=1,
            corner_radius=10,
            height=92,
        )
        self.status_banner.grid(row=1, column=0, sticky="ew", padx=18, pady=(16, 16))
        self.status_banner.grid_propagate(False)
        self.status_banner.grid_columnconfigure(0, weight=1)

        self.status_title = ctk.CTkLabel(
            self.status_banner,
            text="!  Internet Not Connected",
            text_color=WARNING,
            font=self._font(30),
        )
        self.status_title.grid(row=0, column=0, pady=(18, 0))

        self.status_detail = ctk.CTkLabel(
            self.status_banner,
            text="Connect to Wi-Fi to continue.",
            text_color=WARNING,
            font=self._font(18),
        )
        self.status_detail.grid(row=1, column=0, pady=(4, 0))

    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color=COLOR_FG)
        main.grid(row=2, column=0, sticky="nsew", padx=18)
        main.grid_columnconfigure(0, weight=0)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self._build_steps_panel(main)
        self._build_network_panel(main)

    def _build_steps_panel(self, parent):
        panel = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            border_color=COLOR_BLUE,
            border_width=1,
            corner_radius=8,
            width=390,
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        panel.grid_propagate(False)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Connection Steps",
            text_color=COLOR_BLUE,
            font=self._font(20),
        ).grid(row=0, column=0, pady=(18, 14))

        self.step_rows = {}

        steps = [
            (1, "Turn Wi-Fi On"),
            (2, "Find Networks"),
            (3, "Select Network"),
            (4, "Enter Password"),
            (5, "Connect to Wi-Fi"),
        ]

        for number, text in steps:
            row = self._create_step_row(panel, number, text)
            row.grid(row=number, column=0, sticky="ew", padx=34, pady=3)
            self.step_rows[number] = row

        ctk.CTkFrame(panel, height=1, fg_color=COLOR_BLUE).grid(
            row=6, column=0, sticky="ew", padx=18, pady=(18, 18)
        )

        self.enable_button = ctk.CTkButton(
            panel,
            text="📶   1. Turn Wi-Fi On",
            command=self.enable_wifi_threaded,
            height=52,
            **self._outline_button_style(),
        )
        self.enable_button.grid(row=7, column=0, sticky="ew", padx=26, pady=(2, 10))

        self.scan_button = ctk.CTkButton(
            panel,
            text="🔍   2. Find Networks",
            command=self.scan_wifi_threaded,
            height=52,
            **self._outline_button_style(),
        )
        self.scan_button.grid(row=8, column=0, sticky="ew", padx=26, pady=(0, 10))

    def _create_step_row(self, parent, number: int, text: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid_columnconfigure(1, weight=1)

        circle = ctk.CTkLabel(
            row,
            text=str(number),
            width=34,
            height=34,
            corner_radius=17,
            fg_color=COLOR_FG,
            text_color=COLOR_BLUE,
            font=self._font(18),
        )
        circle.grid(row=0, column=0, padx=(0, 16))

        label = ctk.CTkLabel(
            row,
            text=text,
            text_color=COLOR_NUMBERS,
            font=self._font(18),
            anchor="w",
        )
        label.grid(row=0, column=1, sticky="w")

        check = ctk.CTkLabel(
            row,
            text="",
            text_color=GREEN,
            font=self._font(30),
            width=32,
        )
        check.grid(row=0, column=2, padx=(8, 0))

        row.circle = circle
        row.check = check
        return row

    def _build_network_panel(self, parent):
        panel = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            border_color=COLOR_BLUE,
            border_width=1,
            corner_radius=8,
        )
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        self.step_bar = ctk.CTkLabel(
            panel,
            text="Step 3: Select Your Wi-Fi Network",
            fg_color="#303030",
            text_color="#dffcff",
            corner_radius=4,
            height=32,
            font=self._font(18),
        )
        self.step_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 10))

        self.network_list_frame = ctk.CTkScrollableFrame(
            panel,
            fg_color=COLOR_FG,
            border_color=COLOR_BLUE,
            border_width=1,
            corner_radius=10,
            height=210,
        )
        self.network_list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.network_list_frame.grid_columnconfigure(0, weight=1)

        form = ctk.CTkFrame(
            panel,
            fg_color=COLOR_FG,
            border_color=COLOR_BLUE,
            border_width=1,
            corner_radius=8,
        )
        form.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form,
            text="Selected Network:",
            text_color=COLOR_BLUE,
            font=self._font(17),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(12, 6))

        self.ssid_entry = ctk.CTkEntry(
            form,
            textvariable=self.selected_ssid,
            height=38,
            fg_color=HMIColors.TEXTBOX_BG_COLOR,
            border_color=COLOR_BLUE,
            text_color=COLOR_NUMBERS,
            font=self._font(17),
        )
        self.ssid_entry.grid(row=0, column=1, sticky="ew", padx=(12, 24), pady=(12, 6))

        ctk.CTkLabel(
            form,
            text="4. Password:",
            text_color=COLOR_BLUE,
            font=self._font(17),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=6)

        self.password_entry = ctk.CTkEntry(
            form,
            height=38,
            show="*",
            fg_color=HMIColors.TEXTBOX_BG_COLOR,
            border_color=COLOR_BLUE,
            text_color=COLOR_NUMBERS,
            font=self._font(17),
        )
        self.password_entry.grid(row=1, column=1, sticky="ew", padx=(12, 24), pady=6)
        self.password_entry.bind(
            "<KeyRelease>",
            lambda _event: self._set_step_done(4, bool(self.password_entry.get())),
        )

        self.show_password_checkbox = ctk.CTkCheckBox(
            form,
            text="Show password",
            variable=self.show_password_var,
            command=self.toggle_password_visibility,
            text_color=COLOR_BLUE,
            font=self._font(16),
            fg_color=COLOR_BLUE,
            border_color=COLOR_BLUE,
            hover_color=COLOR_NUMBERS,
            checkbox_width=26,
            checkbox_height=26,
        )
        self.show_password_checkbox.grid(
            row=2, column=1, sticky="w", padx=(12, 24), pady=(4, 14)
        )

        self.connect_button = ctk.CTkButton(
            form,
            text="5. Connect to Wi-Fi",
            command=self.connect_wifi_threaded,
            height=58,
            corner_radius=14,
            fg_color=COLOR_BLUE,
            hover_color=COLOR_NUMBERS,
            text_color=WHITE,
            font=self._font(21),
        )
        self.connect_button.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=22, pady=(4, 20)
        )

    def _build_footer(self):
        bottom = ctk.CTkFrame(self, fg_color=COLOR_FG, height=120)
        bottom.grid(row=3, column=0, sticky="ew", padx=18, pady=(20, 22))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_columnconfigure(2, weight=1)

        self.exit_button = ctk.CTkButton(
            bottom,
            text="←  Back" if self.controller else "Exit",
            command=self.exit_or_back,
            width=225,
            height=84,
            **self._outline_button_style(),
        )
        self.exit_button.grid(row=0, column=0, sticky="w")

        self.refresh_button = ctk.CTkButton(
            bottom,
            text="Refresh Status",
            command=self.update_wifi_status_threaded,
            width=230,
            height=84,
            **self._outline_button_style(),
        )
        self.refresh_button.grid(row=0, column=2, sticky="e")

    # ============================================================
    # Thread helpers
    # ============================================================

    def run_worker(self, worker_func):
        def wrapper():
            self.after(0, lambda: self.set_busy(True))
            try:
                worker_func()
            finally:
                self.after(0, lambda: self.set_busy(False))

        threading.Thread(target=wrapper, daemon=True).start()

    def set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"

        for widget in (
            self.scan_button,
            self.connect_button,
            self.refresh_button,
            self.exit_button,
        ):
            widget.configure(state=state)

        if busy:
            self.enable_button.configure(state="disabled")

    # ============================================================
    # Wi-Fi actions using original wifi_manager
    # ============================================================

    def update_wifi_status_threaded(self):
        def worker():
            result = self.wifi.get_status()
            enabled = self.wifi.is_wifi_enabled()

            self.after(0, lambda: self._set_step_done(1, enabled))

            self.after(
                0,
                lambda: self.enable_button.configure(
                    state="disabled" if enabled else "normal"
                ),
            )

            self.after(
                0,
                lambda r=result: self.show_result("Status", r)
            )

            # Optional auto-open if already connected to a selected SSID.
            current_ssid = self.selected_ssid.get().strip()
            if current_ssid and self.wifi.is_connected_to(current_ssid):
                self.after(0, lambda: self._handle_connected(current_ssid))

        self.run_worker(worker)

    def enable_wifi_threaded(self):
        def worker():
            self.after(0, lambda: self.set_status("Enabling Wi-Fi..."))
            result = self.wifi.enable_wifi()

            if result.ok:
                self.after(0, lambda: self._set_step_done(1, True))

            self.after(0, lambda r=result: self.show_result("Enable", r))
            self.after(750, self.update_wifi_status_threaded)

        self.run_worker(worker)

    def scan_wifi_threaded(self):
        def worker():
            self.after(0, lambda: self.set_status("Scanning Wi-Fi networks..."))

            result, networks = self.wifi.scan_networks()

            if result.ok:
                self.after(0, lambda: self._set_step_done(2, True))
                self.after(0, lambda n=networks: self.populate_network_list(n))
                self.after(0, lambda: self.set_status("Select your Wi-Fi network."))
            else:
                self.after(0, lambda r=result: self.show_result("Scan", r))

        self.run_worker(worker)

    def connect_wifi_threaded(self):
        def worker():
            ssid = self.selected_ssid.get().strip()
            password = self.password_entry.get().strip()

            if not ssid:
                self.after(0, lambda: self.set_status_not_connected("Select a Wi-Fi network first."))
                return

            self.after(0, lambda: self._set_step_done(3, True))
            self.after(0, lambda: self._set_step_done(4, bool(password)))
            self.after(0, lambda: self.set_status(f"Connecting to {ssid}..."))

            result = self.wifi.connect(ssid, password)

            if not result.ok:
                self.after(0, lambda r=result: self.show_result("Connect", r))
                return

            connected = False

            for attempt in range(10):
                self.after(
                    0,
                    lambda a=attempt: self.set_status(
                        f"Verifying Wi-Fi connection... {a + 1}/10"
                    ),
                )

                time.sleep(1)

                if self.wifi.is_connected_to(ssid):
                    connected = True
                    break

            if connected:
                self.after(0, lambda: self._handle_connected(ssid))
            else:
                self.after(
                    0,
                    lambda: self.set_status_not_connected(
                        f"Failed to connect to {ssid}. Check the password."
                    ),
                )

        self.run_worker(worker)

    # ============================================================
    # Network list
    # ============================================================

    def populate_network_list(self, networks: list[WifiNetwork]):
        for row in self.network_rows:
            row.destroy()

        self.network_rows.clear()
        self.networks = networks

        if not networks:
            self.set_status_not_connected("No Wi-Fi networks found.")
            return

        for index, network in enumerate(networks):
            self._add_network_row(index, network)

        self.select_ssid(networks[0].ssid)

    def _add_network_row(self, index: int, network: WifiNetwork):
        row = ctk.CTkFrame(
            self.network_list_frame,
            fg_color="#dcefff" if index == 0 else "transparent",
            border_color=COLOR_BLUE if index == 0 else "transparent",
            border_width=1 if index == 0 else 0,
            corner_radius=10,
            height=62,
        )
        row.grid(row=index, column=0, sticky="ew", padx=0, pady=4)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=1)
        row.grid_columnconfigure(3, weight=1)

        icon = ctk.CTkLabel(
            row,
            text="📶",
            text_color=COLOR_BLUE if index == 0 else TEXT_DARK,
            font=self._font(28),
            width=60,
        )
        icon.grid(row=0, column=0, padx=(8, 8), pady=12)

        ssid_label = ctk.CTkLabel(
            row,
            text=network.ssid,
            text_color=COLOR_NUMBERS,
            font=self._font(17),
            anchor="w",
        )
        ssid_label.grid(row=0, column=1, sticky="w", pady=12)

        signal = f"{network.signal}%" if network.signal and "%" not in str(network.signal) else str(network.signal)

        signal_label = ctk.CTkLabel(
            row,
            text=f"Signal: {signal}",
            text_color=COLOR_NUMBERS,
            font=self._font(15, bold=False),
        )
        signal_label.grid(row=0, column=2, sticky="w", pady=12)

        security_label = ctk.CTkLabel(
            row,
            text=f"Security: {network.security or 'Open/Unknown'}",
            text_color=COLOR_NUMBERS,
            font=self._font(15, bold=False),
        )
        security_label.grid(row=0, column=3, sticky="w", pady=12)

        def select():
            self.select_ssid(network.ssid)
            self._highlight_selected_network(network.ssid)

        for widget in (row, icon, ssid_label, signal_label, security_label):
            widget.bind("<Button-1>", lambda _event: select())

        self.network_rows.append(row)

    def _highlight_selected_network(self, ssid: str):
        for row, network in zip(self.network_rows, self.networks):
            selected = network.ssid == ssid
            row.configure(
                fg_color="#dcefff" if selected else "transparent",
                border_color=COLOR_BLUE if selected else "transparent",
                border_width=1 if selected else 0,
            )

    def select_ssid(self, ssid: str):
        self.selected_ssid.set(ssid)
        self._set_step_done(3, True)
        self.set_status(f"Selected: {ssid}")

    # ============================================================
    # Status / steps
    # ============================================================

    def set_status(self, text: str):
        self.status_banner.configure(
            fg_color=WARNING_LIGHT,
            border_color=WARNING_BORDER,
        )
        self.status_title.configure(
            text="!  Internet Not Connected",
            text_color=WARNING,
        )
        self.status_detail.configure(
            text=text,
            text_color=WARNING,
        )

    def set_status_connected(self, detail: str):
        self.status_banner.configure(
            fg_color=GREEN_LIGHT,
            border_color=GREEN_BORDER,
        )
        self.status_title.configure(
            text="✓  Internet Connected",
            text_color=GREEN,
        )
        self.status_detail.configure(
            text=detail,
            text_color=GREEN,
        )

    def set_status_not_connected(self, detail: str):
        self.status_banner.configure(
            fg_color=WARNING_LIGHT,
            border_color=WARNING_BORDER,
        )
        self.status_title.configure(
            text="!  Internet Not Connected",
            text_color=WARNING,
        )
        self.status_detail.configure(
            text=detail,
            text_color=WARNING,
        )

    def show_result(self, action: str, result: CommandResult):
        msg = result.message or result.stdout or result.stderr or "OK"

        if result.ok:
            self.set_status(f"{action}: {msg}")
        else:
            self.set_status_not_connected(f"{action} Error: {msg}")

    def _set_step_done(self, step_number: int, done: bool):
        row = self.step_rows.get(step_number)
        if not row:
            return

        row.circle.configure(
            fg_color=COLOR_BLUE if done else COLOR_FG,
            text_color=WHITE if done else COLOR_BLUE,
        )
        row.check.configure(text="✓" if done else "")

    def _handle_connected(self, ssid: str):
        self._connected = True
        self._set_step_done(5, True)

        self.set_status_connected(
            "Internet access confirmed. Opening Software Update page..."
        )

        if not self._opening_update_page:
            self._opening_update_page = True
            self.after(1200, self.open_software_update_page)

    def reset_steps_to_beginning(self):
        self._connected = False
        self._opening_update_page = False

        self.selected_ssid.set("")
        self.password_entry.delete(0, "end")
        self.show_password_var.set(False)
        self.password_entry.configure(show="*")

        for row in self.network_rows:
            row.destroy()

        self.network_rows.clear()
        self.networks.clear()

        for step_number in range(1, 6):
            self._set_step_done(step_number, False)

        self.set_status_not_connected("Step 1: Turn Wi-Fi on to begin.")

    # ============================================================
    # Misc
    # ============================================================

    def toggle_password_visibility(self):
        self.password_entry.configure(
            show="" if self.show_password_var.get() else "*"
        )

    def open_software_update_page(self):
        if self.controller and hasattr(self.controller, "show_SoftwareUpdatePage"):
            self.controller.show_SoftwareUpdatePage()
        else:
            self.show_software_update_page_standalone()

    def show_software_update_page_standalone(self):
        for child in self.master.winfo_children():
            child.destroy()

        page = SoftwareUpdatePage(self.master)
        page.grid(row=0, column=0, sticky="nsew")

    def exit_or_back(self):
        if self.controller and hasattr(self.controller, "show_HomePage_admin"):
            self.controller.show_HomePage_admin()
        elif self.controller and hasattr(self.controller, "show_HomePage"):
            self.controller.show_HomePage()
        else:
            self.master.destroy()

    def on_show(self):
        self._opening_update_page = False
        self.update_wifi_status_threaded()
        self.reset_steps_to_beginning()


class StandaloneWifiApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("CTk")
        self.geometry("1280x800")
        self.minsize(800, 480)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        page = WifiSettingsPage(self)
        page.grid(row=0, column=0, sticky="nsew")


if __name__ == "__main__":
    app = StandaloneWifiApp()
    app.mainloop()