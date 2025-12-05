# testpage.py
import os
from typing import List
import customtkinter as ctk
from PIL import Image, ImageDraw
from hotspots import Hotspot


class SelectMealPage:
    """
    Page model:
      - uses homepage.png
      - defines three hotspots and their callbacks
    """

    IMAGE_NAME = "SelectMealPage.png"

    def __init__(self, controller=None):
        self.controller = controller

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)

        topLeftX = 194
        topLeftY = 223
        btnWidth = 263
        btnHeight = 190
        btnPaddingX = 34
        btnPaddingY = 63

        self.hotspots: List[Hotspot]
        self.hotspots = []

        for i in range(6):
            x = topLeftX + (i % 3) * (btnWidth + btnPaddingX)
            y = topLeftY + int((i / 3)) * (btnHeight + btnPaddingY)
            hs = Hotspot(
                f"meal{i}",
                (x, y, x + btnWidth, y + btnHeight),
                lambda meal=i: self.on_meal_clicked(meal),  # ← capture parameter
            )
            self.hotspots.append(hs)

        self.hotspots.append(
            Hotspot(
                f"back",
                (84, 642, 154, 707),
                self.on_back_clicked,  # ← capture parameter
            )
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_meal_clicked(self, meal_index):
        print(f"on_meal_clicked {meal_index}")
        if self.controller:
            # self.controller.show_HomePage()
            pass

    def on_back_clicked(self):
        print("on_back_clicked")
        if self.controller:
            self.controller.show_HomePage()
            pass

    def on_exit_clicked(self):
        print("HomePage: Exit clicked")
        # root = self.winfo_toplevel()  # safe, guaranteed root window
        # root.destroy()
