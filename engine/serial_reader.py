import collections
import csv
import glob
import os
import threading
import time
from typing import Optional, List, Dict, Any
import serial

CSV_HEADER = [
    "t_ms", "temp_c", "flow_lpm", "pulses", "turb_mv", "turb_index_pct",
    "ec25_uScm", "tds_ppm", "fhi", "counter_life_pct", "pump", "lock",
    "state", "reason", "tag"
]

class SerialManager:
    """
    Manages serial communication with the Arduino Uno / ESP32.
    Spawns background reader thread, parses CSV rows, logs to file, and provides command dispatch.
    """
    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 115200, maxlen: int = 600):
        self.port = port
        self.baud = baud
        self.maxlen = maxlen
        self.buffer = collections.deque(maxlen=maxlen)
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.log_filepath: Optional[str] = None
        self.csv_file = None
        self.csv_writer = None
        self.lock = threading.Lock()
        self.last_error = ""

    @staticmethod
    def list_available_ports() -> List[str]:
        ports = []
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            pass
        if not ports:
            ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/tty.*")
        return sorted(list(set(ports)))

    def start(self, port: Optional[str] = None) -> bool:
        if port:
            self.port = port
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(1.8) # Allow Arduino auto-reset to settle
            self.running = True

            timestamp_str = time.strftime("run_%Y%m%d_%H%M%S.csv")
            self.log_filepath = os.path.join(os.getcwd(), timestamp_str)
            self.csv_file = open(self.log_filepath, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(CSV_HEADER)
            self.csv_file.flush()

            self.thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.thread.start()
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = str(e)
            self.running = False
            return False

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
        self.ser = None

    def _reader_loop(self):
        while self.running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) != len(CSV_HEADER) or parts[0] == "t_ms":
                    continue
                row_dict = dict(zip(CSV_HEADER, parts))
                with self.lock:
                    self.buffer.append(row_dict)
                    if self.csv_writer and self.csv_file:
                        self.csv_writer.writerow(parts)
                        self.csv_file.flush()
            except Exception as e:
                self.last_error = str(e)
                time.sleep(0.1)

    def send_command(self, cmd: str) -> bool:
        if not self.ser or not self.ser.is_open:
            return False
        try:
            clean_cmd = cmd.strip() + "\n"
            self.ser.write(clean_cmd.encode("ascii"))
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    def get_latest_frame(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            if self.buffer:
                return dict(self.buffer[-1])
        return None

    def get_all_buffered(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.buffer)
