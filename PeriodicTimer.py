import threading
import time


# PeriodicTimer is derived from threading.Thread,
# threading.Thread defines the start() method
class PeriodicTimer(threading.Thread):
    def __init__(self, interval_s, callback):
        super().__init__(
            daemon=True
        )  # daemon=True: Thread automatically exits when the main program exits
        self.interval = interval_s
        self.callback = callback
        self._stop_event = threading.Event()

    def run(self):
        next_time = time.perf_counter()
        while not self._stop_event.is_set():
            self.callback()
            next_time += self.interval
            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                print("Callback overrun!")
                next_time = time.perf_counter()

    def stop(self):
        self._stop_event.set()


# Example usage
# def my_task():
#     print(f"Tick at {time.perf_counter():.3f} seconds")

# timer = PeriodicTimer(0.5, my_task)  # 500 ms
# timer.start()

# # Let it run for 5 seconds
# time.sleep(5)
# timer.stop()
