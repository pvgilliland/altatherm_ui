import customtkinter as ctk


class UpdateMethodDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        on_wifi_cloud,
        on_thumb_drive,
        title="Software Update",
    ):
        super().__init__(parent)

        self.parent = parent
        self.on_wifi_cloud = on_wifi_cloud
        self.on_thumb_drive = on_thumb_drive

        self.title(title)
        self.geometry("460x280")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._center_on_parent()

        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build_ui()

    def _center_on_parent(self):
        self.parent.update_idletasks()

        width = 460
        height = 280

        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()

        x = parent_x + (parent_w // 2) - (width // 2)
        y = parent_y + (parent_h // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        main = ctk.CTkFrame(self, corner_radius=0)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(
            main,
            text="Software Update",
            font=("Arial", 28, "bold"),
        )
        title_label.pack(pady=(10, 8))

        message_label = ctk.CTkLabel(
            main,
            text="How would you like to update the HMI software?",
            font=("Arial", 20),
            wraplength=380,
            justify="center",
        )
        message_label.pack(pady=(0, 20))

        wifi_button = ctk.CTkButton(
            main,
            text="Wi-Fi / Cloud",
            height=48,
            font=("Arial", 22),
            command=self._wifi_cloud_clicked,
        )
        wifi_button.pack(fill="x", padx=35, pady=6)

        thumb_button = ctk.CTkButton(
            main,
            text="Thumb Drive",
            height=48,
            font=("Arial", 22),
            command=self._thumb_drive_clicked,
        )
        thumb_button.pack(fill="x", padx=35, pady=6)

        cancel_button = ctk.CTkButton(
            main,
            text="Cancel",
            height=42,
            font=("Arial", 18),
            command=self._cancel,
        )
        cancel_button.pack(fill="x", padx=35, pady=(12, 0))

    def _wifi_cloud_clicked(self):
        self.destroy()
        if self.on_wifi_cloud:
            self.on_wifi_cloud()

    def _thumb_drive_clicked(self):
        self.destroy()
        if self.on_thumb_drive:
            self.on_thumb_drive()

    def _cancel(self):
        self.destroy()
