# testpage.py
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


class StartCookingConfirmation:
    """
    Page model:
      - uses homepage.png
      - defines three hotspots and their callbacks
    """

    IMAGE_NAME = "04ConfirmationPage.png"

    def __init__(self, controller):
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
        print("StartCookingConfirmation: Start clicked")
        if not self.controller:
            return

        # If this is the Reheat meal, capture the chosen seconds
        if self.meal_index == 5:
            view = getattr(self.controller, "view", None)
            if view and hasattr(view, "get_reheat_seconds"):
                secs = view.get_reheat_seconds()
                try:
                    secs = int(secs)
                except (TypeError, ValueError):
                    secs = 0
                secs = max(0, secs)
                print(f"[StartCookingConfirmation] reheat_seconds = {secs}")
                self.controller.shared_data["reheat_seconds"] = secs

        # Then go to the CookingPage (it will read the override)
        self.controller.show_CookingPage()

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

        # -------------------------------
        # If meal_index == 5 (Reheat), show 15-sec adjuster
        # -------------------------------
        if meal_index == 5:
            print("Showing TimeAdjustControl for Reheat")

            # Default to 30 sec, clamp min/max as needed
            self.controller.view.show_reheat_time_control(
                initial_seconds=0,
                min_seconds=0,
                max_seconds=120,  # up to 5 minutes if you want
                on_change=lambda secs: print("Reheat time changed:", secs),
            )

        else:
            # Hide it for all non-Reheat meals
            self.controller.view.hide_reheat_time_control()

    def on_hide(self):
        self.controller.view.set_overlay_image(None, None, None)
        self.controller.view.hide_reheat_time_control()
