"""Intelbras AMT cloud protocol (ISECMobile over amt.intelbras.com.br)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .const import CLOUD_HOST, CLOUD_PORT, CMD_ARM, CMD_DISARM, CMD_STAY, PARTITIONS, ModelSpec

TIMEOUT = 15
TOKEN = "homeassistant"
CONNECTION_ETHERNET = 0x45

LOGIN_OK = {0xE6, 0xFE, 0x45, 0x46, 0x47}
LOGIN_PANEL_OFFLINE = {0xE4, 0xFD}
LOGIN_BUSY = 0xE8

PACKET_MY_HOME = 0xE9
DELIMITER = 0x21
ACK = 0xFE
RESP_BAD_PASSWORD = 0xE1
MAX_SKIPPED_FRAMES = 5
RECONNECT_COOLDOWN = 3.0

_last_close: dict[str, float] = {}
CMD_DISCONNECT =bytes([0x05, 0xE7, 0x01, 0x15, 0x06, 0x7E, 0x71])


class AmtError(Exception):
    pass


class AmtConnectionError(AmtError):
    pass


class AmtPanelOfflineError(AmtConnectionError):
    pass


class AmtBusyError(AmtConnectionError):
    pass


class AmtAuthError(AmtError):
    pass


class AmtModelError(AmtError):
    pass


@dataclass
class PanelStatus:
    firmware: int
    partitioned: bool
    armed: dict[str, bool] = field(default_factory=dict)
    stay: dict[str, bool] = field(default_factory=dict)
    siren: bool = False

    @property
    def any_armed(self) -> bool:
        return any(self.armed.values())


def checksum(data: list[int]) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value ^ 0xFF


def normalize_mac(mac: str) -> str:
    clean = "".join(c for c in mac if c.isalnum()).upper()
    if len(clean) != 12 or any(c not in "0123456789ABCDEF" for c in clean):
        raise ValueError(mac)
    return ":".join(clean[i : i + 2] for i in range(0, 12, 2))


def _bit(data: bytes, position: tuple[int, int]) -> bool:
    index, bit = position
    return bool(data[index] & (1 << bit))


def parse_status(data: bytes, model: ModelSpec) -> PanelStatus:
    if len(data) < model.min_length or data[1] != PACKET_MY_HOME:
        raise AmtModelError(f"resposta de status inesperada ({len(data)} bytes)")
    firmware = data[model.firmware]
    partitioned = _bit(data, model.partitioned)
    armed = {PARTITIONS[i]: _bit(data, pos) for i, pos in enumerate(model.armed)}
    stay: dict[str, bool] = {}
    if model.stay and firmware >= model.stay_min_firmware:
        stay = {PARTITIONS[i]: _bit(data, pos) for i, pos in enumerate(model.stay)}
    return PanelStatus(
        firmware=firmware,
        partitioned=partitioned,
        armed=armed,
        stay=stay,
        siren=_bit(data, model.siren),
    )


def arm_command(partition: str | None, stay: bool = False) -> list[int]:
    cmd = [CMD_ARM]
    if partition:
        cmd.append(ord(partition))
    if stay:
        cmd.append(CMD_STAY)
    return cmd


def disarm_command(partition: str | None, model: ModelSpec) -> list[int]:
    if partition:
        return [CMD_DISARM, ord(partition)]
    return list(model.disarm_all)


class AmtCloudClient:
    def __init__(self, mac: str, password: str, model: ModelSpec, device_id: str) -> None:
        self.mac = normalize_mac(mac)
        self.password = password
        self.model = model
        self.device_id = device_id
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def _read(self, size: int = 255) -> bytes:
        assert self._reader is not None
        data = await asyncio.wait_for(self._reader.read(size), TIMEOUT)
        if not data:
            raise AmtConnectionError("conexão encerrada pelo servidor Intelbras")
        return data

    async def _read_frame(self) -> bytes:
        assert self._reader is not None
        first = await self._read(1)
        length = first[0]
        if length == ACK:
            return first
        if 0 < length < 0x80:
            rest = await asyncio.wait_for(self._reader.readexactly(length + 1), TIMEOUT)
            return first + rest[:-1]
        return first + await self._read()

    async def _drain_pending(self) -> None:
        assert self._reader is not None
        while True:
            try:
                data = await asyncio.wait_for(self._reader.read(255), 0.05)
            except asyncio.TimeoutError:
                return
            if not data:
                raise AmtConnectionError("conexão encerrada pelo servidor Intelbras")

    async def _connect(self) -> None:
        loop = asyncio.get_running_loop()
        wait = _last_close.get(self.mac, 0) + RECONNECT_COOLDOWN - loop.time()
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(CLOUD_HOST, CLOUD_PORT), TIMEOUT
            )
            self._writer.write(bytes([0x01, 0xFB, 0x05]))
            await self._writer.drain()
            challenge = await self._read()
            if len(challenge) < 2:
                raise AmtConnectionError("servidor não enviou a chave de conexão")
            key = challenge[1]
            packet = [0, 0xE5, 0x06]
            packet += list(bytes.fromhex(self.device_id.rjust(16, "0")[:16]))
            packet += list(bytes.fromhex(self.mac.replace(":", "")))
            packet += [checksum([ord(c) for c in TOKEN]), CONNECTION_ETHERNET, 0, 0, 0, 0, 3, 0]
            packet += [ord(c) for c in TOKEN]
            packet[0] = len(packet) - 1
            packet.append(checksum(packet))
            self._writer.write(bytes(b ^ key for b in packet))
            await self._writer.drain()
            answer = (await self._read())[0]
        except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
            await self._close()
            raise AmtConnectionError(f"falha ao conectar na nuvem Intelbras: {err}") from err
        except AmtError:
            await self._close()
            raise
        if answer in LOGIN_OK:
            return
        await self._close()
        if answer in LOGIN_PANEL_OFFLINE:
            raise AmtPanelOfflineError("central não está conectada à nuvem Intelbras")
        if answer == LOGIN_BUSY:
            raise AmtBusyError("outro aparelho está conectado à central")
        raise AmtConnectionError(f"nuvem Intelbras recusou a conexão (0x{answer:02X})")

    async def _close(self) -> None:
        writer, self._writer, self._reader = self._writer, None, None
        if writer is None:
            return
        if not writer.is_closing():
            try:
                writer.write(CMD_DISCONNECT)
                await asyncio.wait_for(writer.drain(), 2)
            except (OSError, asyncio.TimeoutError):
                pass
        writer.close()
        try:
            await writer.wait_closed()
        except (OSError, asyncio.TimeoutError):
            pass
        _last_close[self.mac] = asyncio.get_running_loop().time()

    async def _exchange(self, cmd: list[int]) -> bytes:
        packet = [len(self.password) + len(cmd) + 3, PACKET_MY_HOME, DELIMITER]
        packet += [ord(c) for c in self.password] + cmd + [DELIMITER]
        packet.append(checksum(packet))
        for attempt in range(2):
            if not self.connected:
                await self._connect()
            assert self._writer is not None
            try:
                await self._drain_pending()
                self._writer.write(bytes(packet))
                await self._writer.drain()
                expects_status = cmd[0] == self.model.status_cmd
                for _ in range(MAX_SKIPPED_FRAMES):
                    frame = await self._read_frame()
                    if frame[0] == ACK and not expects_status:
                        return frame
                    if len(frame) >= 3 and frame[1] == PACKET_MY_HOME:
                        return frame
                raise AmtConnectionError("central respondeu fora do protocolo esperado")
            except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, AmtConnectionError) as err:
                await self._close()
                if attempt:
                    raise AmtConnectionError(f"sem resposta da central: {err}") from err
        raise AmtConnectionError("sem resposta da central")

    @staticmethod
    def _check_password(frame: bytes) -> None:
        if len(frame) >= 3 and frame[1] == PACKET_MY_HOME and frame[2] == RESP_BAD_PASSWORD:
            raise AmtAuthError("senha remota recusada pela central")

    async def async_status(self) -> PanelStatus:
        async with self._lock:
            frame = await self._exchange([self.model.status_cmd])
        self._check_password(frame)
        return parse_status(frame, self.model)

    async def async_send(self, cmd: list[int]) -> None:
        async with self._lock:
            frame = await self._exchange(cmd)
        self._check_password(frame)

    async def async_close(self) -> None:
        async with self._lock:
            await self._close()
