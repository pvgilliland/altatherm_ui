# click_sound.py
import os, sys, platform
from hmi_consts import ASSETS_DIR
import pygame

# One-time init of the sound system
pygame.mixer.init()


def _resource_path(rel_path: str) -> str:
    """Resolve resource paths for source or PyInstaller bundles."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)


# Preload the click sound (WAV/OGG is best, very low latency)
CLICK_SOUND = None
DONE_SOUND = None


def load_sounds(use_sound: bool = True):
    global CLICK_SOUND
    global DONE_SOUND

    if use_sound:
        CLICK_SOUND = pygame.mixer.Sound(ASSETS_DIR / "microwave_beep.wav")
        DONE_SOUND = pygame.mixer.Sound(ASSETS_DIR / "microwave_done.wav")
    else:
        CLICK_SOUND = None
        DONE_SOUND = None


def play_click():
    if CLICK_SOUND:
        CLICK_SOUND.play()  # returns immediately, non-blocking


def play_done():
    if DONE_SOUND:
        DONE_SOUND.play()  # returns immediately, non-blocking
