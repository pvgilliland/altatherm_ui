# testpage.py
import os
from typing import List
import customtkinter as ctk
from PIL import Image, ImageDraw
from hotspots import Hotspot


class PrepareForCookingPage1:
    """
    Page model:
      - uses homepage.png
      - defines three hotspots and their callbacks
    """

    IMAGE_NAME = "02PrepareForCooking.png"

    def __init__(self, controller=None):
        self.controller = controller

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
                f"forward",
                (1122, 642, 1220, 707),
                self.on_forward_clicked,  # ← capture parameter
            ),
        ]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_back_clicked(self):
        print("on_back_clicked")
        if self.controller:
            self.controller.show_SelectMealPage()

    def on_forward_clicked(self):
        print("on_forward_clicked")
        if self.controller:
            self.controller.show_PrepareForCookingPage2()
