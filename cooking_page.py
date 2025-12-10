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
                "start",  # acts as Start initially, then Pause/Resume during cook
                (490, 641, 785, 716),
                self.on_stop_clicked,
            ),
        ]

        # --- Timer / CircularProgress state ---
        self.meal_index: Optional[int] = None
        self._total_time: float = 0.0
        self._remaining_time: float = 0.0
        self._start_epoch: Optional[float] = None
        self._running: bool = False  # actively counting down
        self._paused: bool = False  # paused but not finished/cancelled
        self._tick_after_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_back_clicked(self):
        print("[CookingPage] Back clicked")
        # Treat "Back" as a full stop for the progress ring and cook cycle
        self._stop_progress()
        try:
            self.controller.stop_current_cook()
        except Exception as e:
            print(f"[CookingPage] stop_current_cook in on_back_clicked failed: {e}")
        if self.controller:
            self.controller.show_PrepareForCookingPage2()

    def on_stop_clicked(self):
        """
        Start / Pause / Resume behavior:

        - If NOT running and NOT paused:
            * Start the cook:
              - controller.start_meal_program(meal_index)
              - start circular countdown with returned total time.

        - If currently running:
            * Pause the cook:
              - pause timer
              - controller.pause_current_cook() (if available)
              - navigate to CookingPausedPage

        - If paused (not running, but _paused True):
            * Resume the cook:
              - resume timer based on remaining time
              - controller.resume_current_cook() (if available)
        """
        print("[CookingPage] Start/Pause/Resume clicked")

        # --- START case (first time, or after finished and user presses again) ---
        if not self._running and not self._paused:
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
            self._paused = False
            self._start_progress(total)
            return

        # --- PAUSE case (currently running) ---
        if self._running:
            print("[CookingPage] Pause requested")
            self._pause_progress()

            # Pause sequences / power at controller level (if supported)
            if self.controller and hasattr(self.controller, "pause_current_cook"):
                try:
                    self.controller.pause_current_cook()
                except Exception as e:
                    print(f"[CookingPage] pause_current_cook failed: {e}")

            # Show the CookingPausedPage when we pause
            if self.controller and hasattr(self.controller, "show_CookingPausedPage"):
                try:
                    self.controller.show_CookingPausedPage()
                except Exception as e:
                    print(f"[CookingPage] show_CookingPausedPage failed: {e}")

            return

        # --- RESUME case (paused but not running) ---
        if self._paused and not self._running:
            print("[CookingPage] Resume requested")
            self._resume_progress()

            # Resume sequences / power at controller level (if supported)
            if self.controller and hasattr(self.controller, "resume_current_cook"):
                try:
                    self.controller.resume_current_cook()
                except Exception as e:
                    print(f"[CookingPage] resume_current_cook failed: {e}")

            return

        # Fallback
        print("[CookingPage] on_stop_clicked in unexpected state")

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
            self._paused = False
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
            self._paused = False
            return

        cp = self._ensure_progress_widget()
        if cp is None:
            return

        self._cancel_tick()

        self._total_time = max(0.0, total_seconds)
        self._remaining_time = self._total_time
        self._start_epoch = time.time()
        self._running = True
        self._paused = False

        # Initialize ring at full time
        cp.update_progress(self._remaining_time, self._total_time)
        self._schedule_tick()

    def _pause_progress(self):
        """
        Pause the countdown but keep the circular control visible.
        """
        if not self._running:
            return

        # Ensure we capture the latest remaining time before stopping
        self._tick()  # one last sync; harmless if slightly redundant

        self._cancel_tick()
        self._running = False
        self._paused = True

        # Leave the ring showing the current remaining time

    def _resume_progress(self):
        """
        Resume the countdown from the current remaining time.
        """
        if self._running or not self._paused:
            return

        if self._remaining_time <= 0.0 or self._total_time <= 0.0:
            # Nothing meaningful to resume
            return

        now = time.time()
        # Reconstruct the effective start_epoch so that:
        #   remaining = total - (now - _start_epoch)
        #   => _start_epoch = now - (total - remaining)
        self._start_epoch = now - (self._total_time - self._remaining_time)

        self._running = True
        self._paused = False
        self._schedule_tick()

    def _stop_progress(self):
        """
        Fully stop the countdown and hide the circular control.
        Used for Back / page hide / hard stops.
        """
        self._running = False
        self._paused = False
        self._cancel_tick()
        self._hide_progress_widget()

    # ------------------------------------------------------------------
    # Page lifecycle
    # ------------------------------------------------------------------
    def on_show(self, meal_index: int):
        """
        Called when CookingPage is displayed.

        Two modes:

        - Fresh entry (normal path from SelectMeal/Prepare):
            * Load program total_time
            * Reset timer state
            * Show full circular ring
            * Auto-start cooking

        - Return from a paused state (coming back from CookingPausedPage):
            * Keep _total_time / _remaining_time
            * Recreate ring at the paused value
            * Resume the local countdown (controller already resumed)
        """
        self.meal_index = meal_index

        # ----------------------------
        # RETURNING FROM PAUSE
        # ----------------------------
        if (
            self._paused
            and not self._running
            and self._total_time > 0.0
            and self._remaining_time > 0.0
        ):
            # Just reattach the circular progress at the paused time
            cp = self._ensure_progress_widget()
            if cp is not None:
                cp.update_progress(self._remaining_time, self._total_time)

            # Resume ONLY the local timer; controller.resume_current_cook()
            # will be called from CookingPausedPage.on_resume_clicked.
            if self.controller and hasattr(self.controller, "view"):
                self.controller.view.after_idle(self._resume_progress)

            return

        # ----------------------------
        # FRESH ENTRY (normal start)
        # ----------------------------
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

        # Store base time; on_stop_clicked will start the actual program
        self._total_time = total_timef
        self._remaining_time = total_timef
        self._start_epoch = None
        self._running = False
        self._paused = False

        # Prepare the circular ring to show the full time initially
        cp = self._ensure_progress_widget()
        if cp is not None:
            if self._total_time > 0:
                cp.update_progress(self._total_time, self._total_time)
            else:
                cp.update_progress(0.0, 1.0)

        # Auto-start cooking once the UI is idle (first show only)
        if self.controller and hasattr(self.controller, "view"):
            self.controller.view.after_idle(lambda: self.on_stop_clicked())

    def on_hide(self):
        # Clear any center overlay image if you’re using one
        try:
            self.controller.view.set_overlay_image(None, None, None)
        except Exception:
            pass

        # If we are PAUSED, keep _paused and _remaining_time.
        # Just stop ticking and hide the widget.
        if self._paused and not self._running:
            self._cancel_tick()
            self._hide_progress_widget()
        else:
            # For normal navigation (Back, finished, etc.) do a full stop.
            self._stop_progress()

        # NOTE: We intentionally do NOT call stop_current_cook() here,
        # because the natural completion path already powers down and
        # pause/resume wants to keep the cook session alive.

    def reset_after_hard_stop(self):
        """
        Called from CookingPausedPage when the user cancels the cook.
        Clears pause/running state and resets the timer so the next
        cook starts from the beginning.
        """
        # Stop and hide the progress widget
        self._stop_progress()

        # Reset all timing state
        self._total_time = 0.0
        self._remaining_time = 0.0
        self._start_epoch = None
        self._running = False
        self._paused = False

    @staticmethod
    def mmss_to_seconds(mmss: str) -> float:
        minutes, seconds = map(int, mmss.split(":"))
        return minutes * 60 + seconds
