# testpage.py
import os
from typing import List
import customtkinter as ctk
from PIL import Image, ImageDraw
from hotspots import Hotspot
from hmi_consts import ASSETS_DIR


class StartCookingConfirmation:
    """
    Page model:
      - uses homepage.png
      - defines three hotspots and their callbacks
    """

    IMAGE_NAME = "04ConfirmationPage.png"

    def __init__(self, controller=None):
        self.controller = controller
        self.meal_index: int = -1  # ← store for incoming parameter

        self.meal_images = {
            0: ("ShrimpCurry.png", "Shrimp Curry"),
            1: ("ChickenParmesan.png", "Chicken Parmesan"),
            2: ("BeefStirFry.png", "Beef Stir Fry"),
            3: ("salmon.png", "Salmon"),
            4: ("SteakAndBroccoli.png", "Steak abd Broccoli"),
            5: ("Reheat.png", "Reheat"),
        }

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)

        self.hotspots: List[Hotspot] = [
            Hotspot(
                f"back",
                (84, 642, 154, 707),
                self.on_back_clicked,  # ← capture parameter
            ),
            Hotspot(
                f"start",
                (490, 641, 785, 716),
                self.on_start_clicked,  # ← capture parameter
            ),
        ]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_back_clicked(self):
        print("on_back_clicked")
        if self.controller:
            self.controller.show_PrepareForCookingPage2()

    def on_start_clicked(self):
        print("on_start_clicked")
        if self.controller:
            pass

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------
    def on_show(self, meal_index: int):
        self.meal_index = meal_index
        # Look up the meal's image
        filename, name = self.meal_images[meal_index]

        if not filename:
            self.controller.view.set_overlay_image(None)
            return

        path = os.path.join(ASSETS_DIR, filename)

        print(path)

        # Show it in the confirmation page
        self.controller.view.set_overlay_image(path, name, size=(270, 200))

    def on_hide(self):
        self.controller.view.set_overlay_image(None, None)
