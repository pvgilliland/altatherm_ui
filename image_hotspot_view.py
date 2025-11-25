# image_hotspot_view.py
import os
import tkinter as tk
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from hotspots import Hotspot  # for type hints


class ImageHotspotView(ctk.CTkFrame):
    """
    Singleton view that:
      - Owns the canvas and displays the current page image.
      - Uses the current page's hotspot list to dispatch click callbacks.

    page_obj must provide:
      - image_path: str
      - hotspots: list[Hotspot]
    """

    _instance: Optional["ImageHotspotView"] = None

    IMG_WIDTH = 1280
    IMG_HEIGHT = 800

    def __init__(self, master=None, **kwargs):
        if getattr(self, "_initialized", False):
            return

        super().__init__(master, **kwargs)
        self._initialized = True

        self._current_page = None
        self._tk_img: Optional[ImageTk.PhotoImage] = None
        self._canvas_image_id: Optional[int] = None

        self.canvas = tk.Canvas(
            self,
            width=self.IMG_WIDTH,
            height=self.IMG_HEIGHT,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls, master=None, **kwargs) -> "ImageHotspotView":
        if cls._instance is None:
            if master is None:
                raise ValueError("First call to get_instance must provide master")
            cls._instance = cls(master, **kwargs)
        return cls._instance

    # ------------------------------------------------------------------
    # Page binding
    # ------------------------------------------------------------------
    def set_page(self, page_obj) -> None:
        if not hasattr(page_obj, "image_path"):
            raise AttributeError("page_obj is missing 'image_path'")
        if not hasattr(page_obj, "hotspots"):
            raise AttributeError("page_obj is missing 'hotspots'")

        img_path = page_obj.image_path
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found: {img_path}")

        pil_img = Image.open(img_path)
        if pil_img.size != (self.IMG_WIDTH, self.IMG_HEIGHT):
            raise ValueError(
                f"Image must be {self.IMG_WIDTH}x{self.IMG_HEIGHT}, got {pil_img.size}"
            )

        self._tk_img = ImageTk.PhotoImage(pil_img)
        self._current_page = page_obj

        if self._canvas_image_id is None:
            self._canvas_image_id = self.canvas.create_image(
                0, 0, anchor="nw", image=self._tk_img
            )
        else:
            self.canvas.itemconfig(self._canvas_image_id, image=self._tk_img)

    # ------------------------------------------------------------------
    # Click handling
    # ------------------------------------------------------------------
    def _on_click(self, event):
        if self._current_page is None:
            return

        x, y = event.x, event.y
        print(f"Click: {x},{y}")

        for hs in self._current_page.hotspots:
            x1, y1, x2, y2 = hs.rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                print(f"Hotspot triggered: {hs.name}")
                if hs.handler:
                    hs.handler()
                break
