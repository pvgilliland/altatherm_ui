# cooking_page.py
import json
import os
import time
from typing import List, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw

from hotspots import Hotspot
from hmi_consts import ASSETS_DIR, PROGRAMS_DIR


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
                "start",  # acts as Start when idle, Stop when running
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
        print("[CookingPage] Back clicked")
        # Treat "Back" as a stop for the progress ring and cook cycle
        self._stop_progress()
        try:
            self.controller.stop_current_cook()
        except Exception as e:
            print(f"[CookingPage] stop_current_cook in on_back_clicked failed: {e}")
        if self.controller:
            self.controller.show_PrepareForCookingPage2()

    def on_start_clicked(self):
        """
        Start/Stop behavior (best design):

        - If NOT currently running:
            * Ask controller to start_meal_program(meal_index)
            * Controller builds & starts CookingSequenceManager, sets oven_state, etc.
            * This page starts the circular countdown with the returned total time.

        - If already running:
            * Stop countdown
            * Ask controller to stop_current_cook() (stops sequences + power + oven_state)
            * Return to PrepareForCookingPage2
        """
        print("[CookingPage] Start clicked")

        # --- START case ---
        if not self._running:
            if self.meal_index is None:
                print("[CookingPage] No meal_index; cannot start")
                return

            try:
                total = float(self.controller.start_meal_program(self.meal_index))
            except Exception as e:
                print(f"[CookingPage] controller.start_meal_program failed: {e}")
                return

            if total <= 0:
                print(
                    "[CookingPage] start_meal_program returned non-positive total; aborting"
                )
                return

            print(f"[CookingPage] Starting circular countdown for {total:.1f}s")
            self._start_progress(total)
            return

        # --- STOP case (already running) ---
        print("[CookingPage] Stop requested")
        self._stop_progress()
        try:
            self.controller.stop_current_cook()
        except Exception as e:
            print(f"[CookingPage] stop_current_cook in on_start_clicked failed: {e}")

        if self.controller:
            self.controller.show_PrepareForCookingPage2()

    # ------------------------------------------------------------------
    # CircularProgress overlay plumbing
    # ------------------------------------------------------------------
    def _ensure_progress_widget(self):
        """
        Make sure the shared CircularProgress overlay exists and is visible.
        """
        view = getattr(self.controller, "view", None)
        if view is None:
            return None

        # ImageHotspotView exposes show_circular_progress()
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

            print("[CookingPage] Cook timer complete")
            # Optional: could navigate to a "Food Ready" page here

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
        """
        Called when CookingPage is displayed.

        - Records the meal_index
        - Reads program{31+meal_index}.alt's total_time ("MM:SS") for initial ring display
        - Prepares the CircularProgress ring to show the full time, but does NOT start.
        """
        self.meal_index = meal_index

        program_number: int = meal_index + 31
        path = str(PROGRAMS_DIR / f"program{program_number}.alt")

        total_timef: float = 0.0
        try:
            with open(path, "r") as f:
                data = json.load(f)
            total_time_str = data.get("total_time") or "0:00"
            total_timef = CookingPage.mmss_to_seconds(total_time_str)
        except Exception as e:
            print(f"[CookingPage] Failed to read {path}: {e}")
            total_timef = 0.0

        # Store (but do NOT auto-start; Start button will kick everything off)
        self._total_time = total_timef
        self._remaining_time = total_timef
        self._start_epoch = None
        self._running = False

        # Prepare the circular ring to show the full time initially
        cp = self._ensure_progress_widget()
        if cp is not None:
            if self._total_time > 0:
                cp.update_progress(self._total_time, self._total_time)
            else:
                cp.update_progress(0.0, 1.0)

        # If you want overlay image/name/time, you can call:
        #   self.controller.view.set_overlay_image(image_path, name, cook_time, size)
        # here using SelectMealPage data.

    def on_hide(self):
        # Clear overlay and stop countdown
        try:
            self.controller.view.set_overlay_image(None, None, None)
        except Exception:
            pass
        self._stop_progress()
        # Safety: stop sequences/power if we navigate away unexpectedly
        try:
            self.controller.stop_current_cook()
        except Exception as e:
            print(f"[CookingPage] stop_current_cook in on_hide failed: {e}")

    @staticmethod
    def mmss_to_seconds(mmss: str) -> float:
        minutes, seconds = map(int, mmss.split(":"))
        return minutes * 60 + seconds
