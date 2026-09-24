"""Background thread: webcam capture, marker detection, angle -> A/D key output.

Runs as a plain Python thread driven by cv2.VideoCapture directly (not by
Gradio's webcam component), so steering keeps working while ETS2 has window
focus and the browser tab is backgrounded.
"""

import threading
import time

import cv2
import numpy as np
import pydirectinput

pydirectinput.PAUSE = 0  # no artificial delay between key events

SMOOTHING = 0.5  # exponential moving average weight for the previous angle
MIN_MARKER_AREA = 400  # px; below this it's noise (skin, lips, reflections), not the marker


class Tracker:
    def __init__(self, state, camera_index=0):
        self.state = state
        self.camera_index = camera_index
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.state.set_status("running")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._release_keys()
        self.state.set_status("stopped")

    def _release_keys(self):
        pydirectinput.keyUp("a")
        pydirectinput.keyUp("d")

    def _find_marker(self, hsv, color_range):
        h_min, s_min, v_min, h_max, s_max, v_max = color_range
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, lower, upper)
        # Heavier erosion than dilation: a taped-flat sticky note survives as a
        # solid blob, but thin/uneven false positives (lip highlights, skin
        # specks) shrink away before the dilate step brings them back.
        mask = cv2.erode(mask, None, iterations=3)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, mask
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < MIN_MARKER_AREA:
            return None, mask
        moments = cv2.moments(largest)
        if moments["m00"] == 0:
            return None, mask
        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
        return (cx, cy), mask

    def _run(self):
        cap = cv2.VideoCapture(self.camera_index)
        smoothed_angle = 0.0
        key_state = None

        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame = cv2.flip(frame, 1)  # mirror so left/right match the user's view
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                pink_range, green_range = self.state.get_ranges()
                left, pink_mask = self._find_marker(hsv, pink_range)
                right, green_mask = self._find_marker(hsv, green_range)

                mask_view = np.zeros_like(frame)
                mask_view[pink_mask > 0] = (255, 0, 255)  # BGR magenta
                mask_view[green_mask > 0] = (0, 255, 0)  # BGR green

                raw_angle = None
                if left and right:
                    dx = right[0] - left[0]
                    dy = right[1] - left[1]
                    raw_angle = float(np.degrees(np.arctan2(dy, dx)))
                    smoothed_angle = SMOOTHING * smoothed_angle + (1 - SMOOTHING) * raw_angle

                    neutral = self.state.get_neutral()
                    dead_zone = self.state.get_dead_zone()
                    offset = smoothed_angle - neutral

                    if offset > dead_zone:
                        desired = "D"
                    elif offset < -dead_zone:
                        desired = "A"
                    else:
                        desired = None

                    if desired != key_state:
                        if key_state == "A":
                            pydirectinput.keyUp("a")
                        elif key_state == "D":
                            pydirectinput.keyUp("d")
                        if desired == "A":
                            pydirectinput.keyDown("a")
                        elif desired == "D":
                            pydirectinput.keyDown("d")
                        key_state = desired

                    cv2.line(frame, left, right, (0, 255, 255), 2)
                    cv2.circle(frame, left, 8, (180, 0, 255), -1)
                    cv2.circle(frame, right, 8, (0, 255, 0), -1)
                    cv2.putText(
                        frame,
                        f"angle: {offset:+.1f} deg  key: {key_state or '-'}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2,
                    )
                else:
                    if key_state is not None:
                        self._release_keys()
                        key_state = None
                    cv2.putText(
                        frame,
                        "marker(s) not detected",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb_mask_view = cv2.cvtColor(mask_view, cv2.COLOR_BGR2RGB)
                self.state.set_frame(rgb_frame, rgb_mask_view, raw_angle, smoothed_angle, key_state)

        finally:
            cap.release()
            self._release_keys()
