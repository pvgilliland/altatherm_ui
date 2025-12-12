import customtkinter as ctk
from DoorSafety import DoorSafety
from hmi_consts import HMIColors, HMISizePos, SETTINGS_DIR
from ui_bits import COLOR_FG, COLOR_BLUE, StyledNumericInput, compute_two_card_layout
import logging, json, os

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.alt")


def _load_settings() -> dict:
    """Safe JSON loader for shared settings file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def _save_manual_cook(minute: int, second: int, power: int) -> None:
    """
    Merge-only write to settings.alt.
    Writes under:
      data['manual_cook'] = {'minute':..., 'second':..., 'power':...}
    Keeps other keys (like 'fan_delay') intact.
    """
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    data = _load_settings()
    data["manual_cook"] = {
        "minute": int(minute),
        "second": int(second),
        "power": int(power),
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


class TimePowerPage(ctk.CTkFrame):
    """Manual Input page with proportional two-card layout and persisted settings."""

    def __init__(self, controller, shared_data, **kwargs):
        super().__init__(controller, fg_color=COLOR_FG, **kwargs)
        self.controller = controller
        self.shared_data = shared_data
        self._build_ui()

    def _build_ui(self):
        self.title_label = ctk.CTkLabel(
            self, text="Manual Input", text_color=COLOR_BLUE, font=("Arial", 20, "bold")
        )
        self.title_label.place(relx=0.5, rely=0.025, anchor="n")

        # --- Load saved settings (if any) ---
        settings = _load_settings()
        mc = settings.get(
            "manual_cook", {}
        )  # {'minute':..., 'second':..., 'power':...}

        tpw = self.shared_data.setdefault("time_power_page", {})
        minute_var = (
            tpw.get("minute")
            if isinstance(tpw.get("minute"), ctk.IntVar)
            else ctk.IntVar()
        )
        second_var = (
            tpw.get("second")
            if isinstance(tpw.get("second"), ctk.IntVar)
            else ctk.IntVar()
        )
        power_var = (
            tpw.get("power")
            if isinstance(tpw.get("power"), ctk.IntVar)
            else ctk.IntVar()
        )

        # Defaults fall back to prior behavior if not saved yet
        minute_var.set(int(mc.get("minute", 0)))
        second_var.set(int(mc.get("second", 10)))
        power_var.set(int(mc.get("power", 50)))

        tpw["minute"], tpw["second"], tpw["power"] = minute_var, second_var, power_var

        self.time_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_FG,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BLUE,
            width=1,
            height=1,
        )
        self.power_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_FG,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BLUE,
            width=1,
            height=1,
        )

        self.time_header = ctk.CTkLabel(
            self.time_card,
            text="Time",
            text_color=COLOR_BLUE,
            font=("Arial", 20, "bold"),
        )
        self.power_header = ctk.CTkLabel(
            self.power_card,
            text="Power",
            text_color=COLOR_BLUE,
            font=("Arial", 20, "bold"),
        )
        self.time_div = ctk.CTkFrame(
            self.time_card, height=2, fg_color=COLOR_BLUE, width=1
        )
        self.power_div = ctk.CTkFrame(
            self.power_card, height=2, fg_color=COLOR_BLUE, width=1
        )

        self.minute_control = StyledNumericInput(
            self.time_card, label="Minute", variable=minute_var
        )
        self.second_control = StyledNumericInput(
            self.time_card, label="Second", variable=second_var
        )
        self.power_control = StyledNumericInput(
            self.power_card, label="Level", variable=power_var
        )

        btn_font = ctk.CTkFont(family="Arial", size=18, weight="bold")
        self.back_button = ctk.CTkButton(
            self,
            text="← Back",
            font=btn_font,
            command=self.on_back_pressed,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=20,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
        )
        self.back_button.place(relx=0.0, rely=1.0, x=27, y=-30, anchor="sw")

        self.run_button_font = ctk.CTkFont(
            family="Arial", size=18, weight="bold", overstrike=0
        )
        self.run_button = ctk.CTkButton(
            self,
            text="Run",
            font=self.run_button_font,
            command=self.on_run,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=20,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
        )
        self.run_button.place(relx=1.0, rely=1.0, x=-27, y=-30, anchor="se")

        self.bind("<Configure>", self._relayout)
        self.after(0, self._relayout)

        DoorSafety.Instance().add_listener(self.on_door_change)

    def on_door_change(self, is_open: bool):
        print(f"[TimePowerPage.on_door_change] Door Open = {is_open}")
        btnState = "disabled" if is_open else "normal"
        btnColorBorder = (
            HMIColors.DISABLED_BORDER_COLOR if is_open else HMIColors.color_blue
        )
        btnText = "Run\n(door open)" if is_open else "Run"
        self.run_button_font.configure(overstrike=is_open)
        self.run_button.configure(
            state=btnState, border_color=btnColorBorder, text=btnText
        )

    def _relayout(self, _e=None):
        self.update_idletasks()
        W = max(1, self.winfo_width())
        H = max(1, self.winfo_height())
        geo = compute_two_card_layout(W, H)

        # CTk-safe sizing + placement
        self.time_card.configure(width=geo["left_w"], height=geo["cards_h"])
        self.time_card.place(x=geo["x_left"], y=geo["top_y"])
        self.power_card.configure(width=geo["right_w"], height=geo["cards_h"])
        self.power_card.place(x=geo["x_right"], y=geo["top_y"])

        # internals
        self.time_header.place(x=7, y=geo["header_y"])
        self.time_div.configure(width=geo["left_w"] - 14)
        self.time_div.place(x=7, y=geo["divider_y"])

        self.minute_control.configure(width=geo["tc_w"], height=geo["inner_h"])
        self.minute_control.place(x=7, y=geo["inner_top"])

        self.second_control.configure(width=geo["tc_w"], height=geo["inner_h"])
        self.second_control.place(x=7 + geo["tc_w"] + geo["tc_gap"], y=geo["inner_top"])

        self.power_header.place(x=7, y=geo["header_y"])
        self.power_div.configure(width=geo["right_w"] - 14)
        self.power_div.place(x=7, y=geo["divider_y"])

        self.power_control.configure(width=geo["right_w"] - 14, height=geo["inner_h"])
        self.power_control.place(x=7, y=geo["inner_top"])

    # --- Persistence helpers -------------------------------------------------

    def persist_current_settings(self):
        """Write current Minute/Second/Power to settings.alt -> manual_cook{}."""
        tpw = self.shared_data.get("time_power_page", {})
        minute = int(tpw["minute"].get()) if "minute" in tpw else 0
        second = int(tpw["second"].get()) if "second" in tpw else 0
        power = int(tpw["power"].get()) if "power" in tpw else 50
        _save_manual_cook(minute, second, power)
        logger.info(
            "Saved manual cook settings: %s m, %s s, power %s", minute, second, power
        )

    def restore_saved_settings(self):
        """Load saved values (if present) into the IntVars."""
        tpw = self.shared_data.get("time_power_page", {})
        data = _load_settings().get("manual_cook", {})
        if "minute" in tpw:
            tpw["minute"].set(int(data.get("minute", tpw["minute"].get())))
        if "second" in tpw:
            tpw["second"].set(int(data.get("second", tpw["second"].get())))
        if "power" in tpw:
            tpw["power"].set(int(data.get("power", tpw["power"].get())))

    # Optional: controller can call this when page is shown
    def on_show(self):
        self.restore_saved_settings()

    # --- Button handlers -----------------------------------------------------

    def on_back_pressed(self):
        # Persist, persist_current_settings, save settings even if we didn't
        # run with them so there is no confussion when and if params are saved.
        # They are always saved.
        self.persist_current_settings()
        if self.controller:
            self.controller.show_HomePage()

    def on_run(self):
        # Persist first, then execute the run
        self.persist_current_settings()

        tpw = self.shared_data["time_power_page"]
        minute = int(tpw["minute"].get())
        second = int(tpw["second"].get())
        power = int(tpw["power"].get())
        total_seconds = max(0, minute * 60 + second)

        logger.info("Manual Cook Cycle Started")
        # 1) Turn everything on at the requested power right away.
        try:
            self.controller.serial_all_zones(power)
        except Exception as e:
            print(f"[TimePowerPage] serial_all_zones({power}) failed: {e}")

        # 2) Show the CircularProgressPage and ensure we turn things OFF when it ends (or STOP is pressed).
        self.controller.show_CircularProgressPage(
            total_seconds,
            on_stop=lambda: self.controller.serial_all_zones_off(),
            isManualCookMode=True,
            time_power_page=self,
            powerLevel=power,
        )

    def set_power_to_percent_of_set_value(self, percent: float):
        try:
            tpw = self.shared_data["time_power_page"]
            power = int(tpw["power"].get() * percent)
            # 1) Turn everything on at the requested power right away.
            try:
                self.controller.serial_all_zones(power)
            except Exception as e:
                print(f"[TimePowerPage] serial_all_zones({power}) failed: {e}")
        except Exception as e:
            print(
                f"[TimePowerPage] set_power_to_percent_of_set_value({percent}) failed: {e}"
            )
