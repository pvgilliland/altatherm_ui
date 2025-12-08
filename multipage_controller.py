# multipage_controller.py

import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import logging

from typing import Optional

from image_hotspot_view import ImageHotspotView
from homepage import HomePage
from select_meal_page import SelectMealPage
from prepare_for_cooking1 import PrepareForCookingPage1
from prepare_for_cooking2 import PrepareForCookingPage2
from start_cooking_confirmation import StartCookingConfirmation
from SerialService import SerialService
from DoorSafety import DoorSafety
from hmi_consts import ASSETS_DIR, SETTINGS_DIR, PROGRAMS_DIR, HMISizePos, __version__
from hmi_logger import setup_logging
import oven_state


logger = logging.getLogger("MultiPageController")


class MultiPageController:
    """
    MultiPageController
    -------------------
    Central controller that:
      - Owns the CTk root window
      - Owns the singleton ImageHotspotView
      - Creates and manages page models (HomePage, etc.)
      - Exposes show_* methods for navigation (called by page callbacks)
    """

    def __init__(self, root: ctk.CTk):
        self.root = root

        # Create the singleton hotspot view inside the root
        self.view = ImageHotspotView.get_instance(root)
        self.view.pack(fill="both", expand=True)

        # --- create/start shared serial service (pages access via controller.serial) ---
        self.serial = SerialService(
            tk_root=root
        )  # optionally: port_hint="COM5" or "ACM"
        try:
            self.serial.start()
        except Exception as e:
            print("Serial start failed:", e)

        # need to pass CTk root to make the DoorSafety model UI thread safe
        DoorSafety.Instance().set_ui_root(root)

        self.is_admin = False  # <--- global admin flag lives here

        # Shared data (controller owns defaults)
        self.shared_data = {
            "name": ctk.StringVar(),
            "age": ctk.StringVar(),
            "time_page": {
                "minute": ctk.IntVar(value=1),
                "second": ctk.IntVar(value=1),
            },
            "time_power_page": {
                "minute": ctk.IntVar(value=0),
                "second": ctk.IntVar(value=10),
                "power": ctk.IntVar(value=50),
            },
        }

        # --- track pending fan-off timer ---
        self._fan_off_timer = None

        # Cache icons for SequenceProgramPage
        self.zone_icons = []
        for i in range(8):
            icon = Image.open(f"{ASSETS_DIR}/Zone{i+1}.png").resize((24, 24))
            self.zone_icons.append(
                ctk.CTkImage(light_image=icon, dark_image=icon, size=(24, 24))
            )

        # --- Create pages and give them a reference to this controller ---
        self.home_page = HomePage(controller=self)
        self.select_meal_page = SelectMealPage(controller=self)
        self.prepare_for_cooking_page1 = PrepareForCookingPage1(controller=self)
        self.prepare_for_cooking_page2 = PrepareForCookingPage2(controller=self)
        self.start_cooking_confirm_page = StartCookingConfirmation(controller=self)

        self._current_page = None

        # after self.serial.start(), give the controller COM time to be ready to talk to
        self.after(2000, self.serial_get_door_switch)

        setup_logging("hmi")
        logger.info(f"HMI Started {[__version__]}")

    def after(self, delay_ms: int, callback, *args):
        """
        Proxy to the Tk root's .after(), so pages and controller
        can call controller.after(...) like a widget.
        """
        return self.root.after(delay_ms, callback, *args)

    def after_cancel(self, after_id):
        """
        Proxy to the Tk root's .after_cancel() for cancelling timers.
        """
        return self.root.after_cancel(after_id)

    # ------------------------------------------------------------------
    # Core navigation helpers
    # ------------------------------------------------------------------
    def show_page(self, page_obj) -> None:
        """
        Generic page switch with lifecycle hooks:
        - Calls on_hide() on the previous page (if it exists)
        - Calls on_show() on the new page (if it exists)
        - Updates the ImageHotspotView
        """
        # 1. Call on_hide on the current page (if available)
        if self._current_page and hasattr(self._current_page, "on_hide"):
            try:
                self._current_page.on_hide()
            except Exception as e:
                print(f"WARNING: on_hide() failed on {self._current_page}: {e}")

        # 2. Call on_show on the new page (if available)
        if hasattr(page_obj, "on_show"):
            try:
                page_obj.on_show()
            except TypeError:
                # Some pages (like StartCookingConfirmation) expect parameters
                # They will call on_show manually before show_page()
                pass

        # 3. Switch pages visually
        self._current_page = page_obj
        self.view.set_page(page_obj)

    def show_HomePage(self) -> None:
        self.show_page(self.home_page)

    def show_SelectMealPage(self) -> None:
        self.show_page(self.select_meal_page)

    def show_PrepareForCookingPage1(self) -> None:
        self.show_page(self.prepare_for_cooking_page1)

    def show_PrepareForCookingPage2(self) -> None:
        self.show_page(self.prepare_for_cooking_page2)

    def show_StartCookingConfirmation(self) -> None:
        self.start_cooking_confirm_page.on_show(self.select_meal_page.meal_index)
        self.show_page(self.start_cooking_confirm_page)

    # ------------------------------------------------------------------
    # Serial commands
    # ------------------------------------------------------------------

    def serial_get_door_switch(self):
        print("cmd = D self.serial.send(cmd)")
        cmd = "D"
        self.serial.send(cmd)

    # ------------------------------------------------------------------
    # Application-level actions (called by pages via controller)
    # ------------------------------------------------------------------
    def exit_app(self) -> None:
        """Cleanly shut down the application."""
        self.root.destroy()


# ----------------------------------------------------------------------
# Self-test / harness
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1280x800")

    # root.overrideredirect(True) # remove the titlebar

    controller = MultiPageController(root)
    controller.show_HomePage()

    root.mainloop()
