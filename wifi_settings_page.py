"""
wifi_settings_page.py

Standalone CustomTkinter Wi-Fi settings page.

Works on:
    - Raspberry Pi OS / Linux using nmcli
    - Windows using netsh + PowerShell

Run:
    python wifi_settings_page.py

Install dependency:
    pip install customtkinter
"""

from __future__ import annotations

import threading
import customtkinter as ctk
from software_update_page import SoftwareUpdatePage
from wifi_manager import CommandResult, WifiNetwork, get_wifi_manager

# Use the same palette/sizing as DiagnosticsPage.
try:
    from hmi_consts import HMIColors, HMISizePos
except Exception:  # Keeps this file runnable standalone during early testing.
    class HMIColors:
        color_blue = "#89C8F8"
        color_fg = "#DAFAFF"
        color_numbers = "#3776C3"
        TEXTBOX_BG_COLOR = "#F7F7FF"

    class HMISizePos:
        SCREEN_RES = "800x480"
        BTN_HEIGHT = 64

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


class WifiSettingsPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, fg_color=COLOR_FG)

        self.controller = controller
        self.wifi = get_wifi_manager()
        self.network_buttons: list[ctk.CTkButton] = []
        self.selected_ssid = ctk.StringVar(value="")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()
        self.update_wifi_status_threaded()

    def _button_style(self) -> dict:
        """DiagnosticsPage-style button colors."""
        return {
            "font": ctk.CTkFont(family="Arial", size=18, weight="bold"),
            "fg_color": HMIColors.color_fg,
            "text_color": HMIColors.color_blue,
            "corner_radius": 20,
            "border_width": 2,
            "border_color": HMIColors.color_blue,
            "hover_color": HMIColors.color_numbers,
        }

    def _build_ui(self):
        btn_style = self._button_style()
        lbl_font = ctk.CTkFont(family="Arial", size=20, weight="bold")
        value_font = ctk.CTkFont(family="Arial", size=18, weight="bold")

        # ----- Header: same light background + blue title/divider as DiagnosticsPage -----
        header = ctk.CTkFrame(self, fg_color=COLOR_FG)
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        title = ctk.CTkLabel(
            header,
            text="Wi-Fi Settings",
            text_color=COLOR_BLUE,
            font=("Arial", 20, "bold"),
        )
        title.pack(pady=(4, 8))

        ctk.CTkFrame(header, height=2, fg_color=COLOR_BLUE).pack(
            fill="x", padx=2, pady=(0, 6)
        )

        self.status_label = ctk.CTkLabel(
            header,
            text="Status: Unknown",
            font=value_font,
            text_color=COLOR_NUMBERS,
        )
        self.status_label.pack(pady=(2, 6))

        # ----- Body card: same border/background style as DiagnosticsPage -----
        body = ctk.CTkFrame(
            self,
            fg_color=COLOR_FG,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BLUE,
        )
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        button_frame = ctk.CTkFrame(body, fg_color=COLOR_FG)
        button_frame.grid(row=0, column=0, pady=(10, 4))

        self.enable_button = ctk.CTkButton(
            button_frame,
            text="Enable Wi-Fi",
            width=HMISizePos.sx(160),
            height=HMISizePos.sy(44),
            command=self.enable_wifi_threaded,
            **btn_style,
        )
        self.enable_button.grid(row=0, column=0, padx=10, pady=10)

        self.disable_button = ctk.CTkButton(
            button_frame,
            text="Disable Wi-Fi",
            width=HMISizePos.sx(160),
            height=HMISizePos.sy(44),
            command=self.disable_wifi_threaded,
            **btn_style,
        )
        self.disable_button.grid(row=0, column=1, padx=10, pady=10)

        self.scan_button = ctk.CTkButton(
            button_frame,
            text="Scan Networks",
            width=HMISizePos.sx(160),
            height=HMISizePos.sy(44),
            command=self.scan_wifi_threaded,
            **btn_style,
        )
        self.scan_button.grid(row=0, column=2, padx=10, pady=10)

        selected_frame = ctk.CTkFrame(
            body,
            fg_color=COLOR_FG,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BLUE,
        )
        selected_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        selected_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            selected_frame,
            text="Selected SSID:",
            font=lbl_font,
            text_color=COLOR_BLUE,
        ).grid(row=0, column=0, padx=10, pady=10, sticky="e")

        self.ssid_entry = ctk.CTkEntry(
            selected_frame,
            textvariable=self.selected_ssid,
            font=value_font,
            text_color=COLOR_NUMBERS,
            fg_color=HMIColors.TEXTBOX_BG_COLOR,
            border_color=COLOR_BLUE,
            border_width=2,
        )
        self.ssid_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(
            selected_frame,
            text="Password:",
            font=lbl_font,
            text_color=COLOR_BLUE,
        ).grid(row=1, column=0, padx=10, pady=10, sticky="e")

        self.password_entry = ctk.CTkEntry(
            selected_frame,
            show="*",
            font=value_font,
            text_color=COLOR_NUMBERS,
            fg_color=HMIColors.TEXTBOX_BG_COLOR,
            border_color=COLOR_BLUE,
            border_width=2,
        )
        self.password_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.show_password_var = ctk.BooleanVar(value=False)
        self.show_password_checkbox = ctk.CTkCheckBox(
            selected_frame,
            text="Show password",
            variable=self.show_password_var,
            command=self.toggle_password_visibility,
            font=value_font,
            text_color=COLOR_BLUE,
            border_color=COLOR_BLUE,
            fg_color=COLOR_BLUE,
            hover_color=COLOR_NUMBERS,
            checkbox_width=28,
            checkbox_height=28,
        )
        self.show_password_checkbox.grid(
            row=2, column=1, padx=10, pady=(0, 10), sticky="w"
        )

        self.connect_button = ctk.CTkButton(
            selected_frame,
            text="Connect",
            width=HMISizePos.sx(160),
            height=HMISizePos.sy(45),
            command=self.connect_wifi_threaded,
            **btn_style,
        )
        self.connect_button.grid(row=3, column=0, columnspan=2, padx=10, pady=15)

        self.network_list_frame = ctk.CTkScrollableFrame(
            body,
            label_text="Found Wi-Fi Networks",
            label_text_color=COLOR_BLUE,
            label_font=lbl_font,
            fg_color=COLOR_FG,
            border_width=2,
            border_color=COLOR_BLUE,
        )
        self.network_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.network_list_frame.grid_columnconfigure(0, weight=1)

        # ----- Footer: same light background and rounded bordered buttons -----
        bottom_frame = ctk.CTkFrame(self, fg_color=COLOR_FG)
        bottom_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.refresh_button = ctk.CTkButton(
            bottom_frame,
            text="Refresh Status",
            width=HMISizePos.sx(160),
            height=HMISizePos.BTN_HEIGHT,
            command=self.update_wifi_status_threaded,
            **btn_style,
        )
        self.refresh_button.pack(side="right", padx=10, pady=6)

        self.exit_button = ctk.CTkButton(
            bottom_frame,
            text="← Back" if self.controller else "Exit",
            width=HMISizePos.sx(160),
            height=HMISizePos.BTN_HEIGHT,
            command=self.exit_or_back,
            **btn_style,
        )
        self.exit_button.pack(side="left", padx=10, pady=6)

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
            self.disable_button.configure(state="disabled")

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def run_worker(self, worker_func):
        def wrapper():
            self.after(0, lambda: self.set_busy(True))
            try:
                worker_func()
            finally:
                self.after(0, lambda: self.set_busy(False))

        threading.Thread(target=wrapper, daemon=True).start()

    def update_wifi_status_threaded(self):
        def worker():
            result = self.wifi.get_status()
            enabled = self.wifi.is_wifi_enabled()

            self.after(
                0,
                lambda: self.enable_button.configure(
                    state="disabled" if enabled else "normal"
                )
            )

            self.after(
                0,
                lambda: self.disable_button.configure(
                    state="normal" if enabled else "disabled"
                )
            )

            self.after(
                0,
                lambda: self.show_result("Status", result)
            )

        self.run_worker(worker)

    def enable_wifi_threaded(self):
        def worker():
            self.after(0, lambda: self.set_status("Enabling Wi-Fi..."))
            result = self.wifi.enable_wifi()
            self.after(0, lambda: self.show_result("Enable", result))
            self.after(750, self.update_wifi_status_threaded)

        self.run_worker(worker)

    def disable_wifi_threaded(self):
        def worker():
            self.after(0, lambda: self.set_status("Disabling Wi-Fi..."))
            result = self.wifi.disable_wifi()
            self.after(0, lambda: self.show_result("Disable", result))
            self.after(750, self.update_wifi_status_threaded)

        self.run_worker(worker)

    

    def scan_wifi_threaded(self):
        def worker():
            self.after(0, lambda: self.set_status("Scanning Wi-Fi networks..."))
            result, networks = self.wifi.scan_networks()
            if result.ok:
                self.after(0, lambda: self.populate_network_list(networks))
                self.after(0, lambda: self.set_status(result.stdout))
            else:
                self.after(0, lambda: self.show_result("Scan", result))

        self.run_worker(worker)

    
    def connect_wifi_threaded(self):
        def worker():
            import time

            ssid = self.selected_ssid.get().strip()
            password = self.password_entry.get().strip()

            if not ssid:
                self.after(0, lambda: self.set_status("Select or enter an SSID first"))
                return

            self.after(0, lambda: self.set_status(f"Connecting to {ssid}..."))

            result = self.wifi.connect(ssid, password)

            print("CONNECT RESULT")
            print("ok:", result.ok)
            print("stdout:", result.stdout)
            print("stderr:", result.stderr)
            print("message:", result.message)

            if not result.ok:
                self.after(0, lambda r=result: self.show_result("Connect", r))
                return

            # IMPORTANT:
            # Do not trust result.ok alone.
            # Windows/netsh can say the connect request succeeded even if the password is wrong.
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
                self.after(0, lambda: self.set_status(f"Connected to {ssid}"))

                if self.controller and hasattr(self.controller, "show_SoftwareUpdatePage"):
                    self.after(1000, self.controller.show_SoftwareUpdatePage)
                else:
                    self.after(1000, self.show_software_update_page_standalone)
            else:
                self.after(
                    0,
                    lambda: self.set_status(
                        f"Failed to connect to {ssid}. Check the password."
                    ),
                )

        self.run_worker(worker)

    def show_software_update_page_standalone(self):
        for child in self.master.winfo_children():
            child.destroy()

        page = SoftwareUpdatePage(self.master)
        page.grid(row=0, column=0, sticky="nsew")


    def show_result(self, action: str, result: CommandResult):
        if result.ok:
            msg = result.message or "OK"
            self.set_status(f"{action}: {msg}")
        else:
            msg = result.message or "Unknown error"
            self.set_status(f"{action} Error: {msg}")

    def populate_network_list(self, networks: list[WifiNetwork]):
        for button in self.network_buttons:
            button.destroy()
        self.network_buttons.clear()

        if not networks:
            self.set_status("No Wi-Fi networks found")
            return

        for row, network in enumerate(networks):
            signal = f"{network.signal}%" if network.signal else ""
            security = network.security or "Open/Unknown"
            button_text = f"{network.ssid}    Signal: {signal}    Security: {security}"

            button = ctk.CTkButton(
                self.network_list_frame,
                text=button_text,
                anchor="w",
                height=HMISizePos.sy(40),
                command=lambda s=network.ssid: self.select_ssid(s),
                **self._button_style(),
            )
            button.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
            self.network_buttons.append(button)

    def select_ssid(self, ssid: str):
        self.selected_ssid.set(ssid)
        self.set_status(f"Selected: {ssid}")

    def toggle_password_visibility(self):
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def exit_or_back(self):
        if self.controller and hasattr(self.controller, "show_HomePage"):
            self.controller.show_HomePage()
        else:
            self.master.destroy()


class StandaloneWifiApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Wi-Fi Settings")
        self.geometry("900x600")
        self.minsize(800, 480)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        page = WifiSettingsPage(self)
        page.grid(row=0, column=0, sticky="nsew")


if __name__ == "__main__":
    app = StandaloneWifiApp()
    app.mainloop()
