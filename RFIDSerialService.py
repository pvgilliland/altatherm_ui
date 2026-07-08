import serial
import threading
import time


class RFIDSerialService:
    def __init__(
        self,
        tk_root=None,
        port="/dev/ttyUSB1",
        baudrate=115200,
        on_tag=None,
    ):
        self.tk_root = tk_root
        self.port = port
        self.baudrate = baudrate
        self.on_tag = on_tag

        self.ser = None
        self.running = False
        self.thread = None

    def start(self):
        self.ser = serial.Serial(
            self.port,
            self.baudrate,
            timeout=0.1
        )

        self.running = True
        self.thread = threading.Thread(
            target=self._read_loop,
            daemon=True
        )
        self.thread.start()

    def stop(self):
        self.running = False

        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass

    def _read_loop(self):
        buffer = ""

        while self.running:
            try:
                if not self.ser:
                    time.sleep(0.1)
                    continue

                data = self.ser.read(64)

                if not data:
                    continue

                text = data.decode(errors="ignore")
                buffer += text

                while "\r" in buffer or "\n" in buffer:
                    split_points = [
                        p for p in [buffer.find("\r"), buffer.find("\n")]
                        if p >= 0
                    ]
                    idx = min(split_points)

                    line = buffer[:idx].strip()
                    buffer = buffer[idx + 1:]

                    if line:
                        self._handle_tag(line)

            except Exception as e:
                print(f"[RFID] Read error: {e}")
                time.sleep(0.5)

    def _handle_tag(self, tag_id):
        if self.tk_root and self.on_tag:
            self.tk_root.after(0, self.on_tag, tag_id)
        elif self.on_tag:
            self.on_tag(tag_id)