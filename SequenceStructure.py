from typing import Any, Dict, List, Optional
from SingletonBase import SingletonBase
import json


# ----------------------------------------------------------------------
# Sequence structure constants
# ----------------------------------------------------------------------
NUM_OF_ZONES = 8
NUM_OF_STEPS = 4

# Printable ASCII base-94 encoding:
#     "!" = 0
#     '"' = 1
#     ...
#     "~" = 93
U94_FIRST_ASCII = 33
U94_BASE = 94

# Each power and duration value uses two u94 characters.
ENCODED_POWER_WIDTH = 2
ENCODED_DURATION_WIDTH = 2
ENCODED_STEP_WIDTH = ENCODED_POWER_WIDTH + ENCODED_DURATION_WIDTH

# 8 zones x 4 steps x 4 encoded characters per step = 128 characters.
ENCODED_PROGRAM_DATA_LENGTH = (
    NUM_OF_ZONES * NUM_OF_STEPS * ENCODED_STEP_WIDTH
)


# ----------------------------------------------------------------------
# Encoded program helpers
# ----------------------------------------------------------------------
def decode_u94(encoded_value: str) -> int:
    """
    Decode an unsigned base-94 value.

    Valid characters are the printable ASCII characters from "!" through "~".

    For a two-character value:

        first_character_value * 94 + second_character_value
    """

    if encoded_value is None:
        raise ValueError("Encoded u94 value cannot be None")

    if len(encoded_value) == 0:
        raise ValueError("Encoded u94 value cannot be empty")

    decoded_value = 0

    for character in encoded_value:
        digit = ord(character) - U94_FIRST_ASCII

        if digit < 0 or digit >= U94_BASE:
            raise ValueError(
                f"Invalid u94 character {character!r}. "
                'Valid characters are "!" through "~".'
            )

        decoded_value = decoded_value * U94_BASE + digit

    return decoded_value


def decode_program_to_dict(encoded_program: str) -> Dict[str, Any]:
    """
    Decode an encoded cooking program into the same dictionary shape used
    by SequenceCollection.from_dict().

    Expected format:

        description,<128 encoded characters>

    The 128-character data section contains:

        8 zones
        4 steps per zone
        2 characters for power
        2 characters for duration

    Returned dictionary:

        {
            "description": "Program description",
            "zone_sequences": [
                {
                    "name": "Zone1",
                    "index": 0,
                    "steps": [
                        {"power": 100, "duration": 300.0},
                        ...
                    ]
                },
                ...
            ]
        }
    """

    if encoded_program is None:
        raise ValueError("Encoded program cannot be None")

    # Remove serial terminators and NUL padding only from the ends.
    # Do not call .strip() without arguments because spaces can be valid
    # characters in the program description.
    encoded_program = encoded_program.strip("\r\n\x00")

    if len(encoded_program) == 0:
        raise ValueError("Encoded program cannot be empty")

    comma_index = encoded_program.find(",")

    if comma_index < 0:
        raise ValueError(
            "Encoded program must contain a comma between the "
            "description and encoded program data"
        )

    description = encoded_program[:comma_index].strip()
    encoded_data = encoded_program[comma_index + 1:]

    if len(description) == 0:
        raise ValueError("Program description cannot be empty")

    if len(encoded_data) != ENCODED_PROGRAM_DATA_LENGTH:
        raise ValueError(
            "Encoded program data has the wrong length. "
            f"Expected {ENCODED_PROGRAM_DATA_LENGTH} characters, "
            f"received {len(encoded_data)}."
        )

    zone_sequences: List[Dict[str, Any]] = []
    position = 0

    for zone_index in range(NUM_OF_ZONES):
        steps: List[Dict[str, Any]] = []

        for step_index in range(NUM_OF_STEPS):
            encoded_power = encoded_data[
                position:position + ENCODED_POWER_WIDTH
            ]
            position += ENCODED_POWER_WIDTH

            encoded_duration = encoded_data[
                position:position + ENCODED_DURATION_WIDTH
            ]
            position += ENCODED_DURATION_WIDTH

            power = decode_u94(encoded_power)
            duration = decode_u94(encoded_duration)

            if power < 0 or power > 100:
                raise ValueError(
                    f"Zone {zone_index + 1}, step {step_index + 1}: "
                    f"decoded power {power} is outside the valid range 0-100"
                )

            steps.append(
                {
                    "power": power,
                    "duration": float(duration),
                }
            )

        zone_sequences.append(
            {
                "name": f"Zone{zone_index + 1}",
                "index": zone_index,
                "steps": steps,
            }
        )

    return {
        "description": description,
        "zone_sequences": zone_sequences,
    }


# ----------------------------------------------------------------------
# Sequence data classes
# ----------------------------------------------------------------------
class Step:
    def __init__(self, power: int, duration: float):
        self.power = int(power)
        self.duration = float(duration)

    def set_power_duration(self, power: int, duration: float):
        self.power = int(power)
        self.duration = float(duration)

    def __repr__(self):
        return f"Step(power={self.power}, duration={self.duration})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "power": self.power,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("Step data must be a dictionary")

        try:
            power = int(data["power"])
            duration = float(data["duration"])
        except KeyError as error:
            raise ValueError(
                f"Step data is missing required field: {error.args[0]}"
            ) from error
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Step power and duration must be numeric values"
            ) from error

        if power < 0 or power > 100:
            raise ValueError(
                f"Step power {power} is outside the valid range 0-100"
            )

        if duration < 0:
            raise ValueError("Step duration cannot be negative")

        return cls(power, duration)


class ZoneSequence:
    def __init__(self, name: str, index: int):
        self.name = str(name)
        self.index = int(index)
        self.steps: List[Step] = []

    def add_step(self, power: int, duration: float):
        self.steps.append(Step(power, duration))

    def __repr__(self):
        return f"{self.name}: " + ", ".join(
            str(step) for step in self.steps
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "index": self.index,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("Zone sequence data must be a dictionary")

        try:
            name = str(data["name"])
            index = int(data["index"])
            steps_data = data["steps"]
        except KeyError as error:
            raise ValueError(
                f"Zone data is missing required field: {error.args[0]}"
            ) from error
        except (TypeError, ValueError) as error:
            raise ValueError("Zone index must be an integer") from error

        if not isinstance(steps_data, list):
            raise ValueError(f"{name} steps must be a list")

        zone = cls(name, index)
        zone.steps = [Step.from_dict(step) for step in steps_data]

        return zone


class SequenceCollection(SingletonBase):
    def __init_once__(self):
        print("Initializing SequenceCollection")
        self.zone_sequences: List[ZoneSequence] = []
        self.Init()

    def Init(self):
        """
        Reset the singleton to 8 zones with 4 empty steps per zone.
        """

        self.zone_sequences = []

        for zone_index in range(NUM_OF_ZONES):
            zone_sequence = ZoneSequence(
                f"Zone{zone_index + 1}",
                zone_index,
            )

            for _step_index in range(NUM_OF_STEPS):
                zone_sequence.add_step(0, 0.0)

            self.add_zone_sequence(zone_sequence)

    def add_zone_sequence(self, zone_sequence: ZoneSequence):
        self.zone_sequences.append(zone_sequence)

    def get_zone_sequence(self, name: str) -> Optional[ZoneSequence]:
        for zone in self.zone_sequences:
            if zone.name == name:
                return zone

        return None

    def get_zone_sequence_by_index(
        self,
        index: int,
    ) -> Optional[ZoneSequence]:
        for zone in self.zone_sequences:
            if zone.index == index:
                return zone

        return None

    # Steps are zero-based: 0 through 3.
    def get_zone_step(
        self,
        name: str,
        step: int,
    ) -> Optional[Step]:
        zone = self.get_zone_sequence(name)

        if zone is None:
            return None

        if step < 0 or step >= len(zone.steps):
            return None

        return zone.steps[step]

    def get_zone_step_by_index(
        self,
        index: int,
        step: int,
    ) -> Optional[Step]:
        zone = self.get_zone_sequence_by_index(index)

        if zone is None:
            return None

        if step < 0 or step >= len(zone.steps):
            return None

        return zone.steps[step]

    def __repr__(self):
        return "\n".join(
            str(zone) for zone in self.zone_sequences
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_sequences": [
                zone.to_dict() for zone in self.zone_sequences
            ]
        }

    def save_to_json(self, filename: str):
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Populate the SequenceCollection singleton from a dictionary.

        This is the common population path used by:

            - load_program_into_sequence_collection()
            - SequenceCollection.load_from_json()
            - SequenceCollection.from_encoded_program()

        The singleton is not modified unless the entire incoming structure
        passes validation.
        """

        if not isinstance(data, dict):
            raise ValueError(
                "SequenceCollection data must be a dictionary"
            )

        zone_sequences_data = data.get("zone_sequences")

        if not isinstance(zone_sequences_data, list):
            raise ValueError(
                "SequenceCollection data must contain a "
                "'zone_sequences' list"
            )

        if len(zone_sequences_data) != NUM_OF_ZONES:
            raise ValueError(
                f"Expected {NUM_OF_ZONES} zones, "
                f"received {len(zone_sequences_data)}"
            )

        new_zone_sequences: List[ZoneSequence] = []

        for expected_index in range(NUM_OF_ZONES):
            zone_data = zone_sequences_data[expected_index]
            zone = ZoneSequence.from_dict(zone_data)

            if zone.index != expected_index:
                raise ValueError(
                    f"Zone position {expected_index} has index "
                    f"{zone.index}; expected {expected_index}"
                )

            expected_name = f"Zone{expected_index + 1}"

            if zone.name != expected_name:
                raise ValueError(
                    f"Zone index {expected_index} has name "
                    f"{zone.name!r}; expected {expected_name!r}"
                )

            if len(zone.steps) != NUM_OF_STEPS:
                raise ValueError(
                    f"{zone.name} must contain exactly "
                    f"{NUM_OF_STEPS} steps; "
                    f"received {len(zone.steps)}"
                )

            new_zone_sequences.append(zone)

        instance = cls.Instance()

        # Replace the active program only after every zone and step has
        # been decoded and validated.
        instance.zone_sequences = new_zone_sequences

        return instance

    @classmethod
    def from_encoded_program(
        cls,
        encoded_program: str,
    ) -> Dict[str, Any]:
        """
        Decode an encoded program and populate the singleton through
        SequenceCollection.from_dict().

        Returns the complete decoded dictionary, including description.

        Typical use:

            decoded = SequenceCollection.from_encoded_program(encoded_string)

            save_program_from_sequence_collection(
                program_number,
                description=decoded["description"],
            )
        """

        decoded_program = decode_program_to_dict(encoded_program)

        cls.from_dict(
            {
                "zone_sequences": decoded_program["zone_sequences"],
            }
        )

        return decoded_program

    @classmethod
    def load_from_json(cls, filename: str):
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)

        return cls.from_dict(data)


# ----------------------------------------------------------------------
# Basic local test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    manager = SequenceCollection.Instance()

    print("Default SequenceCollection:")
    print(manager)

    # Example usage with a real encoded string:
    #
    # encoded_string = "Program Name," + ("!" * 128)
    #
    # decoded_program = SequenceCollection.from_encoded_program(
    #     encoded_string
    # )
    #
    # print("\nDecoded description:")
    # print(decoded_program["description"])
    #
    # print("\nDecoded SequenceCollection:")
    # print(SequenceCollection.Instance())
