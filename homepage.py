# homepage.py
import os
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

    IMAGE_NAME = "HomePage.png"

    def __init__(self, controller=None):
        self.controller = controller

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)

        self.hotspots: List[Hotspot] = [
            Hotspot("start", (519, 577, 753, 654), self.on_start_clicked),
        ]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_start_clicked(self):
        print("HomePage: Start clicked")
        if self.controller:
            # e.g. self.controller.show_PreparePage()
            self.controller.show_SelectMealPage()


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
