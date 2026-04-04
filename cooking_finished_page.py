import os
from typing import List
import customtkinter as ctk
from PIL import Image, ImageDraw
from hotspots import Hotspot


class CookingFinishedPage:
    """
    Page model:
      - uses homepage.png
      - defines three hotspots and their callbacks
      - auto-returns to HomePage after 5 seconds
    """

    IMAGE_NAME = "06CookingFinished.png"
    AUTO_RETURN_MS = 5000

    def __init__(self, controller=None):
        self.controller = controller
        self._auto_return_after_id = None

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)

        self.hotspots: List[Hotspot] = [
            Hotspot("close", (1122, 644, 1199, 711), self.on_close_clicked),
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def on_show(self):
        self._cancel_auto_return()

        if self.controller:
            self._auto_return_after_id = self.controller.after(
                self.AUTO_RETURN_MS,
                self._go_home,
            )

    def on_hide(self):
        self._cancel_auto_return()

    def _cancel_auto_return(self):
        if self.controller and self._auto_return_after_id is not None:
            try:
                self.controller.after_cancel(self._auto_return_after_id)
            except Exception:
                pass
        self._auto_return_after_id = None

    def _go_home(self):
        self._auto_return_after_id = None
        if self.controller:
            self.controller.show_HomePage()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def on_close_clicked(self):
        self._cancel_auto_return()
        if self.controller:
            self.controller.show_HomePage()
