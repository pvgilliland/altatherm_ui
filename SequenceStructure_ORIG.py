from typing import List
from SingletonBase import SingletonBase
import json


class Step:
    def __init__(self, power: int, duration: float):
        self.power = power
        self.duration = duration

    def set_power_duration(self, power: int, duration: float):
        self.power = power
        self.duration = duration

    def __repr__(self):
        return f"Step(power={self.power}, duration={self.duration})"

    # Methods for JSON serializarion
    def to_dict(self):
        return {"power": self.power, "duration": self.duration}

    # Methods for JSON serializarion
    @classmethod
    def from_dict(cls, data):
        return cls(data["power"], data["duration"])


class ZoneSequence:
    def __init__(self, name: str, index: int):
        self.name = name
        self.index = index
        self.steps: List[Step] = []

    def add_step(self, power: int, duration: float):
        self.steps.append(Step(power, duration))

    def __repr__(self):
        return f"{self.name}: " + ", ".join(str(step) for step in self.steps)

    # Methods for JSON serializarion
    def to_dict(self):
        return {
            "name": self.name,
            "index": self.index,
            "steps": [step.to_dict() for step in self.steps],
        }

    # Methods for JSON serializarion
    @classmethod
    def from_dict(cls, data):
        zone = cls(data["name"], data["index"])
        zone.steps = [Step.from_dict(s) for s in data["steps"]]
        return zone


class SequenceCollection(SingletonBase):
    def __init_once__(self):
        print("Initializing MyConfig")
        self.zone_sequences = []
        self.Init()

    def Init(self):
        for zoneIndex in range(0, 8):
            zoneSequence = ZoneSequence(f"Zone{zoneIndex + 1}", zoneIndex)
            for phase in range(0, 4):
                zoneSequence.add_step(0, 0)
            self.add_zone_sequence(zoneSequence)

    def add_zone_sequence(self, zone_sequence: ZoneSequence):
        self.zone_sequences.append(zone_sequence)

    def get_zone_sequence(self, name: str) -> ZoneSequence:
        for zone in self.zone_sequences:
            if zone.name == name:
                return zone
        return None  # or raise an exception

    def get_zone_sequence_by_index(self, index: int) -> ZoneSequence:
        for zone in self.zone_sequences:
            if zone.index == index:
                return zone
        return None  # or raise an exception

    # steps are zero based 0 - 3, 4 total steps oer zone
    def get_zone_step(self, name: str, step: int):
        for zone in self.zone_sequences:
            if zone.name == name:
                return zone.steps[step]
        return None  # or raise an exception

    def get_zone_step_by_index(self, index: int, step: int):
        for zone in self.zone_sequences:
            if zone.index == index:
                return zone.steps[step]
        return None  # or raise an exception

    def __repr__(self):
        return "\n".join(str(zone) for zone in self.zone_sequences)

    def to_dict(self):
        return {"zone_sequences": [z.to_dict() for z in self.zone_sequences]}

    def save_to_json(self, filename):
        with open(filename, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data):
        instance = cls.Instance()
        instance.zone_sequences = [
            ZoneSequence.from_dict(z) for z in data["zone_sequences"]
        ]
        return instance

    @classmethod
    def load_from_json(cls, filename):
        with open(filename, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


# === Test code in __main__ ===

if __name__ == "__main__":
    manager = SequenceCollection.Instance()

    manager.get_zone_step("Zone3", 2).set_power_duration(1, 7)

    # zone1 = ZoneSequence("ZONE1")
    # zone1.add_step(10, 1.0)
    # zone1.add_step(2, 3.0)
    # manager.add_zone_sequence(zone1)

    # zone2 = ZoneSequence("ZONE2")
    # zone2.add_step(10, 2.0)
    # manager.add_zone_sequence(zone2)

    # zone3 = ZoneSequence("ZONE3")
    # zone3.add_step(4, 2.5)
    # zone3.add_step(20, 0.5)
    # manager.add_zone_sequence(zone3)

    # zone4 = ZoneSequence("ZONE4")
    # zone4.add_step(5, 4.0)
    # zone4.add_step(3, 2.0)
    # manager.add_zone_sequence(zone4)

    # Test save and restore
    # Save to human-readable file
    # manager.save_to_json("sequences.json")

    # Load and verify
    loaded = SequenceCollection.load_from_json("sequences.json")
    print("Restored step:", loaded.get_zone_step("Zone3", 2))

    # Print all sequences
    print("All zone sequences:")
    print(manager)

    # Get and inspect a specific zone
    zone = manager.get_zone_sequence("Zone3")

    if zone:
        print("\nZone3 details:")
        for step in zone.steps:
            print(f"  Power: {step.power}, Duration: {step.duration}")

    # step is the same as a "phase"
    step = manager.get_zone_step("Zone3", 2)
    if step:
        print(f"Zone3, Step2  Power: {step.power}, Duration: {step.duration}")
