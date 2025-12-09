import customtkinter as ctk
import time


class CircularProgress(ctk.CTkCanvas):
    def __init__(
        self,
        master,
        size=520,
        thickness=32,
        fg_color="#C7A64B",  # GOLD ring
        bg_color="#1A1A1A",  # Dark background inside ring
        text_color="#FFFFFF",  # White timer text
        **kwargs,
    ):
        super().__init__(
            master,
            width=size,
            height=size,
            bg=bg_color,
            highlightthickness=0,
            **kwargs,
        )

        self.size = size
        self.thickness = thickness
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.text_color = text_color
        self.angle = 0

        # Background circle
        self.create_oval(
            thickness,
            thickness,
            size - thickness,
            size - thickness,
            outline=self.bg_color,
            width=thickness,
        )

        # Foreground arc (progress)
        self.arc = self.create_arc(
            thickness,
            thickness,
            size - thickness,
            size - thickness,
            start=90,
            extent=self.angle,
            outline=self.fg_color,
            width=thickness,
            style="arc",
        )

        # Center time text
        self.text_id = self.create_text(
            size // 2,
            size // 2,
            text="0:00",
            font=("Arial", 52, "bold"),  # bigger text
            fill=self.text_color,
        )

    @staticmethod
    def _resolve_bg(master):
        # Match parent background so no white box
        try:
            fg = master.cget("fg_color")
            if isinstance(fg, tuple):
                return fg[0] if ctk.get_appearance_mode() == "Light" else fg[1]
            if fg and fg != "transparent":
                return fg
        except Exception:
            pass
        return "#000000"

    def update_progress(self, remaining_time, total_time):
        ratio = remaining_time / total_time if total_time > 0 else 0
        angle = -ratio * 360
        if abs(angle) >= 360:
            angle = -359.9
        self.itemconfig(self.arc, extent=angle)

        minutes, seconds = divmod(int(max(0, remaining_time)), 60)
        self.itemconfig(self.text_id, text=f"{minutes}:{seconds:02d}")
