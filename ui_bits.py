# ui_bits.py — shared colors, widgets, and layout helpers
import customtkinter as ctk
from hmi_consts import HMISizePos

# ---- Colors (kept consistent across pages) ----
COLOR_NUMBERS = "#3776C3"
COLOR_BLUE = "#89C8F8"
COLOR_FG = "#DAFAFF"


# ---- Reusable circular +/- button ----
class CircularButton(ctk.CTkCanvas):
    """Circular +/- button with scalable glyph that stays optically centered."""

    def __init__(
        self,
        master,
        text,
        command=None,
        fg_color=COLOR_NUMBERS,
        highlight_color="#ccccff",
        size=50,
        **kwargs,
    ):
        self._size = size
        super().__init__(
            master,
            width=size,
            height=size,
            bg=COLOR_BLUE,
            highlightthickness=0,
            **kwargs,
        )
        self.command = command
        self.fg_color = fg_color
        self.highlight_color = highlight_color
        self._text = text  # '+' or '–'
        self._circle = None
        self._label = None
        self._draw()
        # Default single-click behavior (one-shot)
        self.bind("<Button-1>", self._on_press)

    def _draw(self):
        self.delete("all")
        s = self._size
        pad = max(3, int(s * 0.06))
        lw = max(2, int(s * 0.06))
        self._circle = self.create_oval(
            pad, pad, s - pad, s - pad, outline=self.fg_color, width=lw
        )
        # tiny optical nudge keeps "+" centered visually vs "–"
        y = int(s * (0.53 if self._text == "+" else 0.42))
        fs = max(18, int(s * 0.80))  # glyph ≈ 80% of button size
        self._label = self.create_text(
            s // 2, y, text=self._text, font=("Arial", fs), fill=self.fg_color
        )

    def set_size(self, size: int):
        if size != self._size:
            self._size = size
            self.configure(width=size, height=size)
            self._draw()

    def _on_press(self, _e=None):
        self._highlight()
        if self.command:
            self.command()

    def _highlight(self):
        self.itemconfig(self._circle, outline=self.highlight_color)
        self.itemconfig(self._label, fill=self.highlight_color)
        self.after(
            150,
            lambda: (
                self.itemconfig(self._circle, outline=self.fg_color),
                self.itemconfig(self._label, fill=self.fg_color),
            ),
        )


# ---- Press-and-hold variant: triggers once immediately, then auto-repeats while held ----
class HoldCircularButton(CircularButton):
    def __init__(
        self,
        master,
        text,
        command=None,
        repeat_delay=400,
        repeat_interval=100,
        **kwargs,
    ):
        # Let base draw itself, but we override command handling to support repeat
        super().__init__(master, text=text, command=None, **kwargs)
        self._real_command = command
        self._repeat_delay = int(repeat_delay)
        self._repeat_interval = int(repeat_interval)
        self._after_id = None

        # Replace default single-click binding with our own (still fires once immediately)
        self.unbind("<Button-1>")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<Leave>", self._on_release, add="+")

    def _on_press(self, _):
        # visual feedback
        self._highlight()
        # Single-click behavior (fires right away)
        if self._real_command:
            self._real_command()
        # Schedule repeats if the user keeps holding
        self._after_id = self.after(self._repeat_delay, self._repeat)

    def _on_release(self, _):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _repeat(self):
        if self._real_command:
            self._real_command()
        # Keep repeating until released
        self._after_id = self.after(self._repeat_interval, self._repeat)


# ---- Reusable numeric input (value + scalable +/-) ----
class StyledNumericInput(ctk.CTkFrame):
    """Numeric input whose value font and +/- button sizes are fixed by resolution,
    so they match across pages (TimePage, TimePowerPage, PhaseTimePowerPage)."""

    # Per-resolution value font sizes (tweak as desired)
    RES_VALUE_FS = {
        "800x480": 72,
        "1024x600": 90,  # was 120
        "1280x800": 120,  # was 152
    }

    # Per-resolution circular +/- button target sizes (pixels)
    RES_BTN_SIZE = {
        "800x480": 45,
        "1024x600": 65,  # was 96
        "1280x800": 92,  # was 112
    }

    def __init__(
        self,
        master,
        width=200,
        height=200,
        label="label",
        variable=None,
        min_val=0,
        max_val=100,
        repeat_delay=400,
        repeat_interval=100,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=COLOR_FG,
            corner_radius=0,
            border_width=0,
            border_color=COLOR_BLUE,
            width=width,
            height=height,
            **kwargs,
        )
        self.pack_propagate(False)
        self.variable = variable or ctk.IntVar(value=0)
        self.min_val = min_val
        self.max_val = max_val
        self._repeat_delay = int(repeat_delay)
        self._repeat_interval = int(repeat_interval)

        self.level_label = ctk.CTkLabel(
            self, text=label, text_color=COLOR_BLUE, font=("Arial", 16, "normal")
        )
        self.level_label.pack(anchor="w", padx=0, pady=(0, 4))

        self.num_frame = ctk.CTkFrame(self, fg_color=COLOR_BLUE, corner_radius=12)
        self.num_frame.pack(fill="both", expand=True)

        self.value_label = ctk.CTkLabel(
            self.num_frame,
            textvariable=self.variable,
            font=("Arial", 64, "bold"),
            width=120,
            text_color=COLOR_NUMBERS,
            bg_color=COLOR_BLUE,
            anchor="center",
        )
        self.value_label.place(relx=0.5, rely=0.5, anchor="center")

        # Press-and-hold buttons
        self.btn_plus = HoldCircularButton(
            self.num_frame,
            text="+",
            command=self.increase,
            size=50,
            repeat_delay=self._repeat_delay,
            repeat_interval=self._repeat_interval,
        )
        self.btn_minus = HoldCircularButton(
            self.num_frame,
            text="–",
            command=self.decrease,
            size=50,
            repeat_delay=self._repeat_delay,
            repeat_interval=self._repeat_interval,
        )
        self.btn_plus.place(relx=1.0, rely=0.0, x=-8, y=8, anchor="ne")
        self.btn_minus.place(relx=1.0, rely=1.0, x=-8, y=-8, anchor="se")

        # Resize hooks:
        # - outer widget changes size on TimePage (relwidth/relheight)
        # - inner num_frame changes size on TimePower/Phase pages
        self.bind("<Configure>", self._on_resize)
        self.num_frame.bind("<Configure>", self._on_resize)
        # run once after initial layout to avoid 1x1 geometry
        self.after(0, self._on_resize)

    def _on_resize(self, _e=None):
        # --- Resolution-consistent value font (identical across pages) ---
        fs = self.RES_VALUE_FS.get(
            HMISizePos.SCREEN_RES,
            HMISizePos.s(96),  # fallback if a new resolution is added
        )
        self.value_label.configure(font=("Arial", fs, "bold"))

        # --- Resolution-consistent +/- target, capped to available box space ---
        # look at both the inner and outer geometry; pick whichever is larger
        w = max(1, self.num_frame.winfo_width(), self.winfo_width())
        h = max(1, self.num_frame.winfo_height(), self.winfo_height())

        # if geometry isn't realized yet, try again shortly
        if w < 10 or h < 10:
            self.after(10, self._on_resize)
            return

        target = self.RES_BTN_SIZE.get(
            HMISizePos.SCREEN_RES,
            HMISizePos.s(80),  # fallback for future profiles
        )
        cap = int(min(w, h) * 0.42)  # breathing room inside the rounded box
        btn_size = max(44, min(target, cap))

        self.btn_plus.set_size(btn_size)
        self.btn_minus.set_size(btn_size)

        # Header label: scale by resolution (not box height) for consistency
        self.level_label.configure(font=("Arial", HMISizePos.s(16), "normal"))

    def increase(self):
        v = self.variable.get()
        if v < self.max_val:
            self.variable.set(v + 1)

    def decrease(self):
        v = self.variable.get()
        if v > self.min_val:
            self.variable.set(v - 1)


# ---- Layout helper for two-card pages (Time left, Power right) ----


def compute_two_card_layout(W: int, H: int):
    """Returns dict of geometry numbers used by Time/Phase pages."""
    top_band_h = int(H * 0.16)  # title band
    cards_h = int(H * 0.52)  # cards band height
    side_pad = int(W * 0.025)
    gap_w = int(W * 0.03)
    left_w = int(W * 0.61)
    right_w = int(W * 0.29)
    x_left = side_pad
    x_right = W - side_pad - right_w

    header_y = 10
    divider_y = int(cards_h * 0.16)
    inner_top = divider_y + 12
    inner_h = max(10, cards_h - inner_top - 12)
    tc_gap = int(left_w * 0.04)
    tc_w = int((left_w - 14 - tc_gap) / 2)

    return {
        "top_y": top_band_h,
        "cards_h": cards_h,
        "left_w": left_w,
        "right_w": right_w,
        "x_left": x_left,
        "x_right": x_right,
        "header_y": header_y,
        "divider_y": divider_y,
        "inner_top": inner_top,
        "inner_h": inner_h,
        "tc_gap": tc_gap,
        "tc_w": tc_w,
    }
