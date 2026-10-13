import customtkinter as ctk
from hmi_consts import HMIColors, HMISizePos
from ui_bits import COLOR_FG, COLOR_BLUE, StyledNumericInput, compute_two_card_layout


class PhaseTimePowerPage(ctk.CTkFrame):
    """Responsive Phase/Time/Power editor reusing shared widgets and layout."""

    def __init__(self, controller, shared_data, title="Title", **kwargs):
        super().__init__(controller, fg_color=COLOR_FG, **kwargs)
        self.controller = controller
        self.shared_data = shared_data
        self.title = title
        self._build_ui()
        self.bind("<Configure>", self._relayout)
        self.after(0, self._relayout)

    def _build_ui(self):
        self.title_label = ctk.CTkLabel(
            self, text=self.title, text_color=COLOR_BLUE, font=("Arial", 20, "bold")
        )
        self.title_label.place(relx=0.5, rely=0.025, anchor="n")

        minute_var = self.shared_data.get("minute") or ctk.IntVar(value=1)
        second_var = self.shared_data.get("second") or ctk.IntVar(value=1)
        power_var = self.shared_data.get("power") or ctk.IntVar(value=1)
        (
            self.shared_data["minute"],
            self.shared_data["second"],
            self.shared_data["power"],
        ) = (minute_var, second_var, power_var)

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

        font = ctk.CTkFont(family="Arial", size=18, weight="bold")
        self.cancel_button = ctk.CTkButton(
            self,
            text="Cancel",
            font=font,
            command=self._return_to_sequence_page,
            fg_color=HMIColors.color_fg,
            text_color=HMIColors.color_blue,
            corner_radius=20,
            border_width=2,
            border_color=HMIColors.color_blue,
            hover_color=HMIColors.color_numbers,
            width=HMISizePos.sx(110),
            height=HMISizePos.BTN_HEIGHT,
        )
        self.cancel_button.place(relx=0.0, rely=1.0, x=27, y=-30, anchor="sw")

        self.accept_button = ctk.CTkButton(
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
        self.accept_button.place(relx=1.0, rely=1.0, x=-27, y=-30, anchor="se")

    def _relayout(self, _e=None):
        self.update_idletasks()
        W = max(1, self.winfo_width())
        H = max(1, self.winfo_height())
        geo = compute_two_card_layout(W, H)

        self.time_card.configure(width=geo["left_w"], height=geo["cards_h"])
        self.time_card.place(x=geo["x_left"], y=geo["top_y"])
        self.power_card.configure(width=geo["right_w"], height=geo["cards_h"])
        self.power_card.place(x=geo["x_right"], y=geo["top_y"])

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

    def _selected_sequence_page(self):
        """Resolve the editor that opened this phase, not always SequenceProgramPage."""
        if self.shared_data.get("phase_return_page") == "IOC":
            from IOCPage import IOCPage
            page_class = IOCPage
        else:
            from SequenceProgramPage import SequenceProgramPage
            page_class = SequenceProgramPage

        pages = getattr(self.controller, "pages", None)
        if pages is None:
            pages = getattr(self.controller, "admin_pages", {})
        return pages.get(page_class)

    def _return_to_sequence_page(self):
        """Preserve unsaved IOC edits while navigating back to its widget."""
        if self.shared_data.get("phase_return_page") == "IOC":
            self.shared_data["ioc_skip_program_refresh_once"] = True
        self.controller.back_to_SequenceProgramPage()

    def on_accept(self):
        minute = int(self.shared_data["minute"].get())
        second = int(self.shared_data["second"].get())
        power = int(self.shared_data["power"].get())

        row = self.shared_data.get("selected_row")
        col = self.shared_data.get("selected_col")
        if not isinstance(row, int) or not isinstance(col, int):
            self._return_to_sequence_page()
            return

        seq_page = self._selected_sequence_page()
        if seq_page is None:
            raise RuntimeError("Selected sequence editor is not registered")

        btn = seq_page.step_widgets[row - 1].dual_buttons[col]
        btn.set_values(power, minute, second)

        # Keep SequenceCollection consistent with the displayed buttons.
        seq_page.sync_to_model()
        self.shared_data["skip_program_refresh_once"] = True
        self._return_to_sequence_page()

    def set_title(self, title):
        self.load_from_selection()
        self.title = title
        self.title_label.configure(text=title)

    def load_from_selection(self):
        row = self.shared_data.get("selected_row")
        col = self.shared_data.get("selected_col")
        if not isinstance(row, int) or not isinstance(col, int):
            return

        seq_page = self._selected_sequence_page()
        if seq_page is None:
            return

        try:
            btn = seq_page.step_widgets[row - 1].dual_buttons[col]
        except (IndexError, AttributeError):
            return

        self.shared_data["power"].set(int(btn.power))
        self.shared_data["minute"].set(int(btn.min))
        self.shared_data["second"].set(int(btn.sec))
