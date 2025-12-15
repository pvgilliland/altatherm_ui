# image_hotspot_view.py
import os
import tkinter as tk
from typing import Optional, Callable

import customtkinter as ctk
from PIL import Image, ImageTk
from hmi_consts import ASSETS_DIR

from hotspots import Hotspot  # for type hints
from CircularProgress import CircularProgress
from time_adjust_control import TimeAdjustControl
from hmi_consts import HMIColors
from DoorSafety import DoorSafety


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

        super().__init__(master, fg_color=HMIColors.color_fg, **kwargs)
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
            bg=HMIColors.color_fg,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)

        # --- Overlay image widget (for meal preview etc.) ---
        self._overlay_ctk_image = None  # keeps reference
        self.overlay_label = ctk.CTkLabel(
            self, text="", fg_color="black", width=200, height=200
        )
        # Place it where the golden rectangle is (adjust as needed)
        self.overlay_label.place(x=505, y=225)
        self.overlay_label.lower()  # keep it above canvas but below hotspots, if any

        self.label = ctk.CTkLabel(
            self,
            text="",
            fg_color="black",
            bg_color="black",
            width=300,
            height=57,
            font=ctk.CTkFont(family="Poppins", size=32, weight="bold"),
        )
        # Place it where the golden rectangle is (adjust as needed)
        self.label.place(x=490, y=435)
        self.label.lower()  # keep it above canvas but below hotspots, if any

        self.cook_time_label = ctk.CTkLabel(
            self,
            text="00:00",
            fg_color="black",
            bg_color="black",
            width=75,
            height=28,
            font=ctk.CTkFont(family="Poppins", size=28, weight="normal"),
        )
        # Place it where the golden rectangle is (adjust as needed)
        self.cook_time_label.place(x=674, y=559)
        self.cook_time_label.lower()  # keep it above canvas but below hotspots, if any

        # --- CircularProgress overlay (used by CookingPage) ---
        self.circular_progress: Optional[CircularProgress] = None

        # --- Horizontal Reheat Time control (overlay) ---
        self.reheat_time_control: Optional[TimeAdjustControl] = None

        drawer_img = Image.open(f"{ASSETS_DIR}/drawer.png").convert("RGBA")
        drawer_img = drawer_img.resize((48, 48))  # adjust size as needed

        self._drawer_ctk_image = ctk.CTkImage(
            light_image=drawer_img,
            dark_image=drawer_img,
            size=(48, 48),
        )

        # --- Door Open overlay (GLOBAL ie all screens) ---
        self.door_overlay = ctk.CTkLabel(
            self,
            text=" Drawer Open",
            image=self._drawer_ctk_image,
            compound="left",  # <-- key line
            fg_color="#000000",
            bg_color="#000000",
            text_color="white",
            # corner_radius=12,
            font=ctk.CTkFont(family="Poppins", size=28, weight="bold"),
            width=200,
            height=45,
        )
        # Top-center, above everything
        self.door_overlay.place(relx=0.73, rely=0.96, anchor="s")
        self.door_overlay.lower()  # hidden by default

        # Listen for door open status change
        DoorSafety.Instance().add_listener(self._on_door_change)

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

    # ------------------------------------------------------------------
    # Overlay helpers
    # ------------------------------------------------------------------
    def set_overlay_image(
        self,
        image_path: str | None,
        name: str | None,
        cook_time: str | None,
        size=(300, 300),
    ):
        """
        Shows or hides an overlay image on top of the base page image.
        image_path = None → hides the overlay.
        """
        if not image_path:
            self.overlay_label.configure(image=None)
            self._overlay_ctk_image = None
            self.overlay_label.lower()  # hide the label if there is no image
            self.cook_time_label.lower()  # hide the cook time label
            self.label.lower()
            return

        if not os.path.exists(image_path):
            print(f"Overlay image not found: {image_path}")
            return

        from PIL import Image

        pil_img = Image.open(image_path).convert("RGBA")
        pil_img = pil_img.resize(size)

        self._overlay_ctk_image = ctk.CTkImage(dark_image=pil_img, size=size)
        self.overlay_label.configure(image=self._overlay_ctk_image)
        self.overlay_label.lift()  # keep it above canvas but below hotspots, if any

        self.label.configure(text=name)
        self.label.lift()

        self.cook_time_label.configure(text=cook_time)
        self.cook_time_label.lift()

    # ------------------------------------------------------------------
    # CircularProgress overlay API
    # ------------------------------------------------------------------
    def show_circular_progress(self):
        """
        Ensure the CircularProgress widget exists and make it visible,
        centered in the main content area (tuned for 1280x800).
        """
        if self.circular_progress is None:
            self.circular_progress = CircularProgress(
                self,
                size=450,
                thickness=16,
                fg_color="#FFFFFF",  # AltaTherm gold
                bg_color="#000000",
                text_color="#FFFFFF",
            )
        # Centered slightly above the vertical middle to leave room for bottom buttons
        self.circular_progress.place(relx=0.5, rely=0.51, anchor="center")
        # self.circular_progress.lift()  # type: ignore[arg-type]

    def hide_circular_progress(self):
        """Hide (but do not destroy) the CircularProgress widget."""
        if self.circular_progress is not None:
            self.circular_progress.place_forget()

    def show_center_overlay(self, image_path: str, size=(220, 220)):
        """
        Show an overlay image centered inside the CircularProgress widget.
        """
        if not os.path.exists(image_path):
            print(f"Center overlay image not found: {image_path}")
            return

        if self.circular_progress is None:
            print("CircularProgress not created yet")
            return

        # Load and resize image
        pil_img = Image.open(image_path).convert("RGBA")
        pil_img = pil_img.resize(size)

        self._center_overlay_ctk_image = ctk.CTkImage(dark_image=pil_img, size=size)

        # Create label if needed
        if not hasattr(self, "center_overlay_label"):
            self.center_overlay_label = ctk.CTkLabel(
                self, text="", fg_color="transparent"
            )

        # Position overlay relative to the circular progress center
        self.center_overlay_label.configure(image=self._center_overlay_ctk_image)
        self.center_overlay_label.place(
            relx=0.50,
            rely=0.65,  # matches the circular_progress placement
            anchor="center",
        )
        self.center_overlay_label.lift()

    def hide_center_overlay(self):
        if hasattr(self, "center_overlay_label"):
            self.center_overlay_label.place_forget()

    # ------------------------------------------------------------------
    # Reheat time control overlay API
    # ------------------------------------------------------------------
    def show_reheat_time_control(
        self,
        initial_seconds: int = 30,
        min_seconds: int = 0,
        max_seconds: int = 120,
        on_change: Optional[Callable[[int], None]] = None,
    ) -> None:
        """
        Show the horizontal +/- 15 sec time control near the bottom center.
        """
        if self.reheat_time_control is None:
            self.reheat_time_control = TimeAdjustControl(
                self,
                label_text="Reheat Time:",
                step_seconds=15,
                min_seconds=min_seconds,
                max_seconds=max_seconds,
                initial_seconds=initial_seconds,
                on_change=on_change,
            )
        else:
            # Update range & callback and current value
            self.reheat_time_control.configure_range(
                min_seconds=min_seconds, max_seconds=max_seconds, step_seconds=15
            )
            self.reheat_time_control._on_change = on_change  # type: ignore[attr-defined]
            self.reheat_time_control.set_seconds(initial_seconds)

        # Place roughly where your mockup shows the control
        self.reheat_time_control.place(relx=0.5, rely=0.72, anchor="center")
        self.reheat_time_control.lift()

    def hide_reheat_time_control(self) -> None:
        """
        Hide (but do not destroy) the reheat time control.
        """
        if self.reheat_time_control is not None:
            self.reheat_time_control.place_forget()

    def get_reheat_seconds(self) -> int:
        """
        Convenience accessor for current reheat seconds.
        """
        if self.reheat_time_control is None:
            return 0
        return self.reheat_time_control.get_seconds()

    def _on_door_change(self, is_open: bool):
        if is_open:
            self.door_overlay.lift()
            self.door_overlay.tkraise()  # Ensure overlay always wins z-order
        else:
            self.door_overlay.lower()
