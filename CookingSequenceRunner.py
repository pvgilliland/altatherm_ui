import threading
import time


class CookingSequenceRunner(threading.Thread):
    def __init__(self, sequence, zone_callback, name="ZONE", done_callback=None):
        super().__init__(daemon=True, name=name)
        self.sequence = sequence  # [(duration_sec, power_percent), ...]
        self.callback = zone_callback  # (zone_name, value_percent, duration)
        self.done_callback = done_callback
        self._stop_event = threading.Event()
        self.running = False

        # --- scaling support ---
        self._scale_supplier = lambda: 1.0  # returns float 0..1
        self._last_sent_scaled = None  # last scaled int(percent)
        self._current_target = 0  # current step's unscaled int(percent)

        # --- pause/resume support ---
        self._pause_event = threading.Event()  # set() => paused, clear() => running
        self._cut_on_pause = True
        self._paused_output_cut = (
            False  # tracks whether we've already cut to 0 while paused
        )

    # --- manager injects a getter so runners always see latest scale ---
    def set_scale_supplier(self, fn):
        self._scale_supplier = fn or (lambda: 1.0)

    # --- recompute scaled output and (if changed) resend immediately ---
    def apply_scale(self, scale: float | None = None):
        if not self.running:
            return

        s = self._safe_scale(scale)
        scaled = int(round(self._current_target * s))
        if scaled != self._last_sent_scaled:
            try:
                print(f"[{self.name}] RESCALE CALLBACK -> value={scaled}, duration=0")
                self.callback(self.name, scaled, 0)
            except Exception as e:
                print(f"[{self.name}] rescale callback error: {e}")
            self._last_sent_scaled = scaled

    def _safe_scale(self, scale):
        if scale is None:
            try:
                scale = float(self._scale_supplier())
            except Exception:
                scale = 1.0
        return max(0.0, min(1.0, float(scale)))

    # --- public pause/resume API ---
    def pause(self, cut_output: bool = True):
        """Pause the runner; optionally cut output to 0 while paused."""
        self._cut_on_pause = bool(cut_output)
        self._pause_event.set()

    def resume(self):
        """Resume from pause; immediately re-sends the correct scaled output."""
        self._pause_event.clear()
        # Force an immediate send on resume (covers any edge cases)
        if self.running:
            s = self._safe_scale(None)
            scaled = int(round(self._current_target * s))
            try:
                self.callback(self.name, scaled, 0)
            except Exception as e:
                print(f"[{self.name}] resume callback error: {e}")
            self._last_sent_scaled = scaled
        # Clear paused flag used by run-loop
        self._paused_output_cut = False

    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def run(self):
        self.running = True
        try:
            for duration, power in self.sequence:
                if self._stop_event.is_set():
                    break

                # power is % (0..100) from recipe
                self._current_target = int(power)
                s = self._safe_scale(None)
                scaled = int(round(self._current_target * s))
                self._last_sent_scaled = scaled

                print(
                    f"[{self.name}] Output: {scaled}% (target {self._current_target}%, scale {s:.2f}) for {duration} s"
                )
                try:
                    # Initial send for this step with full remaining duration
                    self.callback(self.name, scaled, duration)
                except Exception as e:
                    print(f"[{self.name}] step callback error: {e}")

                # Use an absolute end time so we can slide it forward during pauses
                end_time = time.time() + duration

                # While in this step, watch for stop, pause, and scale changes
                while True:
                    if self._stop_event.is_set():
                        break

                    now = time.time()
                    if now >= end_time:
                        break

                    if self._pause_event.is_set():
                        pause_started = time.time()

                        # Cut output once (if configured)
                        if self._cut_on_pause and not self._paused_output_cut:
                            try:
                                self.callback(self.name, 0, 0)
                            except Exception as e:
                                print(f"[{self.name}] pause callback error: {e}")
                            self._paused_output_cut = True
                            self._last_sent_scaled = (
                                0  # critical: ensure resume triggers a re-send
                            )

                        # Wait here until resumed or stopped
                        while (
                            self._pause_event.is_set() and not self._stop_event.is_set()
                        ):
                            time.sleep(0.1)

                        # Adjust end time to account for paused duration
                        paused_for = time.time() - pause_started
                        end_time += paused_for

                        # Restore output if we cut it on pause
                        if self._cut_on_pause and not self._stop_event.is_set():
                            # apply_scale() will re-send because _last_sent_scaled == 0
                            self.apply_scale()
                        continue

                    # poll scale ~10Hz; if changed, resend immediately
                    self.apply_scale()
                    time.sleep(0.1)

                if self._stop_event.is_set():
                    break

        finally:
            # Ensure output is reset for this zone
            try:
                self.callback(self.name, 0, 0)
            except Exception as e:
                print(f"[{self.name}] reset callback error: {e}")

            print(f"[{self.name}] Sequence complete.")
            self.running = False

            if self.done_callback:
                try:
                    self.done_callback(self.name)
                except Exception as e:
                    print(f"[{self.name}] done_callback error: {e}")

    def stop(self):
        """Signal the runner to stop at the next check."""
        self._stop_event.set()


class CookingSequenceManager:
    def __init__(self):
        self.runners = {}
        self._lock = threading.Lock()
        self._pending = 0
        self._on_all_complete = None
        self._completed_once = False

        # global scale for all zones (0..1)
        self._power_scale = 1.0

        # per-zone scale, keyed by runner name
        self._zone_scales = {}

    def set_on_all_complete(self, fn):
        self._on_all_complete = fn

    def _runner_finished(self, name):
        with self._lock:
            if self._pending > 0:
                self._pending -= 1
            last = self._pending == 0 and not self._completed_once
            if last:
                self._completed_once = True
        if last and self._on_all_complete:
            threading.Thread(target=self._on_all_complete, daemon=True).start()

    def _get_combined_scale_for_runner(self, runner_name: str) -> float:
        global_scale = float(self._power_scale)
        zone_scale = float(self._zone_scales.get(runner_name, 1.0))
        return max(0.0, min(1.0, global_scale * zone_scale))

    def _resolve_runner_name(self, zone) -> str | None:
        """
        Resolve an incoming zone identifier like:
            1
            "1"
            "ZONE1"
            "DAC1"
        to the actual key used in self.runners.
        """
        candidates = []

        # direct match first
        candidates.append(zone)
        candidates.append(str(zone))

        try:
            z = int(zone)
            candidates.extend(
                [
                    f"ZONE{z}",
                    f"Zone{z}",
                    f"zone{z}",
                    f"DAC{z}",
                    f"Dac{z}",
                    f"dac{z}",
                    f"ARRAY{z}",
                    f"Array{z}",
                    f"array{z}",
                ]
            )
        except Exception:
            pass

        for name in candidates:
            if name in self.runners:
                return name

        return None

    def add_dac(self, dac_name, sequence, set_voltage_callback):
        runner = CookingSequenceRunner(
            sequence,
            set_voltage_callback,
            name=dac_name,
            done_callback=self._runner_finished,
        )

        # supply live scale to runner: global * per-zone
        runner.set_scale_supplier(
            lambda name=dac_name: self._get_combined_scale_for_runner(name)
        )

        self.runners[dac_name] = runner
        self._zone_scales.setdefault(dac_name, 1.0)

    def start_all(self):
        with self._lock:
            self._pending = len(self.runners)
            self._completed_once = False
        for runner in self.runners.values():
            runner.start()

    def stop_all(self):
        for runner in self.runners.values():
            runner.stop()

    # --- pause/resume across all zones ---
    def pause_all(self, cut_output: bool = True):
        for r in self.runners.values():
            r.pause(cut_output)

    def resume_all(self):
        for r in self.runners.values():
            r.resume()

    def is_any_running(self):
        return any(runner.running for runner in self.runners.values())

    def is_any_paused(self):
        return any(r.is_paused() for r in self.runners.values())

    def get_status(self):
        return {name: runner.running for name, runner in self.runners.items()}

    # set & broadcast global power scale (0..1)
    def set_power_scale(self, scale: float):
        s = max(0.0, min(1.0, float(scale)))
        with self._lock:
            self._power_scale = s
            # Ask active runners to re-apply the scale right now
            for r in self.runners.values():
                r.apply_scale()

    def set_zone_scale(self, zone, scale: float):
        """
        Set scale for one selected zone/array and immediately update
        that runner's live output.
        """

        s = max(0.0, min(1.0, float(scale)))

        with self._lock:
            runner_name = self._resolve_runner_name(zone)

            if runner_name is None:
                print(
                    f"[CookingSequenceManager] set_zone_scale: zone not found: {zone}"
                )
                return

            self._zone_scales[runner_name] = s

            r = self.runners.get(runner_name)

            if r:
                r.apply_scale()

    def set_selected_zone_scale(self, zones, scale: float):
        for zone in zones:
            self.set_zone_scale(zone, scale)

    def set_all_zone_scales(self, scale: float):
        s = max(0.0, min(1.0, float(scale)))
        with self._lock:
            for name in self.runners.keys():
                self._zone_scales[name] = s
            for r in self.runners.values():
                r.apply_scale()

    def reset_zone_scales(self):
        self.set_all_zone_scales(1.0)
