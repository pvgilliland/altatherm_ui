import tkinter as tk
from typing import Optional, Callable
import customtkinter as ctk


class TimeAdjustControl(ctk.CTkFrame):
    """
    Horizontal +/- time adjust control, 15 sec step, e.g.:

        Reheat Time:   [ - ]   30 sec   [ + ]

    Designed to overlay inside ImageHotspotView.
    """

    def __init__(
        self,
        master,
        label_text: str = "Reheat Time:",
        step_seconds: int = 15,
        min_seconds: int = 0,
        max_seconds: int = 120,
        initial_seconds: int = 30,
        on_change: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._step = step_seconds
        self._min = min_seconds
        self._max = max_seconds
        self._seconds = max(self._min, min(self._max, initial_seconds))
        self._on_change = on_change

        # Layout: label | minus | value | plus
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=0)

        # Colors that match your bronze/gold theme
        gold = "#B08D57"
        text_white = "#FFFFFF"

        label_font = ctk.CTkFont(family="Poppins", size=28, weight="normal")
        value_font = ctk.CTkFont(family="Poppins", size=28, weight="normal")
        btn_font = ctk.CTkFont(family="Poppins", size=32, weight="bold")

        self.desc_label = ctk.CTkLabel(
            self,
            text=label_text,
            text_color=text_white,
            font=label_font,
        )
        self.desc_label.grid(row=0, column=0, padx=(0, 16), pady=10, sticky="e")

        self.minus_btn = ctk.CTkButton(
            self,
            text="-",
            width=70,
            height=70,
            corner_radius=35,
            fg_color="black",  # same as background to make a ring
            border_width=3,
            border_color=gold,
            hover_color="#1f1f1f",
            text_color=gold,
            font=btn_font,
            command=lambda: self._adjust(-self._step),
        )
        self.minus_btn.grid(row=0, column=1, padx=(0, 16), pady=10)

        self.value_label = ctk.CTkLabel(
            self,
            text=self._format_value(),
            text_color=text_white,
            font=value_font,
        )
        self.value_label.grid(row=0, column=2, padx=(0, 16), pady=10)

        self.plus_btn = ctk.CTkButton(
            self,
            text="+",
            width=70,
            height=70,
            corner_radius=35,
            fg_color="black",
            border_width=3,
            border_color=gold,
            hover_color="#1f1f1f",
            text_color=gold,
            font=btn_font,
            command=lambda: self._adjust(+self._step),
        )
        self.plus_btn.grid(row=0, column=3, padx=(0, 0), pady=10)

    # --------------------- internal helpers ---------------------
    def _format_value(self) -> str:
        # Simple "XX sec" style to match the mockup
        return f"{self._seconds} sec"

    def _adjust(self, delta: int) -> None:
        new_val = max(self._min, min(self._max, self._seconds + delta))
        if new_val == self._seconds:
            return
        self._seconds = new_val
        self.value_label.configure(text=self._format_value())
        if self._on_change:
            self._on_change(self._seconds)

    # --------------------- public API ---------------------------
    def get_seconds(self) -> int:
        return self._seconds

    def set_seconds(self, seconds: int) -> None:
        self._seconds = max(self._min, min(self._max, seconds))
        self.value_label.configure(text=self._format_value())
        if self._on_change:
            self._on_change(self._seconds)

    def configure_range(
        self,
        *,
        min_seconds: Optional[int] = None,
        max_seconds: Optional[int] = None,
        step_seconds: Optional[int] = None,
    ) -> None:
        if min_seconds is not None:
            self._min = min_seconds
        if max_seconds is not None:
            self._max = max_seconds
        if step_seconds is not None:
            self._step = step_seconds
        # Clamp current value
        self.set_seconds(self._seconds)
