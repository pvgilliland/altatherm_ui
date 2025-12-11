# hmi_consts.py

from pathlib import Path
import sys


__version__ = "4.0.6 ß"


# app_root(), a very common helper when you’re building Python applications
# that can run both from source and as a frozen executable (e.g. built with PyInstaller).
# _MEIPASS is set when built with PyInstaller.
def app_root() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


ROOT_DIR = app_root()
ASSETS_DIR = ROOT_DIR / "assets"
SETTINGS_DIR = ROOT_DIR / "settings"
PROGRAMS_DIR = ROOT_DIR / "programs"

SETTINGS_FILE = SETTINGS_DIR / "settings.alt"


class HMIColors:
    BORDER_COLOR = "#E0E0F2"
    DISABLED_BORDER_COLOR = "#BDBDBD"
    DIALOG_BG_COLOR = "#FEFEFE"
    BTN_COLOR = "#FAFAFF"
    BTN_HOVER_COLOR = "#F0F0FF"
    TEXT_COLOR = "#6750A4"
    ROW_HIGHLIGHT = "#C0C3EE"
    TEXTBOX_BG_COLOR = "#F7F7FF"
    color_blue = "#89C8F8"
    color_fg = "#DAFAFF"
    color_numbers = "#3776C3"


class HMISizePos:
    """
    Resolution profiles + scaling helpers.
    Baseline design is 800x480; everything scales from there.
    """

    # Baseline
    _BASE_W = 800
    _BASE_H = 480

    # Current resolution (set by set_resolution)
    SCREEN_W = 800
    SCREEN_H = 480
    SCREEN_RES = "800x480"

    # Scale factors
    SX = 1.0  # width scale
    SY = 1.0  # height scale
    SCALE = 1.0  # min(SX, SY), good for fonts/radii

    # Common base sizes
    BTN_WIDTH_BASE = 220
    BTN_HEIGHT_BASE = 64
    PADDING_BASE = 16
    GAP_BASE = 12
    TITLE_SIZE_BASE = 28
    TEXT_SIZE_BASE = 16
    ICON_SIZE_BASE = 24

    # Effective sizes (computed in set_resolution)
    BTN_WIDTH = BTN_WIDTH_BASE
    BTN_HEIGHT = BTN_HEIGHT_BASE
    PADDING = PADDING_BASE
    GAP = GAP_BASE
    TITLE_SIZE = TITLE_SIZE_BASE
    TEXT_SIZE = TEXT_SIZE_BASE
    ICON_SIZE = ICON_SIZE_BASE

    _PROFILES = {
        "800x480": {"w": 800, "h": 480},
        "1024x600": {"w": 1024, "h": 600},
        "1280x800": {"w": 1280, "h": 800},
    }

    @classmethod
    def set_resolution(cls, res: str = "800x480"):
        if res not in cls._PROFILES:
            res = "800x480"
        cls.SCREEN_W = cls._PROFILES[res]["w"]
        cls.SCREEN_H = cls._PROFILES[res]["h"]
        cls.SCREEN_RES = f"{cls.SCREEN_W}x{cls.SCREEN_H}"

        cls.SX = cls.SCREEN_W / cls._BASE_W
        cls.SY = cls.SCREEN_H / cls._BASE_H
        cls.SCALE = min(cls.SX, cls.SY)

        # Derive commonly used sizes
        cls.BTN_WIDTH = int(cls.BTN_WIDTH_BASE * cls.SX)
        cls.BTN_HEIGHT = int(cls.BTN_HEIGHT_BASE * cls.SY)
        cls.PADDING = int(cls.PADDING_BASE * cls.SCALE)
        cls.GAP = int(cls.GAP_BASE * cls.SCALE)
        cls.TITLE_SIZE = max(10, int(cls.TITLE_SIZE_BASE * cls.SCALE))
        cls.TEXT_SIZE = max(8, int(cls.TEXT_SIZE_BASE * cls.SCALE))
        cls.ICON_SIZE = max(12, int(cls.ICON_SIZE_BASE * cls.SCALE))

    # --- scaling helpers your pages call ---
    @classmethod
    def s(cls, v: int | float) -> int:
        """Uniform scale (fonts, radii)."""
        return max(1, int(v * cls.SCALE))

    @classmethod
    def sx(cls, v: int | float) -> int:
        """Scale for widths/x paddings."""
        return max(1, int(v * cls.SX))

    @classmethod
    def sy(cls, v: int | float) -> int:
        """Scale for heights/y paddings."""
        return max(1, int(v * cls.SY))


class HMISerial:
    BAUD_RATE = 115200
    DATABITS = 8
    STOPBITS = 1
    PARITY = "N"
