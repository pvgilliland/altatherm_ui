# software_update_page.py

from __future__ import annotations

import os
import shutil
import zipfile
import tempfile
import threading
import traceback
from pathlib import Path

import requests
import customtkinter as ctk

# This must point directly to the JSON file, not just the folder.
UPDATE_LIST_URL = "https://tallywatcherhrc.com/altatherm_hmi_updates/index.json"


# -----------------------------------------------------------------------------
# TEST PATHS
# -----------------------------------------------------------------------------
# These paths are safe for testing on Windows and Raspberry Pi.
# tempfile.gettempdir() returns something like:
#   Windows: C:\Users\<user>\AppData\Local\Temp
#   Linux/Raspberry Pi: /tmp
#
# For the real Raspberry Pi install, replace HMI_INSTALL_FOLDER with your real
# HMI application folder, for example:
#   HMI_INSTALL_FOLDER = Path("/home/pvgilliland/projects/altatherm_ui")
# -----------------------------------------------------------------------------
BASE_TEMP_FOLDER = Path("/temp")

HMI_INSTALL_FOLDER = BASE_TEMP_FOLDER / "altatherm_ui"
BACKUP_FOLDER = BASE_TEMP_FOLDER / "hmi_backups"
DOWNLOAD_FOLDER = BASE_TEMP_FOLDER / "hmi_downloads"


class SoftwareUpdatePage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, fg_color="#DAFAFF")

        self.controller = controller
        self.selected_update: dict | None = None
        self.update_buttons: list[ctk.CTkButton] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Software Update",
            font=("Arial", 24, "bold"),
            text_color="#89C8F8",
        ).grid(row=0, column=0, pady=20)

        self.file_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Available Update Files",
            label_text_color="#89C8F8",
            width=760,
            height=280,
        )
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self,
            text="Loading update list...",
            font=("Arial", 18, "bold"),
            text_color="#3776C3",
            wraplength=760,
        )
        self.status_label.grid(row=2, column=0, pady=10)

        button_frame = ctk.CTkFrame(self, fg_color="#DAFAFF")
        button_frame.grid(row=3, column=0, pady=10)

        self.refresh_button = ctk.CTkButton(
            button_frame,
            text="Refresh",
            width=160,
            height=55,
            command=self.load_updates_threaded,
        )
        self.refresh_button.grid(row=0, column=0, padx=10)

        self.update_button = ctk.CTkButton(
            button_frame,
            text="Update",
            width=160,
            height=55,
            command=self.run_update_threaded,
        )
        self.update_button.grid(row=0, column=1, padx=10)

        self.back_button = ctk.CTkButton(
            button_frame,
            text="Back",
            width=160,
            height=55,
            command=self.go_back,
        )
        self.back_button.grid(row=0, column=2, padx=10)

        self.load_updates_threaded()

    # -------------------------------------------------------------------------
    # UI helpers
    # -------------------------------------------------------------------------
    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.refresh_button.configure(state=state)
        self.update_button.configure(state=state)
        self.back_button.configure(state=state)

    def safe_after_status(self, text: str):
        """
        Thread-safe status update.

        This avoids this bad pattern:
            self.after(0, lambda: self.set_status(f"Error: {ex}"))

        Exception variables like ex are cleared after the except block exits,
        so the lambda can fail later with:
            NameError: free variable 'ex' referenced before assignment
        """
        self.after(0, lambda msg=text: self.set_status(msg))

    def safe_after_busy(self, busy: bool):
        self.after(0, lambda b=busy: self.set_busy(b))

    # -------------------------------------------------------------------------
    # Load update list
    # -------------------------------------------------------------------------
    def load_updates_threaded(self):
        threading.Thread(target=self.load_updates, daemon=True).start()

    def load_updates(self):
        self.safe_after_busy(True)
        self.safe_after_status("Loading update list...")

        try:
            response = requests.get(UPDATE_LIST_URL, timeout=10)
            response.raise_for_status()

            updates = response.json()

            if not isinstance(updates, list):
                raise RuntimeError("index.json must contain a JSON array/list")

            self.after(0, lambda u=updates: self.populate_update_list(u))
            self.safe_after_status("Select an update file")

        except Exception as ex:
            traceback.print_exc()
            error_msg = str(ex)
            self.safe_after_status(f"Failed to load updates: {error_msg}")

        finally:
            self.safe_after_busy(False)

    def populate_update_list(self, updates: list[dict]):
        for btn in self.update_buttons:
            btn.destroy()

        self.update_buttons.clear()
        self.selected_update = None

        row = 0

        for update in updates:
            if not isinstance(update, dict):
                continue

            name = update.get("name", "")
            url = update.get("url", "")

            if not name or not url:
                continue

            if not name.lower().endswith(".zip"):
                continue

            display_text = name

            version = update.get("version", "")
            notes = update.get("notes", "")

            if version:
                display_text += f"    Version: {version}"

            if notes:
                display_text += f"    {notes}"

            btn = ctk.CTkButton(
                self.file_frame,
                text=display_text,
                anchor="w",
                height=45,
                command=lambda u=update: self.select_update(u),
            )
            btn.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
            self.update_buttons.append(btn)
            row += 1

        if not self.update_buttons:
            self.set_status("No ZIP update files found in index.json")

    def select_update(self, update: dict):
        self.selected_update = update
        self.set_status(f"Selected: {update.get('name', '')}")

    # -------------------------------------------------------------------------
    # Run update
    # -------------------------------------------------------------------------
    def run_update_threaded(self):
        threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        if not self.selected_update:
            self.safe_after_status("Select a ZIP update first")
            return

        self.safe_after_busy(True)

        try:
            self.ensure_test_install_folder_exists()

            zip_path = self.download_update()
            self.validate_zip(zip_path)
            backup_path = self.backup_existing_install()
            self.install_zip(zip_path)

            self.safe_after_status(f"Update complete. Backup saved: {backup_path.name}")

            # For the real HMI, you may want to restart after successful install.
            # self.restart_hmi()

        except Exception as ex:
            traceback.print_exc()
            error_msg = str(ex)
            self.safe_after_status(f"Update failed: {error_msg}")

        finally:
            self.safe_after_busy(False)

    def ensure_test_install_folder_exists(self):
        """
        For testing, create a fake HMI install folder if it does not exist.

        For production, you may want to remove this and instead fail if the real
        HMI folder does not exist.
        """
        HMI_INSTALL_FOLDER.mkdir(parents=True, exist_ok=True)

        marker_file = HMI_INSTALL_FOLDER / "existing_hmi_file.txt"
        if not marker_file.exists():
            marker_file.write_text(
                "This is a fake existing HMI install file for update testing.\n",
                encoding="utf-8",
            )

    def download_update(self) -> Path:
        DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

        if not self.selected_update:
            raise RuntimeError("No update selected")

        name = self.selected_update.get("name", "").strip()
        url = self.selected_update.get("url", "").strip()

        if not name:
            raise RuntimeError("Selected update is missing name")

        if not url:
            raise RuntimeError("Selected update is missing url")

        zip_path = DOWNLOAD_FOLDER / name

        self.safe_after_status(f"Downloading {name}...")

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with open(zip_path, "wb") as f:
            f.write(response.content)

        return zip_path

    def validate_zip(self, zip_path: Path):
        self.safe_after_status("Validating ZIP...")

        if not zip_path.exists():
            raise RuntimeError(f"Downloaded file does not exist: {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError("Downloaded file is not a valid ZIP file")

        with zipfile.ZipFile(zip_path, "r") as zf:
            bad_file = zf.testzip()
            if bad_file:
                raise RuntimeError(f"Bad file inside ZIP: {bad_file}")

    def backup_existing_install(self) -> Path:
        self.safe_after_status("Backing up existing HMI...")

        if not HMI_INSTALL_FOLDER.exists():
            raise RuntimeError(
                f"HMI install folder does not exist: {HMI_INSTALL_FOLDER}"
            )

        BACKUP_FOLDER.mkdir(parents=True, exist_ok=True)

        backup_name = "hmi_backup"
        backup_path = BACKUP_FOLDER / backup_name

        index = 1
        while backup_path.exists():
            backup_path = BACKUP_FOLDER / f"{backup_name}_{index}"
            index += 1

        shutil.copytree(HMI_INSTALL_FOLDER, backup_path)

        return backup_path

    def install_zip(self, zip_path: Path):
        self.safe_after_status("Installing update...")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_path)

            extracted_items = list(temp_path.iterdir())

            if not extracted_items:
                raise RuntimeError("ZIP file is empty")

            for item in extracted_items:
                destination = HMI_INSTALL_FOLDER / item.name

                if destination.exists():
                    if destination.is_dir():
                        shutil.rmtree(destination)
                    else:
                        destination.unlink()

                if item.is_dir():
                    shutil.copytree(item, destination)
                else:
                    shutil.copy2(item, destination)

    def restart_hmi(self):
        """
        Raspberry Pi user-service restart.
        Enable this only after testing update install.
        """
        os.system("systemctl --user restart hmi.service")

    def go_back(self):
        if self.controller and hasattr(self.controller, "show_HomePage"):
            self.controller.show_HomePage()
        else:
            self.master.destroy()


class StandaloneSoftwareUpdateApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Software Update")
        self.geometry("900x600")
        self.minsize(800, 480)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        page = SoftwareUpdatePage(self)
        page.grid(row=0, column=0, sticky="nsew")


if __name__ == "__main__":
    app = StandaloneSoftwareUpdateApp()
    app.mainloop()
