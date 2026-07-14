from typing import List

from hotspots import Hotspot
from DoorSafety import DoorSafety

import os
from hmi_consts import ASSETS_DIR


class ReheatPage:
    """
    Dedicated Reheat page.

    Uses:
        reheat_page.png

    Similar behavior to StartCookingConfirmation,
    but:
        - standalone implementation
        - no meal image overlay
        - always operates in reheat mode
    """

    IMAGE_NAME = "reheat_page.png"

    def __init__(self, controller):
        self.controller = controller

        self.reheat_seconds = 0

        self.image_path = os.path.join(ASSETS_DIR, self.IMAGE_NAME)

        self.hotspots: List[Hotspot] = [
            Hotspot(
                "back",
                (84, 642, 154, 707),
                self.on_back_clicked,
            ),
            Hotspot(
                "start",
                (490, 641, 785, 716),
                self.on_start_clicked,
            ),
            Hotspot(
                "home",
                (1138, 43, 1205, 98),
                self.on_home_clicked,
            ),
            Hotspot(
                "question",
                (1115, 634, 1212, 722),
                self.on_question_clicked,
            ),
        ]

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_back_clicked(self):
        print("ReheatPage: Back clicked")

        if not self.controller:
            return

        self.controller.show_SelectMealPage()

    def on_home_clicked(self):
        print("ReheatPage: Home clicked")

        if not self.controller:
            return

        self.controller.show_HomePage()

    def on_question_clicked(self):
        print("ReheatPage: Question clicked. What to show here?")
        if not self.controller:
            return

    def on_start_clicked(self):
        print("ReheatPage: Start clicked")

        # ------------------------------------------------------------
        # BLOCK START IF DOOR IS OPEN
        # ------------------------------------------------------------

        if DoorSafety.Instance().is_open():
            print("[ReheatPage] Door is open → Start disabled")
            return

        # ------------------------------------------------------------
        # GET REHEAT TIME
        # ------------------------------------------------------------

        view = getattr(self.controller, "view", None)

        reheat_secs = 0

        if view and hasattr(view, "get_reheat_seconds"):
            try:
                reheat_secs = int(view.get_reheat_seconds() or 0)
            except (TypeError, ValueError):
                reheat_secs = 0

        reheat_secs = max(0, reheat_secs)

        # ------------------------------------------------------------
        # BLOCK START IF TIME IS ZERO
        # ------------------------------------------------------------

        if reheat_secs == 0:
            print("[ReheatPage] Reheat time = 0 → ignoring Start click")

            if view and hasattr(view, "show_reheat_time_attention"):
                view.show_reheat_time_attention()

            return

        # ------------------------------------------------------------
        # SAVE REHEAT TIME
        # ------------------------------------------------------------

        self.controller.shared_data["reheat_seconds"] = reheat_secs
        self.controller.shared_data["show_reheat_time_attention"] = False

        # ------------------------------------------------------------
        # CLEAR WARNINGS
        # ------------------------------------------------------------

        try:
            if view and hasattr(view, "_on_door_lock_error"):
                view._on_door_lock_error(False)

            if view and hasattr(view, "hide_reheat_time_attention"):
                view.hide_reheat_time_attention()

        except Exception:
            pass

        # ------------------------------------------------------------
        # START COOKING
        # ------------------------------------------------------------

        self.controller.show_CookingPage(5)

    # ------------------------------------------------------------------
    # Page Lifecycle
    # ------------------------------------------------------------------

    def on_show(self):
        print("ReheatPage: on_show")

        view = getattr(self.controller, "view", None)

        if not view:
            return

        # ------------------------------------------------------------
        # NO FOOD IMAGE OVERLAY
        # ------------------------------------------------------------

        if hasattr(view, "set_overlay_image"):
            view.set_overlay_image(None, None, None)

        # ------------------------------------------------------------
        # SHOW REHEAT TIME CONTROL
        # ------------------------------------------------------------

        if hasattr(view, "show_reheat_time_control"):
            view.show_reheat_time_control(
                initial_seconds=0,
                min_seconds=0,
                max_seconds=120,
                on_change=self.on_reheat_time_changed,
                font_size=42,
            )

        # ------------------------------------------------------------
        # SHOW/HIDE ATTENTION
        # ------------------------------------------------------------

        if self.controller.shared_data.get(
            "show_reheat_time_attention",
            False,
        ):
            if hasattr(view, "show_reheat_time_attention"):
                view.show_reheat_time_attention()
        else:
            if hasattr(view, "hide_reheat_time_attention"):
                view.hide_reheat_time_attention()

    def on_hide(self):
        print("ReheatPage: on_hide")

        view = getattr(self.controller, "view", None)

        if not view:
            return

        if hasattr(view, "hide_reheat_time_control"):
            view.hide_reheat_time_control()

        if hasattr(view, "hide_reheat_time_attention"):
            view.hide_reheat_time_attention()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def on_reheat_time_changed(self, seconds: int):
        self.reheat_seconds = seconds

        print(f"Reheat time changed: {seconds}")
