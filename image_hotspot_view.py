import os
import tkinter as tk
from typing import Optional, Callable

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont
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

    Optional page_obj overlay support:
      - overlay_shapes: list[dict]
      - overlay_text: list[dict]
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

        self._overlay_ctk_image = None
        self.overlay_label = ctk.CTkLabel(
            self, text="", fg_color="black", width=200, height=200
        )
        self.overlay_label.place(x=505, y=225)
        self.overlay_label.lower()

        self.label = ctk.CTkLabel(
            self,
            text="",
            fg_color="black",
            bg_color="black",
            width=300,
            height=57,
            font=ctk.CTkFont(family="Poppins", size=32, weight="bold"),
        )
        self.label.place(x=490, y=435)
        self.label.lower()

        self.cook_time_label = ctk.CTkLabel(
            self,
            text="00:00",
            fg_color="black",
            bg_color="black",
            width=75,
            height=28,
            font=ctk.CTkFont(family="Poppins", size=28, weight="normal"),
        )
        self.cook_time_label.place(x=674, y=559)
        self.cook_time_label.lower()

        self.circular_progress: Optional[CircularProgress] = None
        self.reheat_time_control: Optional[TimeAdjustControl] = None

        drawer_img = Image.open(f"{ASSETS_DIR}/drawer.png").convert("RGBA")
        drawer_img = drawer_img.resize((48, 48))

        self._drawer_ctk_image = ctk.CTkImage(
            light_image=drawer_img,
            dark_image=drawer_img,
            size=(48, 48),
        )

        comm_img = Image.open(f"{ASSETS_DIR}/lost_comm.png").convert("RGBA")
        comm_img = comm_img.resize((48, 48))

        self._comm_ctk_image = ctk.CTkImage(
            light_image=comm_img,
            dark_image=comm_img,
            size=(48, 48),
        )

        self.door_overlay = ctk.CTkLabel(
            self,
            text=" Drawer Open",
            image=self._drawer_ctk_image,
            compound="left",
            fg_color="#000000",
            bg_color="#000000",
            text_color="white",
            font=ctk.CTkFont(family="Poppins", size=28, weight="bold"),
            width=200,
            height=45,
        )
        self.door_overlay.place(relx=0.73, rely=0.96, anchor="s")
        self.door_overlay.lower()

        self.comm_error_overlay = ctk.CTkLabel(
            self,
            text=" Lost Communication!",
            image=self._comm_ctk_image,
            compound="left",
            fg_color="#000000",
            bg_color="#000000",
            text_color="white",
            font=ctk.CTkFont(family="Poppins", size=28, weight="bold"),
            width=200,
            height=45,
        )
        self.comm_error_overlay.place(relx=0.25, rely=0.96, anchor="s")
        self.comm_error_overlay.lower()

        lock_img = Image.open(f"{ASSETS_DIR}/broken_lock.png").convert("RGBA")
        lock_img = lock_img.resize((48, 48))

        self._door_lock_ctk_image = ctk.CTkImage(
            light_image=lock_img,
            dark_image=lock_img,
            size=(48, 48),
        )

        self.door_lock_error_overlay = ctk.CTkLabel(
            self,
            text=" Door Lock Error!",
            image=self._door_lock_ctk_image,
            compound="left",
            fg_color="#000000",
            bg_color="#000000",
            text_color="white",
            font=ctk.CTkFont(family="Poppins", size=28, weight="bold"),
            width=200,
            height=45,
        )
        self.door_lock_error_overlay.place(relx=0.51, rely=0.96, anchor="s")
        self.door_lock_error_overlay.lower()

        DoorSafety.Instance().add_listener(self._on_door_change)
        DoorSafety.Instance().add_wdt_listener(self._on_lost_communication)
        DoorSafety.Instance().add_door_lock_listener(self._on_door_lock_error)

    @classmethod
    def get_instance(cls, master=None, **kwargs) -> "ImageHotspotView":
        if cls._instance is None:
            if master is None:
                raise ValueError("First call to get_instance must provide master")
            cls._instance = cls(master, **kwargs)
        return cls._instance

    def _get_font(self, font_size: int, font_weight: str = "normal"):
        candidates = []
        if font_weight == "bold":
            candidates.extend(
                [
                    "arialbd.ttf",
                    "Arial Bold.ttf",
                    "DejaVuSans-Bold.ttf",
                ]
            )
        candidates.extend(
            [
                "arial.ttf",
                "Arial.ttf",
                "DejaVuSans.ttf",
            ]
        )

        for name in candidates:
            try:
                return ImageFont.truetype(name, font_size)
            except Exception:
                pass

        return ImageFont.load_default()

    def _draw_triangle_up(self, draw, bbox, outline, fill, size=16):
        x1, y1, x2, y2 = bbox

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        s = size

        pts = [
            (cx, cy - s),  # top
            (cx - s, cy + s),  # bottom left
            (cx + s, cy + s),  # bottom right
        ]

        draw.polygon(pts, outline=outline, fill=fill)

    def _draw_triangle_down(self, draw, bbox, outline, fill, size=16):
        x1, y1, x2, y2 = bbox

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        s = size

        pts = [
            (cx - s, cy - s),
            (cx + s, cy - s),
            (cx, cy + s),
        ]

        draw.polygon(pts, outline=outline, fill=fill)

    def _apply_overlay(self, pil_img, page_obj):
        draw = ImageDraw.Draw(pil_img)

        for shape in getattr(page_obj, "overlay_shapes", []):
            kind = shape.get("kind")
            bbox = shape.get("bbox")
            outline = shape.get("outline", "white")
            fill = shape.get("fill", None)
            width = shape.get("width", 1)
            radius = shape.get("radius", 0)

            if not bbox:
                continue

            if kind == "rounded_rect":
                draw.rounded_rectangle(
                    bbox,
                    radius=radius,
                    outline=outline,
                    fill=fill,
                    width=width,
                )
            elif kind == "rect":
                draw.rectangle(
                    bbox,
                    outline=outline,
                    fill=fill,
                    width=width,
                )
            elif kind == "ellipse":
                draw.ellipse(
                    bbox,
                    outline=outline,
                    fill=fill,
                    width=width,
                )
            elif kind == "triangle_up":
                self._draw_triangle_up(
                    draw,
                    bbox,
                    outline,
                    fill,
                    shape.get("size", 16),
                )
            elif kind == "triangle_down":
                self._draw_triangle_down(
                    draw,
                    bbox,
                    outline,
                    fill,
                    shape.get("size", 16),
                )

        for item in getattr(page_obj, "overlay_text", []):
            xy = item.get("xy")
            text = item.get("text", "")
            fill = item.get("fill", "white")
            anchor = item.get("anchor", "la")
            font_size = item.get("font_size", 24)
            font_weight = item.get("font_weight", "normal")

            if not xy:
                continue

            font = self._get_font(font_size, font_weight)
            draw.text(xy, text, fill=fill, font=font, anchor=anchor)

        return pil_img

    def set_page(self, page_obj) -> None:
        if not hasattr(page_obj, "image_path"):
            raise AttributeError("page_obj is missing 'image_path'")
        if not hasattr(page_obj, "hotspots"):
            raise AttributeError("page_obj is missing 'hotspots'")

        img_path = page_obj.image_path
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found: {img_path}")

        pil_img = Image.open(img_path).convert("RGBA")
        if pil_img.size != (self.IMG_WIDTH, self.IMG_HEIGHT):
            raise ValueError(
                f"Image must be {self.IMG_WIDTH}x{self.IMG_HEIGHT}, got {pil_img.size}"
            )

        pil_img = self._apply_overlay(pil_img, page_obj)

        self._tk_img = ImageTk.PhotoImage(pil_img)
        self._current_page = page_obj

        if self._canvas_image_id is None:
            self._canvas_image_id = self.canvas.create_image(
                0, 0, anchor="nw", image=self._tk_img
            )
        else:
            self.canvas.itemconfig(self._canvas_image_id, image=self._tk_img)

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

    def set_overlay_image(
        self,
        image_path: str | None,
        name: str | None,
        cook_time: str | None,
        size=(300, 300),
    ):
        if not image_path:
            self.overlay_label.configure(image=None)
            self._overlay_ctk_image = None
            self.overlay_label.lower()
            self.cook_time_label.lower()
            self.label.lower()
            return

        if not os.path.exists(image_path):
            print(f"Overlay image not found: {image_path}")
            return

        pil_img = Image.open(image_path).convert("RGBA")
        pil_img = pil_img.resize(size)

        self._overlay_ctk_image = ctk.CTkImage(dark_image=pil_img, size=size)
        self.overlay_label.configure(image=self._overlay_ctk_image)
        self.overlay_label.lift()

        self.label.configure(text=name)
        self.label.lift()

        self.cook_time_label.configure(text=cook_time)
        self.cook_time_label.lift()

    def show_circular_progress(self):
        if self.circular_progress is None:
            self.circular_progress = CircularProgress(
                self,
                size=450,
                thickness=16,
                fg_color="#FFFFFF",
                bg_color="#000000",
                text_color="#FFFFFF",
            )
        self.circular_progress.place(relx=0.5, rely=0.51, anchor="center")

    def hide_circular_progress(self):
        if self.circular_progress is not None:
            self.circular_progress.place_forget()

    def show_center_overlay(self, image_path: str, size=(220, 220)):
        if not os.path.exists(image_path):
            print(f"Center overlay image not found: {image_path}")
            return

        if self.circular_progress is None:
            print("CircularProgress not created yet")
            return

        pil_img = Image.open(image_path).convert("RGBA")
        pil_img = pil_img.resize(size)

        self._center_overlay_ctk_image = ctk.CTkImage(dark_image=pil_img, size=size)

        if not hasattr(self, "center_overlay_label"):
            self.center_overlay_label = ctk.CTkLabel(
                self, text="", fg_color="transparent"
            )

        self.center_overlay_label.configure(image=self._center_overlay_ctk_image)
        self.center_overlay_label.place(
            relx=0.50,
            rely=0.65,
            anchor="center",
        )
        self.center_overlay_label.lift()

    def hide_center_overlay(self):
        if hasattr(self, "center_overlay_label"):
            self.center_overlay_label.place_forget()

    def show_reheat_time_control(
        self,
        initial_seconds: int = 30,
        min_seconds: int = 0,
        max_seconds: int = 120,
        on_change: Optional[Callable[[int], None]] = None,
    ) -> None:
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
            self.reheat_time_control.configure_range(
                min_seconds=min_seconds, max_seconds=max_seconds, step_seconds=15
            )
            self.reheat_time_control._on_change = on_change  # type: ignore[attr-defined]
            self.reheat_time_control.set_seconds(initial_seconds)

        self.reheat_time_control.place(relx=0.5, rely=0.72, anchor="center")
        self.reheat_time_control.lift()

    def hide_reheat_time_control(self) -> None:
        if self.reheat_time_control is not None:
            self.reheat_time_control.place_forget()

    def get_reheat_seconds(self) -> int:
        if self.reheat_time_control is None:
            return 0
        return self.reheat_time_control.get_seconds()

    def _on_door_change(self, is_open: bool):
        if is_open:
            self.door_overlay.lift()
            self.door_overlay.tkraise()
        else:
            self.door_overlay.lower()

    def _on_lost_communication(self, lostCommunication: bool):
        if lostCommunication:
            self.comm_error_overlay.lift()
            self.comm_error_overlay.tkraise()
        else:
            self.comm_error_overlay.lower()

    def _on_door_lock_error(self, is_error: bool):
        if is_error:
            self.door_lock_error_overlay.lift()
            self.door_lock_error_overlay.tkraise()
        else:
            self.door_lock_error_overlay.lower()
