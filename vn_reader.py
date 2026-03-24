import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field

import serial

HISTORY_LEN = 300

INS_MODES = {0: "Not Tracking", 1: "Degraded", 2: "Healthy", 3: "GNSS Loss"}


def vn_command(payload: str) -> bytes:
    """Build a VN command with XX checksum bypass."""
    return f"${payload}*XX\r\n".encode("ascii")


def decode_ins_status(status: int) -> dict:
    return {
        "mode": INS_MODES.get(status & 0x03, "Unknown"),
        "error": bool(status & 0x04),
        "time_error": bool(status & 0x08),
        "imu_error": bool(status & 0x10),
        "mag_pres_error": bool(status & 0x20),
        "gnss_error": bool(status & 0x40),
    }


def compute_mag_heading(mag_x: float, mag_y: float) -> float:
    heading = math.degrees(math.atan2(-mag_y, mag_x))
    if heading < 0:
        heading += 360.0
    return heading


@dataclass
class VNData:
    # Device info (queried once at startup)
    model: str = ""
    hw_rev: str = ""
    serial_num: str = ""
    firmware: str = ""

    # Connection state
    connected: bool = False
    error_msg: str = ""

    # INS data from $VNINS
    ins_time: float = 0.0
    ins_week: int = 0
    ins_status: int = 0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    vel_n: float = 0.0
    vel_e: float = 0.0
    vel_d: float = 0.0
    att_unc: float = 0.0
    pos_unc: float = 0.0
    vel_unc: float = 0.0

    # Mag data from Register 27 poll
    mag_x: float = 0.0
    mag_y: float = 0.0
    mag_z: float = 0.0
    mag_heading: float = 0.0

    # Decoded INS status
    ins_mode: str = "Unknown"
    ins_error: bool = False
    ins_time_error: bool = False
    ins_imu_error: bool = False
    ins_mag_pres_error: bool = False
    ins_gnss_error: bool = False

    # Time-series buffers
    mag_x_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    mag_y_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    mag_z_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    mag_heading_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    mag_time_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    yaw_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    pitch_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    roll_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    att_time_hist: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))

    _start_time: float = field(default_factory=time.monotonic)


class VNReader(threading.Thread):
    def __init__(self, port: str = "COM4", baud: int = 115200):
        super().__init__(daemon=True)
        self.port = port
        self.baud = baud
        self.data = VNData()
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self._ser: serial.Serial | None = None
        self._poll_interval = 0.25  # poll mag register at 4Hz

    def run(self):
        while not self._stop_event.is_set():
            try:
                self._connect()
                self._query_device_info()
                self._main_loop()
            except serial.SerialException:
                with self.lock:
                    self.data.connected = False
                    self.data.error_msg = "Connection lost"
                if self._ser:
                    try:
                        self._ser.close()
                    except Exception:
                        pass
                    self._ser = None
                self._stop_event.wait(2)  # retry after 2s
            except Exception as e:
                with self.lock:
                    self.data.connected = False
                    self.data.error_msg = str(e)
                break

    def stop(self):
        self._stop_event.set()
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:
                pass

    def get_snapshot(self) -> dict:
        with self.lock:
            return {
                "model": self.data.model,
                "hw_rev": self.data.hw_rev,
                "serial_num": self.data.serial_num,
                "firmware": self.data.firmware,
                "connected": self.data.connected,
                "error_msg": self.data.error_msg,
                "ins_time": self.data.ins_time,
                "ins_week": self.data.ins_week,
                "ins_status": self.data.ins_status,
                "yaw": self.data.yaw,
                "pitch": self.data.pitch,
                "roll": self.data.roll,
                "latitude": self.data.latitude,
                "longitude": self.data.longitude,
                "altitude": self.data.altitude,
                "vel_n": self.data.vel_n,
                "vel_e": self.data.vel_e,
                "vel_d": self.data.vel_d,
                "att_unc": self.data.att_unc,
                "pos_unc": self.data.pos_unc,
                "vel_unc": self.data.vel_unc,
                "mag_x": self.data.mag_x,
                "mag_y": self.data.mag_y,
                "mag_z": self.data.mag_z,
                "mag_heading": self.data.mag_heading,
                "ins_mode": self.data.ins_mode,
                "ins_error": self.data.ins_error,
                "ins_time_error": self.data.ins_time_error,
                "ins_imu_error": self.data.ins_imu_error,
                "ins_mag_pres_error": self.data.ins_mag_pres_error,
                "ins_gnss_error": self.data.ins_gnss_error,
                "mag_x_hist": list(self.data.mag_x_hist),
                "mag_y_hist": list(self.data.mag_y_hist),
                "mag_z_hist": list(self.data.mag_z_hist),
                "mag_heading_hist": list(self.data.mag_heading_hist),
                "mag_time_hist": list(self.data.mag_time_hist),
                "yaw_hist": list(self.data.yaw_hist),
                "pitch_hist": list(self.data.pitch_hist),
                "roll_hist": list(self.data.roll_hist),
                "att_time_hist": list(self.data.att_time_hist),
            }

    # -- internal --

    def _connect(self):
        self._ser = serial.Serial(self.port, self.baud, timeout=0.05)
        time.sleep(0.3)
        self._ser.reset_input_buffer()
        with self.lock:
            self.data.connected = True
            self.data.error_msg = ""

    def _send(self, cmd: bytes):
        if self._ser and self._ser.is_open:
            self._ser.write(cmd)

    def _read_line(self) -> str:
        if not self._ser or not self._ser.is_open:
            return ""
        raw = self._ser.readline()
        if raw:
            return raw.decode("ascii", errors="replace").strip()
        return ""

    def _query_device_info(self):
        reg_fields = {
            1: "model",
            2: "hw_rev",
            3: "serial_num",
            4: "firmware",
        }
        for reg_num, field_name in reg_fields.items():
            for attempt in range(3):
                self._send(vn_command(f"VNRRG,{reg_num:02d}"))
                deadline = time.monotonic() + 0.5
                found = False
                while time.monotonic() < deadline:
                    line = self._read_line()
                    if not line:
                        continue
                    # Parse any VNINS messages we see while waiting
                    if line.startswith("$VNINS"):
                        self._parse_vnins(line)
                    elif line.startswith(f"$VNRRG,{reg_num:02d}"):
                        parts = line.split("*")[0].split(",")
                        if len(parts) >= 3:
                            with self.lock:
                                setattr(self.data, field_name, parts[2].strip())
                        found = True
                        break
                if found:
                    break

    def _main_loop(self):
        last_poll = time.monotonic()
        while not self._stop_event.is_set():
            line = self._read_line()
            if line:
                self._dispatch(line)

            now = time.monotonic()
            if now - last_poll >= self._poll_interval:
                self._send(vn_command("VNRRG,17"))
                last_poll = now

    def _dispatch(self, line: str):
        if line.startswith("$VNINS"):
            self._parse_vnins(line)
        elif line.startswith("$VNRRG"):
            self._parse_vnrrg(line)

    def _parse_vnins(self, line: str):
        try:
            payload = line.split("*")[0]
            parts = payload.split(",")
            if len(parts) < 16:
                return

            elapsed = time.monotonic() - self.data._start_time
            status = int(parts[3], 16)
            decoded = decode_ins_status(status)

            with self.lock:
                self.data.ins_time = float(parts[1])
                self.data.ins_week = int(parts[2])
                self.data.ins_status = status
                self.data.yaw = float(parts[4])
                self.data.pitch = float(parts[5])
                self.data.roll = float(parts[6])
                self.data.latitude = float(parts[7])
                self.data.longitude = float(parts[8])
                self.data.altitude = float(parts[9])
                self.data.vel_n = float(parts[10])
                self.data.vel_e = float(parts[11])
                self.data.vel_d = float(parts[12])
                self.data.att_unc = float(parts[13])
                self.data.pos_unc = float(parts[14])
                self.data.vel_unc = float(parts[15])

                self.data.ins_mode = decoded["mode"]
                self.data.ins_error = decoded["error"]
                self.data.ins_time_error = decoded["time_error"]
                self.data.ins_imu_error = decoded["imu_error"]
                self.data.ins_mag_pres_error = decoded["mag_pres_error"]
                self.data.ins_gnss_error = decoded["gnss_error"]

                self.data.yaw_hist.append(self.data.yaw)
                self.data.pitch_hist.append(self.data.pitch)
                self.data.roll_hist.append(self.data.roll)
                self.data.att_time_hist.append(elapsed)
        except (ValueError, IndexError):
            pass

    def _parse_vnrrg(self, line: str):
        try:
            payload = line.split("*")[0]
            parts = payload.split(",")
            if len(parts) < 3:
                return

            reg_num = int(parts[1])

            if reg_num == 17 and len(parts) >= 5:
                # $VNRRG,27,MagX,MagY,MagZ
                mag_x = float(parts[2])
                mag_y = float(parts[3])
                mag_z = float(parts[4])
                heading = compute_mag_heading(mag_x, mag_y)
                elapsed = time.monotonic() - self.data._start_time

                with self.lock:
                    self.data.mag_x = mag_x
                    self.data.mag_y = mag_y
                    self.data.mag_z = mag_z
                    self.data.mag_heading = heading

                    self.data.mag_x_hist.append(mag_x)
                    self.data.mag_y_hist.append(mag_y)
                    self.data.mag_z_hist.append(mag_z)
                    self.data.mag_heading_hist.append(heading)
                    self.data.mag_time_hist.append(elapsed)

            elif reg_num in (1, 2, 3, 4) and len(parts) >= 3:
                field_map = {1: "model", 2: "hw_rev", 3: "serial_num", 4: "firmware"}
                with self.lock:
                    setattr(self.data, field_map[reg_num], parts[2].strip())
        except (ValueError, IndexError):
            pass
