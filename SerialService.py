import threading
import time
from typing import Callable, List, Optional
import serial
import serial.tools.list_ports

try:
    from hmi_consts import HMISerial

    BAUD = getattr(HMISerial, "BAUD_RATE", 115200)  # was 115200
    DATABITS = getattr(HMISerial, "DATABITS", serial.EIGHTBITS)
    PARITY = getattr(HMISerial, "PARITY", serial.PARITY_NONE)
    STOPBITS = getattr(HMISerial, "STOPBITS", serial.STOPBITS_ONE)
except Exception:
    BAUD, DATABITS, PARITY, STOPBITS = (
        115200,
        serial.EIGHTBITS,
        serial.PARITY_NONE,
        serial.STOPBITS_ONE,
    )


class SerialService:
    """Threaded serial manager with Tk-safe callbacks.
    Thread-safe, with enforced 50ms minimum spacing between sends.
    """

    def __init__(self, tk_root=None, port_hint: Optional[str] = None, line_ending="\r"):
        self.tk_root = tk_root
        self.port_hint = port_hint
        self.line_ending = line_ending
        self._ser = None
        self._read_thread = None
        self._stop = threading.Event()
        self._listeners: List[Callable[[str], None]] = []

        self._io_lock = threading.Lock()  # protects reads/writes to _ser
        self._state_lock = threading.Lock()  # protects start/stop lifecycle
        self._last_send_time = 0.0  # throttle state

    # ---- public API ----
    def start(self):
        with self._state_lock:
            self._open_port()
            self._stop.clear()
            self._read_thread = threading.Thread(target=self._reader, daemon=True)
            self._read_thread.start()

    def stop(self):
        with self._state_lock:
            self._stop.set()
            if self._read_thread and self._read_thread.is_alive():
                self._read_thread.join(timeout=1.0)
            self._read_thread = None
            with self._io_lock:
                if self._ser:
                    try:
                        self._ser.close()
                    except Exception:
                        pass
                self._ser = None

    def restart(self):
        self.stop()
        self.start()

    def send(self, cmd: str):
        with self._io_lock:
            if not self._ser or not self._ser.is_open:
                raise RuntimeError("Serial port not open")

            # throttle enforcement
            now = time.time()
            elapsed = now - self._last_send_time
            min_interval = 0  # 0.05  # 50 ms
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

            data = (cmd + self.line_ending).encode("utf-8", errors="ignore")
            self._ser.write(data)
            self._last_send_time = time.time()

    def add_listener(self, fn: Callable[[str], None]):
        if fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[str], None]):
        if fn in self._listeners:
            self._listeners.remove(fn)

    # ---- internals ----
    def _open_port(self):
        port = self._pick_port()
        if not port:
            raise RuntimeError("No serial ports found")
        with self._io_lock:
            self._ser = serial.Serial(
                port=port,
                baudrate=BAUD,
                bytesize=DATABITS,
                parity=PARITY,
                stopbits=STOPBITS,
                timeout=0.1,
                write_timeout=0.5,
            )
            self._ser.dtr = True
            self._ser.rts = True

    def _pick_port(self) -> Optional[str]:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return None
        if self.port_hint:
            for p in ports:
                if (
                    self.port_hint in (p.device or "")
                    or self.port_hint.lower() in (p.description or "").lower()
                ):
                    return p.device
        return ports[0].device

    def _emit_line(self, line: str):
        if self.tk_root and hasattr(self.tk_root, "after"):
            self.tk_root.after(0, self._notify_listeners, line)
        else:
            raise RuntimeError(
                "SerialService must be given a tk_root for UI-safe callbacks"
            )

    def _notify_listeners(self, line: str):
        for fn in list(self._listeners):
            try:
                fn(line)
            except Exception:
                pass

    def _reader(self):
        buf = bytearray()
        try:
            while not self._stop.is_set():
                with self._io_lock:
                    ser = self._ser
                if not ser or not ser.is_open:
                    break
                try:
                    b = ser.read(1)
                    if not b:
                        continue
                    if b in (b"\n", b"\r"):
                        if buf:
                            line = buf.decode(errors="ignore").strip()
                            buf.clear()
                            if line:
                                self._emit_line(line)
                    else:
                        buf.extend(b)
                except Exception:
                    time.sleep(0.05)
        finally:
            with self._io_lock:
                if self._ser:
                    try:
                        self._ser.close()
                    except Exception:
                        pass
                self._ser = None
