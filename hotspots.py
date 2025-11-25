# hotspots.py
from dataclasses import dataclass
from typing import Callable, Tuple, List

Rect = Tuple[int, int, int, int]
HotspotHandler = Callable[[], None]


# @dataclass is a Python decorator (from the dataclasses module) that
# automatically generates boilerplate code for classes that primarily store data.
# When you put @dataclass above a class, Python will automatically create hidden:
# ✔ __init__() – initializer
# ✔ __repr__() – readable string representation
# ✔ __eq__() – equality comparison


@dataclass
class Hotspot:
    name: str
    rect: Rect  # (x1, y1, x2, y2)
    handler: HotspotHandler
