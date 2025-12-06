# multipage_controller.py

import customtkinter as ctk

from image_hotspot_view import ImageHotspotView
from homepage import HomePage
from select_meal_page import SelectMealPage
from prepare_for_cooking1 import PrepareForCookingPage1
from prepare_for_cooking2 import PrepareForCookingPage2
from start_cooking_confirmation import StartCookingConfirmation


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

        # --- Create pages and give them a reference to this controller ---
        self.home_page = HomePage(controller=self)
        self.select_meal_page = SelectMealPage(controller=self)
        self.prepare_for_cooking_page1 = PrepareForCookingPage1(controller=self)
        self.prepare_for_cooking_page2 = PrepareForCookingPage2(controller=self)
        self.start_cooking_confirm_page = StartCookingConfirmation(controller=self)

        # If you later add more pages, create them here, e.g.:
        # from settings_page import SettingsPage
        # self.settings_page = SettingsPage(controller=self)

        self._current_page = None

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

    # Example for future pages:
    # def show_SettingsPage(self) -> None:
    #     self.show_page(self.settings_page)

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
