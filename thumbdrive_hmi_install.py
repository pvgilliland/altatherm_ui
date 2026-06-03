import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import shutil
import zipfile


class ThumbDriveHmiInstallDialog(ctk.CTkToplevel):
    def __init__(self, parent, controller=None):
        super().__init__(parent)

        self.controller = controller
        self.zip_file = None
        self.destination_folder = None

        self.title("AltaTherm HMI Installer")
        self.geometry("760x420")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()
        self.focus_force()

        ctk.CTkLabel(
            self, text="AltaTherm HMI Installer", font=("Arial", 30, "bold")
        ).pack(pady=(30, 20))

        self.zip_label = ctk.CTkLabel(
            self, text="No zip file selected", font=("Arial", 15)
        )
        self.zip_label.pack(pady=10)

        ctk.CTkButton(
            self,
            text="Select Install Zip File",
            width=260,
            height=45,
            command=self.select_zip_file,
        ).pack(pady=10)

        self.dest_label = ctk.CTkLabel(
            self, text="No destination folder selected", font=("Arial", 15)
        )
        self.dest_label.pack(pady=10)

        ctk.CTkButton(
            self,
            text="Select Destination Folder",
            width=260,
            height=45,
            command=self.select_destination_folder,
        ).pack(pady=10)

        ctk.CTkButton(
            self,
            text="Backup and Install",
            width=260,
            height=60,
            font=("Arial", 18, "bold"),
            command=self.install_hmi,
        ).pack(pady=25)

        self.status_label = ctk.CTkLabel(self, text="Ready", font=("Arial", 16, "bold"))
        self.status_label.pack(pady=10)

    def select_zip_file(self):
        filename = filedialog.askopenfilename(
            parent=self,
            title="Select HMI Install Zip File",
            filetypes=[("Zip Files", "*.zip")],
        )

        if filename:
            self.zip_file = Path(filename)
            self.zip_label.configure(text=f"Zip File:\n{self.zip_file}")

    def select_destination_folder(self):
        folder = filedialog.askdirectory(parent=self, title="Select Destination Folder")

        if folder:
            self.destination_folder = Path(folder)
            self.dest_label.configure(text=f"Destination:\n{self.destination_folder}")

    def install_hmi(self):
        if self.zip_file is None:
            messagebox.showerror("Error", "Please select a zip file.", parent=self)
            return

        if self.destination_folder is None:
            messagebox.showerror(
                "Error", "Please select a destination folder.", parent=self
            )
            return

        if not self.zip_file.exists():
            messagebox.showerror(
                "Error", f"Zip file does not exist:\n{self.zip_file}", parent=self
            )
            return

        if not zipfile.is_zipfile(self.zip_file):
            messagebox.showerror(
                "Error",
                f"Selected file is not a valid zip file:\n{self.zip_file}",
                parent=self,
            )
            return

        try:
            self.status_label.configure(text="Installing...")
            self.update_idletasks()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            backup_folder = self.destination_folder.parent / (
                f"{self.destination_folder.name}_backup_{timestamp}"
            )

            if self.destination_folder.exists():
                self.status_label.configure(text="Creating backup...")
                self.update_idletasks()

                shutil.copytree(
                    self.destination_folder, backup_folder, dirs_exist_ok=False
                )
            else:
                self.destination_folder.mkdir(parents=True, exist_ok=True)

            temp_extract_folder = self.destination_folder.parent / (
                f"_hmi_install_temp_{timestamp}"
            )

            temp_extract_folder.mkdir(parents=True, exist_ok=True)

            self.status_label.configure(text="Extracting zip...")
            self.update_idletasks()

            with zipfile.ZipFile(self.zip_file, "r") as zipf:
                zipf.extractall(temp_extract_folder)

            self.status_label.configure(text="Copying files...")
            self.update_idletasks()

            self.copy_folder_contents(
                source_folder=temp_extract_folder,
                destination_folder=self.destination_folder,
            )

            shutil.rmtree(temp_extract_folder, ignore_errors=True)

            self.status_label.configure(text="Install complete")

            messagebox.showinfo(
                "Success",
                f"HMI install complete.\n\n"
                f"Installed to:\n{self.destination_folder}\n\n"
                f"Backup created:\n{backup_folder}",
                parent=self,
            )

            self.destroy()

        except Exception as ex:
            self.status_label.configure(text="Install failed")
            messagebox.showerror("Install Failed", str(ex), parent=self)

    def copy_folder_contents(self, source_folder: Path, destination_folder: Path):
        for item in source_folder.iterdir():
            source_item = item
            destination_item = destination_folder / item.name

            if source_item.is_dir():
                destination_item.mkdir(parents=True, exist_ok=True)
                self.copy_folder_contents(source_item, destination_item)
            else:
                destination_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_item, destination_item)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.withdraw()

    ThumbDriveHmiInstallDialog(app)

    app.mainloop()
