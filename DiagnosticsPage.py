import time
import customtkinter as ctk
from typing import TYPE_CHECKING, Dict, Any, Optional
import json, os

# Same imports TimePowerPage uses for palette & sizing
from MessageBoxPage import showerror, showinfo
from SerialService import SerialService
from hmi_consts import HMIColors, HMISizePos, __version__, SETTINGS_DIR
from ui_bits import COLOR_FG, COLOR_BLUE, COLOR_NUMBERS
from LabeledIntInput import LabeledIntInput  # Alarm Level & Hysteresis (ints)
from LabeledFloatInput import LabeledFloatInput
from utilities import save_log_file  # Over Temp Power (float)
import logging
from utilities import load_use_sound_from_settings

if TYPE_CHECKING:
    from MultiPageController import MultiPageController

logger = logging.getLogger("DiagnosticsPage")


class DiagnosticsPage(ctk.CTkFrame):
    # RESOLUTION_BASED_VERT_PAD dictionary
    RESOLUTION_BASED_VERT_PAD = {
        "800x480": 5,
        "1024x600": 7,
        "1280x800": 9,
    }

    def __init__(
        self, controller: "MultiPageController", shared_data: Dict[str, Any], **kwargs
    ):
        # Match page background to TimePowerPage
        super().__init__(controller, fg_color=COLOR_FG, **kwargs)
        self.controller = controller
        self.shared_data = shared_data

        # Serial: use the shared SerialService owned by controller (no direct pyserial here)
        self.serial: Optional["SerialService"] = getattr(
            self.controller, "serial", None
        )
        # NOTE: Do NOT add the listener here. We only listen while this page is shown.
        # Cleanup safety: if the widget is destroyed while showing, drop the listener.
        self.bind("<Destroy>", lambda e: self._remove_serial_listener_safe())

        # Grid: header (fixed), body (expands), footer (fixed)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # ----- Header -----
        header = ctk.CTkFrame(self, fg_color=COLOR_FG)
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        ctk.CTkLabel(
            header,
            text="Diagnostics",
            text_color=COLOR_BLUE,
            font=("Arial", 20, "bold"),
        ).pack(pady=(4, 8))

        # Thin divider in blue to mirror card dividers
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

        # Fonts
        btn_font = ctk.CTkFont(family="Arial", size=18, weight="bold")
        lbl_font = ctk.CTkFont(family="Arial", size=20, weight="bold")

        # ----- Two-column container -----
        outer = ctk.CTkFrame(body, fg_color=COLOR_FG)
        outer.pack(fill="x", padx=10, pady=10)
        outer.grid_columnconfigure(0, weight=1)  # left stretches
        outer.grid_columnconfigure(1, weight=0)  # right fixed

        leftCol = ctk.CTkFrame(outer, fg_color=COLOR_FG)
        rightCol = ctk.CTkFrame(outer, fg_color=COLOR_FG)
        leftCol.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        rightCol.grid(row=0, column=1, sticky="nsew")

        # common spacing/colors
        VERTICAL_PAD = self.RESOLUTION_BASED_VERT_PAD.get(HMISizePos.SCREEN_RES, 7)
        LBL_COLOR = COLOR_BLUE
        VAL_COLOR = COLOR_NUMBERS

        # ---------------- LEFT COLUMN (labels/values) ----------------
        # Row 0: HMI Version
        lblHMIVer = ctk.CTkLabel(
            leftCol, font=lbl_font, text="HMI Version:", text_color=LBL_COLOR
        )
        lblHMIVer.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)
        lblHMIVal = ctk.CTkLabel(
            leftCol, font=lbl_font, text=__version__, text_color=VAL_COLOR
        )
        lblHMIVal.grid(row=0, column=1, sticky="w", padx=10, pady=VERTICAL_PAD)

        # Row 1: Firmware Version
        lblFirmwareVer = ctk.CTkLabel(
            leftCol, font=lbl_font, text="Firmware Version:", text_color=LBL_COLOR
        )
        lblFirmwareVer.grid(
            row=1, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD
        )
        self.lblFirmwareVal = ctk.CTkLabel(
            leftCol, font=lbl_font, text="Unknown", text_color=VAL_COLOR
        )
        self.lblFirmwareVal.grid(
            row=1, column=1, sticky="w", padx=10, pady=VERTICAL_PAD
        )

        # Row 2: Hardware Version
        lblBoardVer = ctk.CTkLabel(
            leftCol, font=lbl_font, text="Hardware Version:", text_color=LBL_COLOR
        )
        lblBoardVer.grid(row=2, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)
        self.lblBoardVal = ctk.CTkLabel(
            leftCol, font=lbl_font, text="Unknown", text_color=VAL_COLOR
        )
        self.lblBoardVal.grid(row=2, column=1, sticky="w", padx=10, pady=VERTICAL_PAD)

        # Row 3: Door Status
        lblDoorStatus = ctk.CTkLabel(
            leftCol, font=lbl_font, text="Door Status:", text_color=LBL_COLOR
        )
        lblDoorStatus.grid(row=3, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)
        self.lblDoorStatusVal = ctk.CTkLabel(
            leftCol, font=lbl_font, text="Unknown", text_color=VAL_COLOR
        )
        self.lblDoorStatusVal.grid(
            row=3, column=1, sticky="w", padx=10, pady=VERTICAL_PAD
        )

        # Row 4: Thermistors (left)
        lblThermistors = ctk.CTkLabel(
            leftCol, font=lbl_font, text="Thermistor Values:", text_color=LBL_COLOR
        )
        lblThermistors.grid(
            row=4, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD
        )
        self.lblThermistorsVals = ctk.CTkLabel(
            leftCol, font=lbl_font, text="xxxxxxx,yyyyyyy", text_color=VAL_COLOR
        )
        self.lblThermistorsVals.grid(
            row=4, column=1, sticky="w", padx=10, pady=VERTICAL_PAD
        )

        # Rows 5–8: IR sensors (left column)
        self.lblsIRValues = []
        for i in range(4):
            lblIRn = ctk.CTkLabel(
                leftCol,
                font=lbl_font,
                text=f"IR Sensor {i + 1} (°C):",
                text_color=LBL_COLOR,
            )
            lblIRn.grid(
                row=5 + i, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD
            )
            lblBoardValn = ctk.CTkLabel(
                leftCol, font=lbl_font, text="N/A", text_color=VAL_COLOR
            )
            lblBoardValn.grid(
                row=5 + i, column=1, sticky="w", padx=10, pady=VERTICAL_PAD
            )
            self.lblsIRValues.append(lblBoardValn)

        # ---------------- RIGHT COLUMN (controls) ----------------
        # Row 0: Fan radios
        lblFan = ctk.CTkLabel(
            rightCol, font=lbl_font, text="Fan:", text_color=LBL_COLOR
        )
        lblFan.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)

        radio_frame = ctk.CTkFrame(
            rightCol,
            fg_color="transparent",
            border_width=2,
            border_color=COLOR_BLUE,
            corner_radius=6,
        )
        radio_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=VERTICAL_PAD)

        # Row 1: Door Lock radios
        lblDoor = ctk.CTkLabel(
            rightCol, font=lbl_font, text="Door Lock:", text_color=LBL_COLOR
        )
        lblDoor.grid(row=1, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)

        door_lock_radio_frame = ctk.CTkFrame(
            rightCol,
            fg_color="transparent",
            border_width=2,
            border_color=COLOR_BLUE,
            corner_radius=6,
        )
        door_lock_radio_frame.grid(
            row=1, column=1, sticky="ew", padx=10, pady=VERTICAL_PAD
        )

        # Row 2: Alarm Level
        self.alarm_threshold_input = LabeledIntInput(
            rightCol,
            label="Alarm Level:         ",
            initial=999,  # on_show() will load saved value
            min_val=0,
            max_val=5000,
            step=1,
            big_step=100,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=80,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.alarm_threshold_input.grid(
            row=2, column=0, columnspan=2, sticky="w", padx=0, pady=VERTICAL_PAD
        )

        # Row 3: Alarm Hysteresis
        self.alarm_hysteresis_input = LabeledIntInput(
            rightCol,
            label="Alarm Hysteresis: ",
            initial=200,  # on_show() will load saved value
            min_val=100,
            max_val=1000,
            step=1,
            big_step=100,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=80,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.alarm_hysteresis_input.grid(
            row=3, column=0, columnspan=2, sticky="w", padx=0, pady=VERTICAL_PAD
        )

        # Row 4: Over Temp Power (FLOAT, one decimal place typical; using 0.01 steps here)
        self.over_temp_power_input = LabeledFloatInput(
            rightCol,
            label="Over Temp Power:",
            initial=0.75,  # default; on_show() will load saved value
            min_val=0.01,
            max_val=1.0,  # adjust as needed
            step=0.01,
            big_step=0.10,
            repeat_delay=400,
            repeat_interval=10,
            value_fs=32,
            btn_glyph_fs=32,
            value_width=80,
            label_font=lbl_font,
            label_padx=(10, 5),
        )
        self.over_temp_power_input.grid(
            row=4, column=0, columnspan=2, sticky="w", padx=0, pady=VERTICAL_PAD
        )

        # Row 5: Use Sound radios (Yes / No)
        lblUseSound = ctk.CTkLabel(
            rightCol, font=lbl_font, text="Use Sound:", text_color=LBL_COLOR
        )
        lblUseSound.grid(row=5, column=0, sticky="w", padx=(10, 5), pady=VERTICAL_PAD)

        use_sound_radio_frame = ctk.CTkFrame(
            rightCol,
            fg_color="transparent",
            border_width=2,
            border_color=COLOR_BLUE,
            corner_radius=6,
        )
        use_sound_radio_frame.grid(
            row=5, column=1, sticky="ew", padx=10, pady=VERTICAL_PAD
        )

        self.selected_use_sound_option = ctk.StringVar(value="Yes")

        radSoundYes = ctk.CTkRadioButton(
            use_sound_radio_frame,
            text="Yes",
            font=lbl_font,
            text_color=VAL_COLOR,
            border_color=VAL_COLOR,
            variable=self.selected_use_sound_option,
            value="Yes",
            command=self.on_use_sound_change,
        )
        radSoundYes.pack(side="left", padx=10, pady=VERTICAL_PAD)

        radSoundNo = ctk.CTkRadioButton(
            use_sound_radio_frame,
            text="No",
            font=lbl_font,
            text_color=VAL_COLOR,
            border_color=VAL_COLOR,
            variable=self.selected_use_sound_option,
            value="No",
            command=self.on_use_sound_change,
        )
        radSoundNo.pack(side="left", padx=10, pady=VERTICAL_PAD)

        # Row 6: Save Log button (moved down one row)
        save_log_btn = ctk.CTkButton(
            rightCol,
            text="Save Log",
            command=self.on_save_log,
            font=btn_font,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=20,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=HMISizePos.sx(50),
            height=50,
        )
        save_log_btn.grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            padx=0,
            pady=VERTICAL_PAD - VERTICAL_PAD,
        )

        # Control vars for radios
        self.selected_fan_option = ctk.StringVar(value="Off")
        self.selected_door_lock_option = ctk.StringVar(value="Unlocked")

        self.radFanOn = ctk.CTkRadioButton(
            radio_frame,
            text="On",
            font=lbl_font,
            text_color=VAL_COLOR,
            border_color=VAL_COLOR,
            variable=self.selected_fan_option,
            value="On",
            command=self.on_fan_change,
        )
        self.radFanOn.pack(side="left", padx=10, pady=VERTICAL_PAD)

        radFanOff = ctk.CTkRadioButton(
            radio_frame,
            text="Off",
            font=lbl_font,
            text_color=VAL_COLOR,
            border_color=VAL_COLOR,
            variable=self.selected_fan_option,
            value="Off",
            command=self.on_fan_change,
        )
        radFanOff.pack(side="left", padx=10, pady=VERTICAL_PAD)

        radDoorLocked = ctk.CTkRadioButton(
            door_lock_radio_frame,
            text="Locked",
            font=lbl_font,
            text_color=VAL_COLOR,
            border_color=VAL_COLOR,
            variable=self.selected_door_lock_option,
            value="Locked",
            command=self.on_lock_change,
        )
        radDoorLocked.pack(side="left", padx=10, pady=VERTICAL_PAD)

        radDoorUnlocked = ctk.CTkRadioButton(
            door_lock_radio_frame,
            text="Unlocked",
            font=lbl_font,
            text_color=VAL_COLOR,
            border_color=VAL_COLOR,
            variable=self.selected_door_lock_option,
            value="Unlocked",
            command=self.on_lock_change,
        )
        radDoorUnlocked.pack(side="left", padx=10, pady=VERTICAL_PAD)

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

    # --- settings helpers ---
    def _load_settings_dict(self) -> dict:
        """Load settings/settings.alt as JSON; always return a dict."""
        path = os.path.join(SETTINGS_DIR, "settings.alt")
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    def _load_alarm_level_from_settings(self, default: int = 1500) -> int:
        """Return alarm_level from settings; coerce to int; fall back safely."""
        data = self._load_settings_dict()
        try:
            return int(data.get("alarm_level", default))
        except Exception:
            return default

    def _load_alarm_hysteresis_from_settings(self, default: int = 200) -> int:
        """Return alarm_hysteresis from settings; coerce to int; fall back safely."""
        data = self._load_settings_dict()
        try:
            return int(data.get("alarm_hysteresis", default))
        except Exception:
            return default

    def _load_over_temp_power_from_settings(self, default: float = 0.75) -> float:
        """Return over_temp_power from settings; coerce to float; fall back safely."""
        data = self._load_settings_dict()
        try:
            return float(data.get("over_temp_power", default))
        except Exception:
            return default

    # ----- Actions -----
    def _send(self, cmd: str):
        try:
            if hasattr(self.controller, "serial_send"):
                self.controller.serial_send(cmd)
            else:
                print(
                    f"[DiagnosticsPage] serial_send not available. Would send: {cmd!r}"
                )
        except Exception as e:
            print(f"[DiagnosticsPage] Failed to send {cmd!r}: {e}")

    def on_back(self):
        # Merge-save: preserve other fields (fan_delay/etc.), only set diagnostics values
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            path = os.path.join(SETTINGS_DIR, "settings.alt")

            data = self._load_settings_dict()
            data["alarm_level"] = int(self.alarm_threshold_input.get())
            data["alarm_hysteresis"] = int(self.alarm_hysteresis_input.get())
            data["over_temp_power"] = float(self.over_temp_power_input.get())
            data["use_sound"] = self.selected_use_sound_option.get() == "Yes"

            with open(path, "w") as f:
                json.dump(data, f, indent=2)

            print(
                f"[DiagnosticsPage] Saved Alarm Level={data['alarm_level']}, "
                f"Alarm Hysteresis={data['alarm_hysteresis']}, "
                f"Over Temp Power={data['over_temp_power']}, "
                f"Use Sound={data['use_sound']} to {path}"
            )
        except Exception as e:
            print(f"[DiagnosticsPage] Failed to save settings: {e}")

        if hasattr(self.controller, "show_HomePage"):
            self.controller.show_HomePage()
        else:
            print("[DiagnosticsPage] Back pressed (no controller.show_HomePage)")

    def on_show(self):
        # Restore values from settings
        try:
            saved_alarm = self._load_alarm_level_from_settings(default=1500)
            self.alarm_threshold_input.set(saved_alarm)

            saved_hyst = self._load_alarm_hysteresis_from_settings(default=200)
            self.alarm_hysteresis_input.set(saved_hyst)

            saved_power = self._load_over_temp_power_from_settings(default=0.75)
            self.over_temp_power_input.set(saved_power)

            use_sound = load_use_sound_from_settings(default=True)
            self.selected_use_sound_option.set("Yes" if use_sound else "No")
            # Publish for global use (e.g., click wrappers)
            self.shared_data["use_sound"] = use_sound
            # Optional: notify controller if it exposes a setter
            if hasattr(self.controller, "set_use_sound"):
                try:
                    self.controller.set_use_sound(use_sound)
                except Exception:
                    pass
        except Exception as e:
            print(f"[DiagnosticsPage] Failed to restore settings: {e}")

        # Add serial listener when the page becomes visible
        if self.serial:
            try:
                self.serial.add_listener(self._on_serial_line)
            except Exception as e:
                print(f"[DiagnosticsPage] add_listener failed: {e}")

        self.on_refresh()

    def on_hide(self):
        # Remove serial listener when leaving the page
        self._remove_serial_listener_safe()

    def _remove_serial_listener_safe(self):
        try:
            if self.serial:
                self.serial.remove_listener(self._on_serial_line)
        except Exception:
            pass

    def on_refresh(self):
        SERIAL_DELAY = 0  # 0.05
        self.shared_data["diagnostics_last_saved"] = True
        print("[DiagnosticsPage] Refreshed")
        self.controller.serial_get_versions()
        time.sleep(SERIAL_DELAY)
        self.controller.serial_get_thermistor()
        time.sleep(SERIAL_DELAY)
        self.controller.serial_get_fan()
        time.sleep(SERIAL_DELAY)
        self.controller.serial_get_door_lock()
        time.sleep(SERIAL_DELAY)
        self.controller.serial_get_door_switch()
        for sendorId in range(1, 5):
            time.sleep(SERIAL_DELAY)
            self.controller.serial_get_IR_temp(sendorId)

    def on_save_log(self):
        ok, msg = save_log_file()
        if not ok and "E0001" in msg:
            showerror(self, "Error", "No thumb drive found!")
            return
        if not ok:
            showerror(self, "Error", msg)

        showinfo(self, "Information", msg)

    def on_fan_change(self):
        print("Selected:", self.selected_fan_option.get())
        val = self.selected_fan_option.get()  # "On" or "Off"
        self.controller.serial_fan(True if val == "On" else False)

    def on_lock_change(self):
        print("Selected:", self.selected_door_lock_option.get())
        val = self.selected_door_lock_option.get()  # "Locked" or "Unlocked"
        self.controller.serial_door_lock(True if val == "Locked" else False)

    def on_use_sound_change(self):
        val = self.selected_use_sound_option.get()  # "Yes" or "No"
        use_sound = val == "Yes"
        # Publish for global access; click wrappers can consult this.
        self.shared_data["use_sound"] = use_sound
        # Optional: notify controller if available
        if hasattr(self.controller, "set_use_sound"):
            try:
                self.controller.set_use_sound(use_sound)
            except Exception:
                pass
        print(f"[DiagnosticsPage] Use Sound set to {use_sound}")

    def _on_serial_line(self, line: str) -> None:
        # print("[DiagnosticsPage]: " + line)
        if line.startswith("I="):
            nums = line[2:]
            parts = nums.split(",")
            self.lblFirmwareVal.configure(text=parts[0])
            self.lblBoardVal.configure(text=parts[1])
            return

        if line.startswith("R="):
            nums = line[2:]
            self.lblThermistorsVals.configure(text=nums)
            return

        if line.startswith("T0"):
            return

        if line.startswith("T"):
            sensorNum = line[1]
            temps = line[3:]
            self.lblsIRValues[int(sensorNum) - 1].configure(text=temps)
            return

        if line.startswith("F="):
            status = line[2]
            self.selected_fan_option.set("On" if status == "1" else "Off")
            return

        # Door Lock
        if line.startswith("L="):
            status = line[2]
            self.selected_door_lock_option.set(
                "Locked" if status == "1" else "Unlocked"
            )
            return

        # Door Switch
        if line.startswith("D="):
            status = line[2]
            self.lblDoorStatusVal.configure(
                text=("Open" if status == "1" else "Closed")
            )
            return


# ---- Standalone test harness ----
if __name__ == "__main__":

    class DummyController(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("DiagnosticsPage Test")
            self.geometry("1024x600")
            self.shared_data = {}

        def serial_send(self, cmd):
            print(f"[DummyController] Sending: {cmd}")

        def show_HomePage(self):
            print("[DummyController] Going back to HomePage")

        # Stubs to avoid attribute errors in on_refresh()
        def serial_get_versions(self):
            print("[Dummy] get_versions")

        def serial_get_thermistor(self):
            print("[Dummy] get_thermistor")

        def serial_get_fan(self):
            print("[Dummy] get_fan")

        def serial_get_door_lock(self):
            print("[Dummy] get_door_lock")

        def serial_get_door_switch(self):
            print("[Dummy] get_door_switch")

        def serial_get_IR_temp(self, n):
            print(f"[Dummy] get_IR {n}")

        def set_use_sound(self, v: bool):
            print(f"[DummyController] set_use_sound({v})")

    app = DummyController()
    page = DiagnosticsPage(controller=app, shared_data=app.shared_data)
    page.pack(fill="both", expand=True)
    app.mainloop()
