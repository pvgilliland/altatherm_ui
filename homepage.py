# homepage.py
import os
import time
from typing import List
import customtkinter as ctk
from PIL import Image, ImageDraw
from hotspots import Hotspot


class HomePage:
    """
    Page model:
      - uses homepage.png
      - defines three hotspots and their callbacks
    """

    IMAGE_NAME = "00HomePage.png"

    def __init__(self, controller=None):
        self.controller = controller

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)

        self.hotspots: List[Hotspot] = [
            Hotspot("logo", (560, 230, 730, 390), self.on_logo_clicked),
            Hotspot("start", (519, 577, 753, 654), self.on_start_clicked),
        ]

        # Track recent logo click timestamps (seconds since epoch)
        self._logo_click_times: list[float] = []

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_start_clicked(self):
        print("HomePage: Start clicked")
        if self.controller:
            # e.g. self.controller.show_PreparePage()
            self.controller.show_SelectMealPage()

    def on_logo_clicked(self):
        """
        Detect when the logo has been clicked 5 times within 3 seconds.
        """
        print("[HomePage] Logo clicked")

        now = time.time()
        window = 3.0  # seconds

        # Keep only clicks within the last `window` seconds
        self._logo_click_times = [
            t for t in self._logo_click_times if (now - t) <= window
        ]

        # Add this click
        self._logo_click_times.append(now)

        print(
            f"[HomePage] Logo clicks in last {window}s: {len(self._logo_click_times)}"
        )

        if len(self._logo_click_times) >= 5:
            print("[HomePage] 5 logo clicks within 3s - SECRET COMBO DETECTED")

            # Optional: reset so they have to do 5 again next time
            self._logo_click_times.clear()

            # Hook for your admin / hidden screen
            if self.controller and hasattr(self.controller, "on_logo_easter_egg"):
                try:
                    self.controller.on_logo_easter_egg()
                except Exception as e:
                    print(f"[HomePage] on_logo_easter_egg failed: {e}")


# ----------------------------------------------------------------------
# Self-test / harness for HomePage + ImageHotspotView
# ----------------------------------------------------------------------
if __name__ == "__main__":
    from image_hotspot_view import ImageHotspotView

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1280x800")

    # Singleton view
    view = ImageHotspotView.get_instance(root)
    view.pack(fill="both", expand=True)

    # Page model (controller is root for this simple demo)
    home_page = HomePage(controller=root)

    # Bind it to the singleton view
    view.set_page(home_page)

    root.mainloop()
