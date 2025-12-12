"""
LabeledIntInput — reusable integer spinner control for CustomTkinter (CTk)

Layout (left → right):
  [label]  [− HoldCircularButton]  [ value in framed box ]  [+ HoldCircularButton]

Features
- Integer value with min/max, step, big_step
- Single click and press‑and‑hold auto‑repeat on − / + (uses HoldCircularButton)
- Responsive sizing: button size and value font adapt to screen profile
- Optional on_change callback fired after each value update

Per‑instance styling (does NOT affect other users of HoldCircularButton)
- value_fs: override **value label** font size (px)
- btn_target: override **button size** (px)
- btn_glyph_fs: override **± glyph** font size (px)
- buttons_bg: set the button canvas background for this control only
- value_width: set **value label width** (px) to keep columns aligned

Requirements
- ui_bits.py must provide: COLOR_FG, COLOR_BLUE, COLOR_NUMBERS, HoldCircularButton
- hmi_consts.HMISizePos must provide: SCREEN_RES and s()/sx()/sy() helpers

Example
-------
from LabeledIntInput import LabeledIntInput

spinner = LabeledIntInput(
    parent,
    label="Alarm Level:",
    min_val=0,
    max_val=5000,
    step=1,
    big_step=100,
    repeat_delay=400,
    repeat_interval=100,
    initial=1500,
    value_fs=48,          # value label font size
    value_width=140,      # value label width (px)
    btn_target=56,        # button diameter
    btn_glyph_fs=44,      # ± glyph font size
    buttons_bg="transparent",
    on_change=lambda v: print("value:", v),
)
spinner.grid(row=0, column=0, sticky="w", padx=8, pady=8)

val = spinner.get()   # int
spinner.set(1234)     # clamps to min/max
"""

from __future__ import annotations
import customtkinter as ctk
from typing import Callable, Optional, Any, Union, Tuple  # add Any, Union, Tuple

from ui_bits import COLOR_FG, COLOR_BLUE, COLOR_NUMBERS, HoldCircularButton
from hmi_consts import HMISizePos


# Local subclass to allow per-instance glyph font override without modifying the
# shared HoldCircularButton used elsewhere in the app.
class _GlyphHoldButton(HoldCircularButton):
    def __init__(self, *args, glyph_fs: int | None = None, **kwargs):
        self._glyph_fs_override = glyph_fs
        super().__init__(*args, **kwargs)

    def set_size(self, size: int):
        # call normal sizing (this redraws the canvas and sets default glyph size)
        super().set_size(size)
        # then apply our per-instance glyph font override if requested
        if getattr(self, "_glyph_fs_override", None):
            try:
                fs = int(self._glyph_fs_override)
                # _label is the canvas text item id created in CircularButton
                self.itemconfig(self._label, font=("Arial", fs))
            except Exception:
                pass


class LabeledIntInput(ctk.CTkFrame):
    # Per-resolution value font sizes (kept in sync with StyledNumericInput)
    RES_VALUE_FS = {
        "800x480": 72,
        "1024x600": 90,
        "1280x800": 120,
    }
    # Per-resolution circular button target sizes
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
        initial: int = 0,
        min_val: int = 0,
        max_val: int = 999999,
        step: int = 1,
        big_step: int = 10,
        repeat_delay: int = 400,
        repeat_interval: int = 100,
        on_change: Optional[Callable[[int], None]] = None,
        # per-instance style overrides
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

        self._min = int(min_val)
        self._max = int(max_val)
        self._step = int(step)
        self._big_step = int(big_step)
        self._on_change = on_change
        self._label_padx = (
            label_padx if label_padx is not None else (4, 8)
        )  # default matches old behavior

        # style overrides
        self._value_fs_override = int(value_fs) if value_fs is not None else None
        self._value_width_override = (
            int(value_width) if value_width is not None else None
        )
        self._btn_target_override = int(btn_target) if btn_target is not None else None
        self._btn_glyph_fs_override = (
            int(btn_glyph_fs) if btn_glyph_fs is not None else None
        )
        self._buttons_bg = buttons_bg

        self.value = ctk.IntVar(value=int(initial))
        self.value.trace_add("write", lambda *_: self._notify_change())

        # Grid: [label][ - ][ value_frame ][ + ]
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
            textvariable=self.value,
            font=("Arial", self._value_fs(), "bold"),
            text_color=COLOR_NUMBERS,
            bg_color="transparent",
            anchor="center",
            width=self._value_width(),  # explicit width if provided
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

        # Button canvas backgrounds (per-instance)
        bg_match = (
            self._buttons_bg if self._buttons_bg is not None else self.cget("fg_color")
        )
        try:
            self.btn_minus.configure(bg=bg_match)
            self.btn_plus.configure(bg=bg_match)
        except Exception:
            pass

        # Resize responsiveness
        self.bind("<Configure>", self._on_resize)
        self.after(0, self._on_resize)

        # Optional keyboard shortcuts (control-local). CTk forbids bind_all.
        # Click anywhere on the control to focus it; then arrows/PageUp/PageDown work.
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
        self.bind("<Prior>", lambda e: self._inc(big=True))  # PageUp
        self.bind("<Next>", lambda e: self._dec(big=True))  # PageDown

    # ----- Public API -----
    def get(self) -> int:
        return int(self.value.get())

    def set(self, v: int) -> None:
        self.value.set(self._clamp(int(v)))

    def configure_range(
        self, *, min_val: Optional[int] = None, max_val: Optional[int] = None
    ) -> None:
        if min_val is not None:
            self._min = int(min_val)
        if max_val is not None:
            self._max = int(max_val)
        self.set(self.get())  # re-clamp current value

    # ----- Internal helpers -----
    def _clamp(self, v: int) -> int:
        return max(self._min, min(self._max, v))

    def _notify_change(self) -> None:
        if self._on_change:
            try:
                self._on_change(int(self.value.get()))
            except Exception as e:
                print(f"[LabeledIntInput] on_change error: {e}")

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
        # Ensure grid has at least this width so row height doesn’t compress label
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
        # Scale value font by screen profile/override
        self.value_label.configure(font=("Arial", self._value_fs(), "bold"))
        # Re-apply width constraints on resize (in case parent layout changed)
        self._apply_value_width_constraints()

        # Compute a practical cap based on the height of this control
        h = max(1, self.winfo_height())
        cap = int(h * 0.75)  # leave margins
        btn_size = max(40, min(self._btn_target(), cap))

        # Buttons: set_size triggers our glyph override application
        try:
            self.btn_plus.set_size(btn_size)
            self.btn_minus.set_size(btn_size)
        except Exception:
            pass


if __name__ == "__main__":
    # Simple self-test / demo harness for the LabeledIntInput control
    import customtkinter as ctk

    def make_row(parent, **kwargs):
        w = LabeledIntInput(parent, **kwargs)
        w.grid(sticky="w", padx=16, pady=12)
        return w

    ctk.set_appearance_mode("light")
    app = ctk.CTk()
    app.title("LabeledIntInput Demo")
    app.geometry("1100x320")

    frm = ctk.CTkFrame(app, fg_color="#DAFAFF")
    frm.pack(fill="both", expand=True)
    frm.grid_columnconfigure(0, weight=1)

    make_row(
        frm,
        label="Alarm Level:",
        initial=45,
        min_val=0,
        max_val=5000,
        step=1,
        big_step=100,
        value_fs=48,
        value_width=140,
        btn_target=56,
        btn_glyph_fs=44,
        buttons_bg="transparent",
        on_change=lambda v: print("[Alarm]", v),
    )

    make_row(
        frm,
        label="Fan Delay (ms):",
        initial=2500,
        min_val=0,
        max_val=10000,
        step=50,
        big_step=250,
        value_width=180,
        on_change=lambda v: print("[Fan Delay]", v),
    )

    make_row(
        frm,
        label="Power Level:",
        initial=50,
        min_val=0,
        max_val=100,
        step=1,
        big_step=10,
        on_change=lambda v: print("[Power]", v),
    )

    # Quality-of-life: ESC to quit
    app.bind("<Escape>", lambda e: app.destroy())
    app.mainloop()
