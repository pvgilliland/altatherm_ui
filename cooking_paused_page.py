# cooking_paused_page.py
import os
from typing import List
import customtkinter as ctk
from PIL import Image, ImageDraw
from hotspots import Hotspot


class CookingPausedPage:
    """
    Page model:
      - uses homepage.png
      - defines three hotspots and their callbacks
    """

    IMAGE_NAME = "07CookingPausedPage.png"

    def __init__(self, controller=None):
        self.controller = controller

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)

        self.hotspots: List[Hotspot] = [
            Hotspot("stop", (262, 530, 578, 590), self.on_stop_clicked),
            Hotspot("resume", (654, 530, 1027, 590), self.on_resume_clicked),
        ]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_stop_clicked(self):
        if not self.controller:
            return

        print("[CookingPausedPage] Stop (hard cancel) clicked")

        # 1) Stop the current cook completely (sequences + zones + oven_state)
        try:
            self.controller.stop_current_cook()
        except Exception as e:
            print(f"[CookingPausedPage] stop_current_cook failed: {e}")

        # 2) Reset CookingPage's timer / pause state so the next run starts fresh
        try:
            cp = getattr(self.controller, "cooking_page", None)
            if cp is not None and hasattr(cp, "reset_after_hard_stop"):
                cp.reset_after_hard_stop()
        except Exception as e:
            print(f"[CookingPausedPage] reset_after_hard_stop failed: {e}")

        # 3) Go back to meal selection
        self.controller.show_SelectMealPage()

    def on_resume_clicked(self):
        if not self.controller:
            return

        # 1) Resume the sequence manager / hardware
        if hasattr(self.controller, "resume_current_cook"):
            try:
                self.controller.resume_current_cook()
            except Exception as e:
                print(f"[CookingPausedPage] resume_current_cook failed: {e}")

        # 2) Go back to CookingPage. Its on_show() will detect _paused
        #    and restart the circular timer from the remaining time.
        self.controller.show_CookingPage()
