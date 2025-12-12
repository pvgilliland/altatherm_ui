"""
LabeledFloatInput — reusable float spinner control for CustomTkinter (CTk)

Same layout/behavior as LabeledIntInput, but uses floats
and displays value to 2 decimal place.

Features
- Float value with min/max, step, big_step
- Single click and press-and-hold auto-repeat on − / +
- Responsive sizing like LabeledIntInput
- Optional on_change callback fired after each value update

Per-instance styling options same as LabeledIntInput.
"""

from __future__ import annotations
import customtkinter as ctk
from typing import Callable, Optional, Any, Union, Tuple

from ui_bits import COLOR_FG, COLOR_BLUE, COLOR_NUMBERS, HoldCircularButton
from hmi_consts import HMISizePos


class _GlyphHoldButton(HoldCircularButton):
    def __init__(self, *args, glyph_fs: int | None = None, **kwargs):
        self._glyph_fs_override = glyph_fs
        super().__init__(*args, **kwargs)

    def set_size(self, size: int):
        super().set_size(size)
        if getattr(self, "_glyph_fs_override", None):
            try:
                fs = int(self._glyph_fs_override)
                self.itemconfig(self._label, font=("Arial", fs))
            except Exception:
                pass


class LabeledFloatInput(ctk.CTkFrame):
    RES_VALUE_FS = {
        "800x480": 72,
        "1024x600": 90,
        "1280x800": 120,
    }
    RES_BTN_SIZE = {
        "800x480": 45,
        "1024x600": 65,
        "1280x800": 92,
    }

    def __init__(
        self,
        master,
        *,
        label: str = "Label:",
        initial: float = 0.0,
        min_val: float = 0.0,
        max_val: float = 9999.9,
        step: float = 0.1,
        big_step: float = 1.0,
        repeat_delay: int = 400,
        repeat_interval: int = 100,
        on_change: Optional[Callable[[float], None]] = None,
        value_fs: int | None = None,
        value_width: int | None = None,
        btn_target: int | None = None,
        btn_glyph_fs: int | None = None,
        buttons_bg: str | None = None,
        label_font: Any | None = None,
        label_padx: Union[int, Tuple[int, int], None] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color=COLOR_FG, corner_radius=0, **kwargs)

        self._min = float(min_val)
        self._max = float(max_val)
        self._step = float(step)
        self._big_step = float(big_step)
        self._on_change = on_change
        self._label_padx = label_padx if label_padx is not None else (4, 8)

        self._value_fs_override = int(value_fs) if value_fs is not None else None
        self._value_width_override = (
            int(value_width) if value_width is not None else None
        )
        self._btn_target_override = int(btn_target) if btn_target is not None else None
        self._btn_glyph_fs_override = (
            int(btn_glyph_fs) if btn_glyph_fs is not None else None
        )
        self._buttons_bg = buttons_bg

        self.value = ctk.DoubleVar(value=float(initial))
        self.value.trace_add("write", lambda *_: self._notify_change())

        # Layout
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=0)

        self.lbl = ctk.CTkLabel(
            self,
            text=label,
            text_color=COLOR_BLUE,
            font=(label_font or ("Arial", HMISizePos.s(18), "bold")),
        )
        self.lbl.grid(row=0, column=0, sticky="w", padx=self._label_padx)

        self.btn_minus = _GlyphHoldButton(
            self,
            text="–",
            command=self._dec,
            repeat_delay=repeat_delay,
            repeat_interval=repeat_interval,
            glyph_fs=self._btn_glyph_fs_override,
        )
        self.btn_minus.grid(row=0, column=1, padx=(0, 8), pady=2, sticky="w")

        self.value_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=12,
            border_width=2,
            border_color=COLOR_BLUE,
        )
        self.value_frame.grid(row=0, column=2, sticky="we", padx=(0, 8))
        self.value_frame.grid_columnconfigure(0, weight=1)

        self.value_label = ctk.CTkLabel(
            self.value_frame,
            text=self._format(self.value.get()),
            font=("Arial", self._value_fs(), "bold"),
            text_color=COLOR_NUMBERS,
            bg_color="transparent",
            anchor="center",
            width=self._value_width(),
        )
        self.value_label.grid(row=0, column=0, sticky="we", padx=12, pady=6)
        self._apply_value_width_constraints()

        self.btn_plus = _GlyphHoldButton(
            self,
            text="+",
            command=self._inc,
            repeat_delay=repeat_delay,
            repeat_interval=repeat_interval,
            glyph_fs=self._btn_glyph_fs_override,
        )
        self.btn_plus.grid(row=0, column=3, padx=(0, 4), pady=2, sticky="e")

        # Update display when variable changes
        self.value.trace_add("write", self._update_label)

        bg_match = (
            self._buttons_bg if self._buttons_bg is not None else self.cget("fg_color")
        )
        try:
            self.btn_minus.configure(bg=bg_match)
            self.btn_plus.configure(bg=bg_match)
        except Exception:
            pass

        self.bind("<Configure>", self._on_resize)
        self.after(0, self._on_resize)

        for w in (
            self,
            self.value_frame,
            self.value_label,
            self.btn_plus,
            self.btn_minus,
        ):
            w.bind("<Button-1>", lambda e: self.focus_set(), add="+")

        self.bind("<Key-Up>", lambda e: self._inc())
        self.bind("<Key-Down>", lambda e: self._dec())
        self.bind("<Prior>", lambda e: self._inc(big=True))
        self.bind("<Next>", lambda e: self._dec(big=True))

    # ----- Public API -----
    def get(self) -> float:
        return float(self.value.get())

    def set(self, v: float) -> None:
        self.value.set(self._clamp(float(v)))

    def configure_range(
        self, *, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> None:
        if min_val is not None:
            self._min = float(min_val)
        if max_val is not None:
            self._max = float(max_val)
        self.set(self.get())

    # ----- Internal helpers -----
    def _format(self, v: float) -> str:
        return f"{v:.2f}"

    def _update_label(self, *_):
        try:
            self.value_label.configure(text=self._format(self.value.get()))
        except Exception:
            pass

    def _clamp(self, v: float) -> float:
        return max(self._min, min(self._max, v))

    def _notify_change(self) -> None:
        if self._on_change:
            try:
                self._on_change(float(self.value.get()))
            except Exception as e:
                print(f"[LabeledFloatInput] on_change error: {e}")

    def _inc(self, big: bool = False) -> None:
        step = self._big_step if big else self._step
        self.set(self.get() + step)

    def _dec(self, big: bool = False) -> None:
        step = self._big_step if big else self._step
        self.set(self.get() - step)

    def _value_fs(self) -> int:
        if self._value_fs_override is not None:
            return int(self._value_fs_override)
        return self.RES_VALUE_FS.get(HMISizePos.SCREEN_RES, HMISizePos.s(96))

    def _value_width(self) -> int:
        return int(self._value_width_override or 0)

    def _apply_value_width_constraints(self) -> None:
        try:
            if self._value_width_override:
                self.value_frame.grid_columnconfigure(
                    0, minsize=self._value_width_override
                )
                self.value_label.configure(width=self._value_width_override)
            else:
                self.value_frame.grid_columnconfigure(0, minsize=0)
                self.value_label.configure(width=0)
        except Exception:
            pass

    def _btn_target(self) -> int:
        if self._btn_target_override is not None:
            return int(self._btn_target_override)
        return self.RES_BTN_SIZE.get(HMISizePos.SCREEN_RES, HMISizePos.s(80))

    def _on_resize(self, _e=None):
        self.value_label.configure(font=("Arial", self._value_fs(), "bold"))
        self._apply_value_width_constraints()

        h = max(1, self.winfo_height())
        cap = int(h * 0.75)
        btn_size = max(40, min(self._btn_target(), cap))

        try:
            self.btn_plus.set_size(btn_size)
            self.btn_minus.set_size(btn_size)
        except Exception:
            pass


if __name__ == "__main__":
    import customtkinter as ctk

    ctk.set_appearance_mode("light")

    app = ctk.CTk()
    app.geometry("600x200")
    app.title("LabeledFloatInput Demo")

    w = LabeledFloatInput(
        app,
        label="Over Temp Power:",
        initial=5.0,
        min_val=0.0,
        max_val=10.0,
        step=0.1,
        big_step=1.0,
        value_fs=48,
        value_width=120,
    )
    w.pack(padx=20, pady=20)

    app.bind("<Escape>", lambda e: app.destroy())
    app.mainloop()
