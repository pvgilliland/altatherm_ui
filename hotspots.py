# hotspots.py
from dataclasses import dataclass
from typing import Callable, Tuple, List

Rect = Tuple[int, int, int, int]
HotspotHandler = Callable[[], None]


@dataclass
class Hotspot:
    name: str
    rect: Rect  # (x1, y1, x2, y2)
    handler: HotspotHandler
