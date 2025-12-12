import customtkinter as ctk
import time


class CircularProgress_admin(ctk.CTkCanvas):
    def __init__(
        self,
        master,
        size=200,
        thickness=15,
        fg_color="#89C8F8",
        bg_color="#D6ECFD",
        **kwargs,
    ):
        super().__init__(
            master,
            width=size,
            height=size,
            bg="#DAFAFF",
            highlightthickness=0,
            **kwargs,
        )
        self.size = size
        self.thickness = thickness
        self.fg_color = fg_color
        self.bg_color = bg_color
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

        # Foreground arc
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

        # Center text
        self.text_id = self.create_text(
            size // 2, size // 2, text="0:00", font=("Arial", 32, "bold"), fill="black"
        )

    def update_progress(self, remaining_time, total_time):
        """Update arc and time text."""
        ratio = remaining_time / total_time if total_time > 0 else 0
        angle = -ratio * 360
        if abs(angle) >= 360:  # Ensure full arc draws correctly
            angle = -359.9
        self.itemconfig(self.arc, extent=angle)

        minutes, seconds = divmod(int(max(0, remaining_time)), 60)
        self.itemconfig(self.text_id, text=f"{minutes}:{seconds:02d}")

    def _resolve_bg(master):
        """Return a real hex color for Tk/CTk parents."""
        # Prefer CTk's fg_color if present
        try:
            fg = master.cget("fg_color")  # CTk returns a color or (light, dark)
            if isinstance(fg, tuple):
                return fg[0] if ctk.get_appearance_mode() == "Light" else fg[1]
            if fg and fg != "transparent":
                return fg
        except Exception:
            pass

        # Fall back to classic Tk background keys
        for key in ("bg", "background"):
            try:
                return master.cget(key)
            except Exception:
                pass

        return "#FFFFFF"  # safe default


class TimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Countdown Timer")
        self.geometry("320x460")
        ctk.set_appearance_mode("light")

        self.total_time = 10  # Total countdown time (seconds)
        self.remaining_time = self.total_time
        self.start_time = None
        self.running = False
        self.paused = False

        self.progress = CircularProgress(self, size=250, thickness=20)
        self.progress.pack(pady=20)

        # Buttons
        self.start_button = ctk.CTkButton(
            self, text="START", command=self.start_timer, fg_color="#22C55E"
        )
        self.start_button.pack(pady=5)

        self.pause_button = ctk.CTkButton(
            self, text="PAUSE", command=self.pause_timer, fg_color="#F59E0B"
        )
        self.pause_button.pack(pady=5)

        self.reset_button = ctk.CTkButton(
            self, text="RESET", command=self.reset_timer, fg_color="#EF4444"
        )
        self.reset_button.pack(pady=5)

        self.restart_button = ctk.CTkButton(
            self, text="RESTART", command=self.restart_timer, fg_color="#3B82F6"
        )
        self.restart_button.pack(pady=5)

        self.progress.update_progress(self.remaining_time, self.total_time)

    def start_timer(self):
        if not self.running:
            self.running = True
            self.start_time = time.time() - (self.total_time - self.remaining_time)
            self.animate_timer()

    def animate_timer(self):
        if not self.running:
            return
        elapsed = time.time() - self.start_time
        self.remaining_time = max(0, self.total_time - elapsed)
        self.progress.update_progress(self.remaining_time, self.total_time)

        if self.remaining_time > 0:
            self.after(50, self.animate_timer)
        else:
            self.running = False
            self.progress.update_progress(0, self.total_time)

    def pause_timer(self):
        if self.running:
            self.running = False
            self.paused = True
        elif self.paused:  # Resume
            self.start_timer()
            self.paused = False

    def reset_timer(self):
        self.running = False
        self.paused = False
        self.remaining_time = self.total_time
        self.progress.update_progress(self.remaining_time, self.total_time)

    def restart_timer(self):
        """Stop, reset, and immediately start the timer again."""
        self.reset_timer()
        self.start_timer()


if __name__ == "__main__":
    app = TimerApp()
    app.mainloop()
