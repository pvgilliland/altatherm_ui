# multipage_controller.py

import customtkinter as ctk

from image_hotspot_view import ImageHotspotView
from homepage import HomePage
from select_meal_page import SelectMealPage


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

        # If you later add more pages, create them here, e.g.:
        # from settings_page import SettingsPage
        # self.settings_page = SettingsPage(controller=self)

        self._current_page = None

    # ------------------------------------------------------------------
    # Core navigation helpers
    # ------------------------------------------------------------------
    def show_page(self, page_obj) -> None:
        """
        Generic page switch:
          - page_obj must have image_path + hotspots
        """
        self._current_page = page_obj
        self.view.set_page(page_obj)

    def show_HomePage(self) -> None:
        self.show_page(self.home_page)

    def show_SelectMealPage(self) -> None:
        self.show_page(self.select_meal_page)

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

    controller = MultiPageController(root)
    controller.show_HomePage()

    root.mainloop()
