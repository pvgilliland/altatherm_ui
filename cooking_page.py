# cooking_page.py
import json
import os
import time
from typing import List, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw

from hotspots import Hotspot
from hmi_consts import ASSETS_DIR, PROGRAMS_DIR
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
                "back",
                (84, 642, 154, 707),
                self.on_back_clicked,
            ),
            Hotspot(
                "start",  # visually "Stop" button while cooking
                (490, 641, 785, 716),
                self.on_start_clicked,
            ),
        ]

        # --- Timer / CircularProgress state ---
        self.meal_index: Optional[int] = None
        self._total_time: float = 0.0
        self._remaining_time: float = 0.0
        self._start_epoch: Optional[float] = None
        self._running: bool = False
        self._tick_after_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_back_clicked(self):
        print("on_back_clicked")
        # Treat "Back" as a stop for the progress ring as well
        self._stop_progress()
        if self.controller:
            self.controller.show_PrepareForCookingPage2()

    def on_start_clicked(self):
        """
        This hotspot corresponds to the bottom-center pill button which
        visually says "Stop". For now we just stop the cooking countdown
        and return to the previous page; you can extend this to mirror
        the SessionEndedPage flow from CircularProgressPage if desired.
        """
        print("on_start_clicked (Stop)")
        self._stop_progress()
        if self.controller:
            # Simple behavior: go back to the prepare page.
            # If you want the full SessionEndedPage flow, you can call:
            #   self.controller.show_SessionEndedPage(...)
            self.controller.show_PrepareForCookingPage2()

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------
    def _ensure_progress_widget(self):
        """
        Make sure the shared CircularProgress overlay exists and is visible.
        """
        view = getattr(self.controller, "view", None)
        if view is None:
            return None

        # ImageHotspotView now exposes show_circular_progress()
        if hasattr(view, "show_circular_progress"):
            view.show_circular_progress()
            return getattr(view, "circular_progress", None)
        return None

    def _hide_progress_widget(self):
        view = getattr(self.controller, "view", None)
        if view is not None and hasattr(view, "hide_circular_progress"):
            view.hide_circular_progress()

    def _schedule_tick(self):
        if not self._running:
            return
        view = getattr(self.controller, "view", None)
        if view is None:
            return
        # 50 ms step like CircularProgressPage
        self._tick_after_id = view.after(50, self._tick)

    def _cancel_tick(self):
        if self._tick_after_id is None:
            return
        view = getattr(self.controller, "view", None)
        if view is None:
            return
        try:
            view.after_cancel(self._tick_after_id)
        except Exception:
            pass
        self._tick_after_id = None

    def _tick(self):
        if not self._running:
            return

        view = getattr(self.controller, "view", None)
        cp = getattr(view, "circular_progress", None) if view else None

        # Same style of countdown as CircularProgressPage._tick
        elapsed = time.time() - (self._start_epoch or time.time())
        self._remaining_time = max(0.0, self._total_time - elapsed)

        if cp is not None:
            cp.update_progress(self._remaining_time, self._total_time)

        if self._remaining_time > 0.0:
            self._schedule_tick()
        else:
            # Finished
            self._running = False
            if cp is not None:
                cp.update_progress(0.0, self._total_time)
            # At this point you could navigate to FoodReadyPage if desired,
            # similar to CircularProgressPage:
            #   self.controller.show_FoodReadyPage(...)
            # For now we just leave the CookingPage showing "0:00".
            print("[CookingPage] Cook timer complete")

    def _start_progress(self, total_seconds: float):
        """
        Start / restart the circular countdown for the given total time.
        """
        try:
            total_seconds = float(total_seconds or 0.0)
        except (TypeError, ValueError):
            total_seconds = 0.0

        if total_seconds <= 0:
            # Nothing to count down; just ensure ring shows 0
            cp = self._ensure_progress_widget()
            if cp is not None:
                cp.update_progress(0.0, 1.0)
            self._running = False
            return

        cp = self._ensure_progress_widget()
        if cp is None:
            return

        self._cancel_tick()

        self._total_time = max(0.0, total_seconds)
        self._remaining_time = self._total_time
        self._start_epoch = time.time()
        self._running = True

        # Initialize ring at full time
        cp.update_progress(self._remaining_time, self._total_time)
        self._schedule_tick()

    def _stop_progress(self):
        """
        Stop the countdown and hide the circular control.
        """
        self._running = False
        self._cancel_tick()
        self._hide_progress_widget()

    # ------------------------------------------------------------------
    # Page lifecycle
    # ------------------------------------------------------------------
    def on_show(self, meal_index: int):
        self.meal_index = meal_index
        # Look up the meal's image

        """
        filename, name = self.meal_images[meal_index]

        if not filename:
            self.controller.view.set_overlay_image(None, None, None)
            self._stop_progress()
            return

        image_path = os.path.join(ASSETS_DIR, filename)
        print(image_path)
        """

        program_number: int = meal_index + 31

        # load_program_into_sequence_collection(program_number)

        path = str(PROGRAMS_DIR / f"program{program_number}.alt")
        with open(path, "r") as f:
            data = json.load(f)
        total_time = data.get("total_time")
        total_timef: float = CookingPage.mmss_to_seconds(total_time)

        # Show it in the confirmation page
        # self.controller.view.set_overlay_image(
        #    image_path, name, total_time, size=(270, 200)
        # )

        # Also start the circular countdown using the same total_time
        self._start_progress(total_timef)

    def on_hide(self):
        # Clear overlay and stop countdown
        self.controller.view.set_overlay_image(None, None, None)
        self._stop_progress()

    @staticmethod
    def mmss_to_seconds(mmss: str) -> float:
        minutes, seconds = map(int, mmss.split(":"))
        return minutes * 60 + seconds
