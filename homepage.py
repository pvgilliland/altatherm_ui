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

    IMG_WIDTH = 1280
    IMG_HEIGHT = 800
    IMAGE_NAME = "homepage.png"

    def __init__(self, controller=None):
        self.controller = controller

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)

        if not os.path.exists(self.image_path):
            self._generate_placeholder_homepage(self.image_path)

        self.hotspots: List[Hotspot] = [
            Hotspot("start", (150, 550, 450, 650), self.on_start_clicked),
            Hotspot("settings", (500, 550, 800, 650), self.on_settings_clicked),
            Hotspot("exit", (850, 550, 1150, 650), self.on_exit_clicked),
        ]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_start_clicked(self):
        print("HomePage: Start clicked")
        if self.controller:
            # e.g. self.controller.show_PreparePage()
            pass

    def on_settings_clicked(self):
        print("HomePage: Settings clicked")
        if self.controller:
            # e.g. self.controller.show_SettingsPage()
            pass

    def on_exit_clicked(self):
        print("HomePage: Exit clicked")
        # root = self.winfo_toplevel()  # safe, guaranteed root window
        # root.destroy()

    # ------------------------------------------------------------------
    # Placeholder image generator
    # ------------------------------------------------------------------
    @classmethod
    def _generate_placeholder_homepage(cls, path: str):
        img = Image.new("RGB", (cls.IMG_WIDTH, cls.IMG_HEIGHT), "#303030")
        d = ImageDraw.Draw(img)

        # Title bar
        d.rectangle((0, 0, cls.IMG_WIDTH, 120), fill="#505050")
        d.text((40, 40), "HOME PAGE", fill="white")

        # Three buttons
        d.rectangle((150, 550, 450, 650), fill="#3a7f3a")
        d.text((210, 585), "START", fill="white")

        d.rectangle((500, 550, 800, 650), fill="#3a4f7f")
        d.text((530, 585), "SETTINGS", fill="white")

        d.rectangle((850, 550, 1150, 650), fill="#7f3a3a")
        d.text((940, 585), "EXIT", fill="white")

        img.save(path)
        print(f"Generated placeholder homepage image at: {path}")


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
