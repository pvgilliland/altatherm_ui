import customtkinter as ctk
from hmi_consts import HMIColors, HMISizePos, SETTINGS_DIR
from ui_bits import COLOR_FG, COLOR_BLUE, StyledNumericInput
import json, os

SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.alt")


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def save_settings(minute: int, second: int) -> None:
    """
    Merge-only write: keep other fields (e.g., alarm_level) intact.
    Writes fan delay under data['fan_delay'] = {'minute':..., 'second':...}
    """
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    data = load_settings()
    data["fan_delay"] = {
        "minute": int(minute),
        "second": int(second),
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


class TimePage(ctk.CTkFrame):
    """Fan Delay page, responsive and consistent with shared widgets."""

    def __init__(self, controller, shared_data, **kwargs):
        super().__init__(controller, fg_color=COLOR_FG, **kwargs)
        self.controller = controller
        self.shared_data = shared_data
        self.build_ui()

    def build_ui(self):
        title_label = ctk.CTkLabel(
            self,
            text="Fan Delay Input",
            text_color=COLOR_BLUE,
            font=("Arial", 20, "bold"),
        )
        title_label.pack(fill="x", pady=HMISizePos.sy(6), anchor="n")

        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_FG,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BLUE,
        )
        self.main_frame.place(
            relx=0.5, rely=0.46, anchor="center", relwidth=0.72, relheight=0.62
        )
        self.main_frame.pack_propagate(False)

        time_label = ctk.CTkLabel(
            self.main_frame,
            text="Time",
            text_color=COLOR_BLUE,
            font=("Arial", 20, "bold"),
        )
        time_label.place(x=7, y=10)

        divider = ctk.CTkFrame(self.main_frame, height=2, fg_color=COLOR_BLUE)
        divider.place(relx=0.5, rely=0.15, relwidth=0.96, anchor="n")

        settings = load_settings()
        fd = settings.get("fan_delay", {})  # nested fan delay block

        tp = self.shared_data.setdefault("time_page", {})
        tp["minute"] = (
            tp.get("minute")
            if isinstance(tp.get("minute"), ctk.IntVar)
            else ctk.IntVar()
        )
        tp["second"] = (
            tp.get("second")
            if isinstance(tp.get("second"), ctk.IntVar)
            else ctk.IntVar()
        )

        # Use nested fan_delay defaults if absent
        tp["minute"].set(int(fd.get("minute", 1)))
        tp["second"].set(int(fd.get("second", 1)))

        self.minute_control = StyledNumericInput(
            self.main_frame, label="Minute", variable=tp["minute"]
        )
        self.second_control = StyledNumericInput(
            self.main_frame, label="Second", variable=tp["second"]
        )

        pad_x = 0.05
        ctrl_w = 0.42
        ctrl_h = 0.70
        y_top = 0.22
        self.minute_control.place(
            relx=pad_x, rely=y_top, relwidth=ctrl_w, relheight=ctrl_h, anchor="nw"
        )
        self.second_control.place(
            relx=1 - pad_x, rely=y_top, relwidth=ctrl_w, relheight=ctrl_h, anchor="ne"
        )

        font = ctk.CTkFont(family="Arial", size=18, weight="bold")
        back_button = ctk.CTkButton(
            self,
            text="← Back",
            font=font,
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
        back_button.place(relx=0.0, rely=1.0, x=27, y=-30, anchor="sw")

        accept_button = ctk.CTkButton(
            self,
            text="Accept",
            font=font,
            command=self.on_accept,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=20,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
        )
        accept_button.place(relx=1.0, rely=1.0, x=-27, y=-30, anchor="se")

    def on_accept(self):
        tp = self.shared_data["time_page"]
        save_settings(tp["minute"].get(), tp["second"].get())
        if self.controller:
            self.controller.show_HomePage()

    def on_back_pressed(self):
        self.restore_saved_settings()
        if self.controller:
            self.controller.show_HomePage()

    def restore_saved_settings(self):
        settings = load_settings()
        fd = settings.get("fan_delay", {})
        tp = self.shared_data.get("time_page", {})
        if "minute" in tp:
            tp["minute"].set(int(fd.get("minute", 1)))
        if "second" in tp:
            tp["second"].set(int(fd.get("second", 1)))

    def on_show(self):
        self.restore_saved_settings()
