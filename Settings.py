import json
import os
from hmi_consts import SETTINGS_DIR


class Settings:
    _instance = None

    def __init__(self):
        self.tset = 60.0
        self.thys = 5.0
        self.top_zones_correction_factor = 80
        self.bottom_zones_correction_factor = 80
        self.tc = 240
        self.enable_cook_algorithm = False
        self.load()

    @staticmethod
    def Instance():
        if Settings._instance is None:
            Settings._instance = Settings()
        return Settings._instance

    def _settings_path(self):
        return os.path.join(SETTINGS_DIR, "settings.alt")

    def load(self):
        path = self._settings_path()
        try:
            with open(path, "r") as f:
                data = json.load(f)

            self.tset = data.get("tset", self.tset)
            self.thys = data.get("thys", self.thys)
            self.top_zones_correction_factor = data.get(
                "top_zones_correction_factor",
                self.top_zones_correction_factor,
            )
            self.bottom_zones_correction_factor = data.get(
                "bottom_zones_correction_factor",
                self.bottom_zones_correction_factor,
            )
            self.tc = data.get("tc", self.tc)
            self.enable_cook_algorithm = data.get(
                "enable_cook_algorithm", self.enable_cook_algorithm
            )

        except Exception as e:
            print(f"[Settings] load failed: {e}")

    def save(self):
        path = self._settings_path()
        try:
            data = {}

            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"[Settings] existing settings read failed: {e}")
                    data = {}

            data["tset"] = self.tset
            data["thys"] = self.thys
            data["top_zones_correction_factor"] = self.top_zones_correction_factor
            data["bottom_zones_correction_factor"] = self.bottom_zones_correction_factor
            data["tc"] = self.tc
            data["enable_cook_algorithm"] = self.enable_cook_algorithm

            with open(path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"[Settings] save failed: {e}")
