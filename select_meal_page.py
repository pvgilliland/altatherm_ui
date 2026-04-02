import os
from typing import List, Sequence, Dict, Any

from hotspots import Hotspot


class SelectMealPage:
    """
    Select Meal page with visible scrolling metadata.

    This page now provides:
      - image_path
      - hotspots
      - overlay_shapes
      - overlay_text

    ImageHotspotView must render overlay_shapes and overlay_text.
    """

    IMAGE_NAME = "01SelectMealPage.png"

    GRID_COLS = 3
    VISIBLE_ROWS = 2

    TOP_LEFT_X = 194
    TOP_LEFT_Y = 223
    BTN_WIDTH = 263
    BTN_HEIGHT = 190
    BTN_PADDING_X = 34
    BTN_PADDING_Y = 63

    BACK_RECT = (84, 642, 154, 707)
    QUESTION_RECT = (1110, 637, 1205, 718)

    SCROLL_TRACK_RECT = (1190, 215, 1230, 590)
    SCROLL_UP_RECT = (1170, 165, 1250, 240)
    SCROLL_DOWN_RECT = (1170, 566, 1250, 641)

    def __init__(
        self,
        controller=None,
        from_info: bool = False,
        scroll_row: int = 0,
        meal_labels: Sequence[str] | None = None,
    ):
        self.controller = controller
        self.from_info = from_info
        self.meal_index: int = -1
        self.scroll_row = max(0, int(scroll_row))

        self.meal_labels: List[str] = list(
            meal_labels
            if meal_labels is not None
            else [
                "Item 1",
                "Item 2",
                "Item 3",
                "Item 4",
                "Item 5",
                "Reheat",
                "Item 7",
                "Item 8",
                "Item 9",
                "Item 10",
                "Item 11",
                "Item 12",
            ]
        )

        here = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        assets_dir = os.path.join(here, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        self.image_path = os.path.join(assets_dir, self.IMAGE_NAME)
        self.reheat_image_path = os.path.join(assets_dir, "Reheat.png")

        self.hotspots: List[Hotspot] = []
        self.overlay_shapes: List[Dict[str, Any]] = []
        self.overlay_text: List[Dict[str, Any]] = []

        self._rebuild()

    @property
    def meal_count(self) -> int:
        return len(self.meal_labels)

    @property
    def total_rows(self) -> int:
        return (self.meal_count + self.GRID_COLS - 1) // self.GRID_COLS

    @property
    def max_scroll_row(self) -> int:
        return max(0, self.total_rows - self.VISIBLE_ROWS)

    def _clamp_scroll_row(self) -> None:
        self.scroll_row = max(0, min(self.scroll_row, self.max_scroll_row))

    def _rebuild(self) -> None:
        self._clamp_scroll_row()
        self.hotspots = []
        self.overlay_shapes = []
        self.overlay_text = []

        first_visible_row = self.scroll_row
        last_visible_row = self.scroll_row + self.VISIBLE_ROWS - 1

        for meal_index in range(self.meal_count):
            row = meal_index // self.GRID_COLS
            col = meal_index % self.GRID_COLS

            if row < first_visible_row or row > last_visible_row:
                continue

            visible_row = row - self.scroll_row

            x1 = self.TOP_LEFT_X + col * (self.BTN_WIDTH + self.BTN_PADDING_X)
            y1 = self.TOP_LEFT_Y + visible_row * (self.BTN_HEIGHT + self.BTN_PADDING_Y)
            x2 = x1 + self.BTN_WIDTH
            y2 = y1 + self.BTN_HEIGHT

            # Clickable meal hotspot
            self.hotspots.append(
                Hotspot(
                    f"meal{meal_index}",
                    (x1, y1, x2, y2),
                    lambda meal=meal_index: self.on_meal_clicked(meal),
                )
            )

            # Visible rounded card border
            self.overlay_shapes.append(
                {
                    "kind": "rounded_rect",
                    "bbox": (x1, y1, x2, y2),
                    "outline": "#9C6615",
                    "width": 4,
                    "radius": 22,
                }
            )

            # Simple circular icon placeholder
            cx = x1 + self.BTN_WIDTH // 2
            cy = y1 + 50
            r = 90
            if meal_index != 5:
                self.overlay_shapes.append(
                    {
                        "kind": "ellipse",
                        "bbox": (cx - r, cy - r, cx + r, cy + r),
                        "outline": "#F2F2F2",
                        "fill": "#000000",
                        "width": 5,
                    }
                )

            if meal_index == 5 and os.path.exists(self.reheat_image_path):
                sz = 108
                self.overlay_shapes.append(
                    {
                        "kind": "image",
                        "bbox": (cx - sz, cy - sz, cx + sz, cy + sz),
                        "image_path": self.reheat_image_path,
                    }
                )
            else:
                self.overlay_text.append(
                    {
                        "xy": (cx, cy),
                        "text": "Food Image Here",
                        "fill": "#888888",
                        "anchor": "mm",
                        "font_size": 16,
                        "font_weight": "normal",
                    }
                )

            # Meal label
            self.overlay_text.append(
                {
                    "xy": (x1 + self.BTN_WIDTH // 2, y2 - 24),
                    "text": self.meal_labels[meal_index],
                    "fill": "#F2F2F2",
                    "anchor": "ms",
                    "font_size": 26,
                    "font_weight": "bold",
                }
            )

        # Always-visible nav hotspots
        self.hotspots.append(Hotspot("back", self.BACK_RECT, self.on_back_clicked))
        self.hotspots.append(
            Hotspot("question", self.QUESTION_RECT, self.on_question_clicked)
        )

        # Visible scrollbar only if needed
        if self.max_scroll_row > 0:
            tx1, ty1, tx2, ty2 = self.SCROLL_TRACK_RECT

            self.overlay_shapes.append(
                {
                    "kind": "rounded_rect",
                    "bbox": self.SCROLL_TRACK_RECT,
                    "outline": "#8A5A12",
                    "fill": "#1A1A1A",
                    "width": 2,
                    "radius": 12,
                }
            )

            track_h = ty2 - ty1
            thumb_h = max(56, int(track_h * self.VISIBLE_ROWS / self.total_rows))
            travel = track_h - thumb_h
            thumb_y = (
                ty1
                if self.max_scroll_row == 0
                else ty1 + int(travel * (self.scroll_row / self.max_scroll_row))
            )

            self.overlay_shapes.append(
                {
                    "kind": "rounded_rect",
                    "bbox": (tx1 + 4, thumb_y, tx2 - 4, thumb_y + thumb_h),
                    "outline": "#444444",
                    "fill": "#2A2A2A",
                    "width": 1,
                    "radius": 10,
                }
            )

            # SMALL GOLD CHEVRON UP
            self.overlay_shapes.append(
                {
                    "kind": "triangle_up",
                    "bbox": self.SCROLL_UP_RECT,
                    "outline": "#8A5A12",
                    "fill": "#8A5A12",
                    "width": 4,
                    "size": 20,  # controls how small it is
                }
            )

            # SMALL GOLD CHEVRON DOWN
            self.overlay_shapes.append(
                {
                    "kind": "triangle_down",
                    "bbox": self.SCROLL_DOWN_RECT,
                    "outline": "#8A5A12",
                    "fill": "#8A5A12",
                    "width": 4,
                    "size": 20,
                }
            )

            if self.scroll_row > 0:
                self.hotspots.append(
                    Hotspot("scroll_up", self.SCROLL_UP_RECT, self.on_scroll_up_clicked)
                )

            if self.scroll_row < self.max_scroll_row:
                self.hotspots.append(
                    Hotspot(
                        "scroll_down",
                        self.SCROLL_DOWN_RECT,
                        self.on_scroll_down_clicked,
                    )
                )

    def _show_self_again(self) -> None:
        if self.controller:
            self.controller.show_SelectMealPage(
                from_info=self.from_info,
                scroll_row=self.scroll_row,
                meal_labels=self.meal_labels,
            )

    def on_meal_clicked(self, meal_index: int):
        print(f"on_meal_clicked {meal_index}")
        self.meal_index = meal_index

        if not self.controller:
            return

        if self.from_info:
            self.controller.show_StartCookingConfirmation()
        else:
            self.controller.show_PrepareForCookingPage1(from_info=False)

    def on_back_clicked(self):
        print("on_back_clicked")
        if self.controller:
            self.controller.show_HomePage()

    def on_question_clicked(self):
        print("on_question_clicked")
        if self.controller:
            self.controller.show_PrepareForCookingPage1(from_info=True)

    def on_scroll_up_clicked(self):
        print("on_scroll_up_clicked")
        if self.scroll_row > 0:
            self.scroll_row -= 1
            self._show_self_again()

    def on_scroll_down_clicked(self):
        print("on_scroll_down_clicked")
        if self.scroll_row < self.max_scroll_row:
            self.scroll_row += 1
            self._show_self_again()
