# FoodReadyPage.py
import customtkinter as ctk
from typing import Optional
from pathlib import Path
from PIL import Image
from hmi_consts import HMIColors

from play_sound import play_done


class FoodReadyPage_admin(ctk.CTkFrame):
    """
    Minimal page that shows 'Food is ready!' and a thumbs-up image, sized for 800x480.
    Signature matches the other pages: __init__(controller, shared_data=None, **kwargs)

    Place your image at:
        <this file>/assets/thumbs_up.png

    Usage with your controller (pre-instantiated in self.pages):
        self.show_FoodReadyPage(auto_return_to=HomePage, after_ms=3000)

    Or directly:
        page = self.pages[FoodReadyPage]
        self.show_page(FoodReadyPage)
        page.configure_auto_return(auto_return_to=HomePage, after_ms=3000)
    """

    def __init__(self, controller, shared_data=None, **kwargs):
        super().__init__(controller, fg_color=HMIColors.color_fg, **kwargs)
        self.controller = controller
        self.shared_data = shared_data or {}

        self._auto_return_target: Optional[type] = None
        self._auto_return_after_ms: int = 0
        self._after_id: Optional[str] = None

        # Layout for 800x480
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Message
        self.msg = ctk.CTkLabel(
            self,
            text="Food is ready!",
            font=ctk.CTkFont(size=44, weight="bold"),
            text_color="#2F6FAB",  # pleasant blue similar to your mock
        )
        self.msg.grid(row=0, column=0, sticky="s", pady=(0, 6))

        # ---- Thumbs-up IMAGE (works on Windows & Raspberry Pi) ----
        # Keep a persistent reference to the CTkImage on self to prevent GC.
        self.thumbs_img = None
        self.thumb = None

        assets_dir = Path(__file__).resolve().parent / "assets"
        img_path = assets_dir / "thumbs_up_admin.png"  # <- put your PNG here

        try:
            pil_img = Image.open(img_path).convert("RGBA")
            # Adjust size to taste; the CTkImage will scale the bitmap cleanly.
            self.thumbs_img = ctk.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=(200, 200),
            )
            self.thumb = ctk.CTkLabel(self, text="", image=self.thumbs_img)
        except Exception as e:
            # Fallback text if the image can't be loaded; prints error to console.
            print(f"[FoodReadyPage] Could not load image {img_path}: {e}")
            self.thumb = ctk.CTkLabel(
                self,
                text="(thumbs_up.png not found)",
                font=ctk.CTkFont(size=20),
                text_color="#7A7A7A",
            )

        self.thumb.grid(row=1, column=0, sticky="n", pady=(6, 0))

        # Tap anywhere to return
        self.bind_all_events()

    # ---------- Public API ----------
    def configure_auto_return(
        self, auto_return_to: Optional[type] = None, after_ms: int = 0
    ):
        """
        Set an optional auto-return target and delay (ms). Call before showing the page,
        or inside your controller's show_FoodReadyPage helper.
        """
        self._auto_return_target = auto_return_to
        self._auto_return_after_ms = max(0, int(after_ms))

    def on_show(self):
        play_done()
        """Call from controller right after raising this page."""
        # Cancel any previous pending timers
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        if self._auto_return_target and self._auto_return_after_ms > 0:
            self._after_id = self.after(self._auto_return_after_ms, self._go_back)

    def on_hide(self):
        """Optional cleanup when leaving this page."""
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    # ---------- Internal ----------
    def bind_all_events(self):
        # Click or touch anywhere to go back immediately
        for widget in (self, self.msg, self.thumb):
            widget.bind("<Button-1>", lambda _e: self._go_back())

    def _go_back(self):
        target = self._auto_return_target
        self.controller.show_HomePage()


if __name__ == "__main__":
    import customtkinter as ctk

    ctk.set_appearance_mode("light")

    class DummyController(ctk.CTk):
        def show_page(self, target):
            print(f"Switching to page: {target}")

    controller = DummyController()
    controller.geometry("800x480")
    controller.title("FoodReadyPage Test")

    page = FoodReadyPage(controller)
    page.place(x=0, y=0, relwidth=1, relheight=1)

    page.configure_auto_return(auto_return_to=None, after_ms=5000)
    page.on_show()

    controller.mainloop()
