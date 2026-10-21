"""Constants for Intelbras AMT (cloud)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

DOMAIN = "intelbras_amt_cloud"
LOGGER = logging.getLogger(__package__)

MANUFACTURER = "Intelbras"

CLOUD_HOST = "amt.intelbras.com.br"
CLOUD_PORT = 9016

CONF_MAC = "mac"
CONF_MODEL = "model"
CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10

PLATFORMS = ["alarm_control_panel", "binary_sensor", "sensor"]

PARTITIONS = ("A", "B", "C", "D")

CMD_ARM = 0x41
CMD_DISARM = 0x44
CMD_STAY = 0x50


@dataclass(frozen=True)
class ModelSpec:
    name: str
    status_cmd: int
    firmware: int
    partitioned: tuple[int, int]
    armed: tuple[tuple[int, int], ...]
    siren: tuple[int, int]
    stay: tuple[tuple[int, int], ...] = ()
    stay_min_firmware: int = 0
    disarm_all: tuple[int, ...] = (CMD_DISARM,)
    tested: bool = False

    @property
    def min_length(self) -> int:
        positions = [self.firmware, self.partitioned[0], self.siren[0]]
        positions += [b for b, _ in self.armed] + [b for b, _ in self.stay]
        return max(positions) + 1


MODELS: dict[str, ModelSpec] = {
    "anm24net": ModelSpec(
        name="ANM 24 Net",
        status_cmd=0x5A,
        firmware=21,
        partitioned=(22, 0),
        armed=((23, 0), (23, 1)),
        siren=(39, 2),
        disarm_all=(CMD_DISARM, 0x41),
        tested=True,
    ),
    "amt2018": ModelSpec(
        name="AMT 2018",
        status_cmd=0x5A,
        firmware=21,
        partitioned=(22, 0),
        armed=((23, 0), (23, 1)),
        siren=(39, 2),
    ),
    "amt2018esmart": ModelSpec(
        name="AMT 2018 E Smart",
        status_cmd=0x5D,
        firmware=21,
        partitioned=(22, 0),
        armed=((23, 0), (23, 1)),
        stay=((94, 0), (94, 1)),
        siren=(39, 2),
    ),
    "amt4010": ModelSpec(
        name="AMT 4010",
        status_cmd=0x5B,
        firmware=27,
        partitioned=(28, 0),
        armed=((29, 0), (29, 1), (30, 0), (30, 1)),
        stay=((29, 4), (29, 5), (30, 4), (30, 5)),
        stay_min_firmware=87,
        siren=(47, 3),
    ),
}

DEFAULT_MODEL = "anm24net"
