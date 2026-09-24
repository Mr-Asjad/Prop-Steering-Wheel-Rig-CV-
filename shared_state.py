"""Thread-safe state shared between the tracker thread and the Gradio UI.

The tracker thread writes new frames/angles here; the UI polls it. All access
goes through a lock since two threads touch this at once.
"""

import threading


class SharedState:
    def __init__(self):
        self._lock = threading.Lock()

        # HSV ranges: [h_min, s_min, v_min, h_max, s_max, v_max]
        # Loose starting ranges -- narrow these with the sliders while
        # watching "Show color masks" in the UI.
        self.pink_range = [130, 100, 50, 179, 255, 255]
        self.green_range = [25, 50, 50, 90, 255, 255]

        self.dead_zone_deg = 8.0
        self.neutral_angle = 0.0

        self.raw_angle = None
        self.smoothed_angle = 0.0
        self.key_state = None  # None, "A", or "D"

        self.preview_frame = None  # last annotated frame, RGB numpy array
        self.mask_frame = None  # last color-mask debug view, RGB numpy array
        self.show_mask = False
        self.status = "stopped"

    def get_ranges(self):
        with self._lock:
            return tuple(self.pink_range), tuple(self.green_range)

    def set_pink_range(self, values):
        with self._lock:
            self.pink_range = list(values)

    def set_green_range(self, values):
        with self._lock:
            self.green_range = list(values)

    def set_dead_zone(self, value):
        with self._lock:
            self.dead_zone_deg = float(value)

    def get_dead_zone(self):
        with self._lock:
            return self.dead_zone_deg

    def set_neutral_to_current(self):
        with self._lock:
            if self.raw_angle is not None:
                self.neutral_angle = self.raw_angle
        return self.neutral_angle

    def get_neutral(self):
        with self._lock:
            return self.neutral_angle

    def set_frame(self, frame, mask_frame, raw_angle, smoothed_angle, key_state):
        with self._lock:
            self.preview_frame = frame
            self.mask_frame = mask_frame
            self.raw_angle = raw_angle
            self.smoothed_angle = smoothed_angle
            self.key_state = key_state

    def get_frame(self):
        with self._lock:
            return self.preview_frame, self.mask_frame, self.raw_angle, self.smoothed_angle, self.key_state

    def set_show_mask(self, value):
        with self._lock:
            self.show_mask = bool(value)

    def get_show_mask(self):
        with self._lock:
            return self.show_mask

    def set_status(self, status):
        with self._lock:
            self.status = status

    def get_status(self):
        with self._lock:
            return self.status
