import time


class Stopwatch:
    def __init__(self):
        self._start_time = None
        self._elapsed = 0
        self._running = False

    def start(self):
        if not self._running:
            self._start_time = time.perf_counter()
            self._running = True

    def stop(self):
        if self._running:
            self._elapsed += time.perf_counter() - self._start_time
            self._running = False

    def reset(self):
        self._start_time = None
        self._elapsed = 0
        self._running = False

    def elapsed_ms(self):
        if self._running:
            return (self._elapsed + time.perf_counter() - self._start_time) * 1000
        return self._elapsed * 1000
