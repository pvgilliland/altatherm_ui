# cooking_page.py
import json
import os
from typing import List
import customtkinter as ctk
from PIL import Image, ImageDraw
from hotspots import Hotspot
from hmi_consts import ASSETS_DIR, PROGRAMS_DIR
from typing import Optional
from SelectProgramPage import (
    load_program_into_sequence_collection,
    save_program_from_sequence_collection,
)


class CookingPage:

    IMAGE_NAME = "05CookingPage.png"

    def __init__(self, controller):
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

        image_path = os.path.join(ASSETS_DIR, filename)

        print(image_path)

        program_number: int = meal_index + 31

        load_program_into_sequence_collection(program_number)

        path = str(PROGRAMS_DIR / f"program{program_number}.alt")
        with open(path, "r") as f:
            data = json.load(f)
        total_time = data.get("total_time")

        # Show it in the confirmation page
        self.controller.view.set_overlay_image(
            image_path, name, total_time, size=(270, 200)
        )

    def on_hide(self):
        self.controller.view.set_overlay_image(None, None, None)
