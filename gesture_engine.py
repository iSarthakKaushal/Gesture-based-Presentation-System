from collections import deque
from dataclasses import dataclass
from threading import Lock
import time

import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector


@dataclass
class GestureState:
    gesture: str = "none"
    finger_count: int = 0
    hand_detected: bool = False
    pointer: tuple | None = None
    drawing: bool = False
    timestamp: float = 0.0


class HandGestureProcessor:
    """
    Thread-safe gesture processor.

    Gestures:
        prev     -> thumb only above threshold
        next     -> pinky only above threshold
        undo     -> index+middle+ring above threshold
        draw     -> index finger only
        pointer  -> index+middle
    """

    GESTURE_THRESHOLD_RATIO = 0.42

    NAVIGATION_COOLDOWN = 0.8
    UNDO_COOLDOWN = 0.8

    def __init__(self):
        self._detector = None

        self._lock = Lock()

        self.state = GestureState()

        self.smooth_points = deque(maxlen=10)

        self.last_prev_time = 0.0
        self.last_next_time = 0.0
        self.last_undo_time = 0.0
        self._frame_width = 640
        self._frame_height = 480

    # --------------------------------------------------
    # Detector
    # --------------------------------------------------

    def _get_detector(self):
        if self._detector is None:
            self._detector = HandDetector(
                detectionCon=0.8,
                maxHands=1,
            )
        return self._detector

    # --------------------------------------------------
    # State Helpers
    # --------------------------------------------------

    def _update_state(
        self,
        gesture="none",
        finger_count=0,
        hand_detected=False,
        pointer=None,
        drawing=False,
    ):
        with self._lock:
            self.state.gesture = gesture
            self.state.finger_count = finger_count
            self.state.hand_detected = hand_detected
            self.state.pointer = pointer
            self.state.drawing = drawing
            self.state.timestamp = time.time()

    def get_state_snapshot(self):
        """
        Safe read for Streamlit/UI thread.
        """

        with self._lock:
            return {
                "gesture": self.state.gesture,
                "finger_count": self.state.finger_count,
                "hand_detected": self.state.hand_detected,
                "pointer": self.state.pointer,
                "drawing": self.state.drawing,
                "timestamp": self.state.timestamp,
                "frame_width": self._frame_width,
                "frame_height": self._frame_height,
            }

    # --------------------------------------------------
    # Cooldown Helpers
    # --------------------------------------------------

    def _can_trigger_prev(self):
        now = time.time()

        if now - self.last_prev_time >= self.NAVIGATION_COOLDOWN:
            self.last_prev_time = now
            return True

        return False

    def _can_trigger_next(self):
        now = time.time()

        if now - self.last_next_time >= self.NAVIGATION_COOLDOWN:
            self.last_next_time = now
            return True

        return False

    def _can_trigger_undo(self):
        now = time.time()

        if now - self.last_undo_time >= self.UNDO_COOLDOWN:
            self.last_undo_time = now
            return True

        return False

    # --------------------------------------------------
    # Main Processing
    # --------------------------------------------------

    def process(self, frame: np.ndarray) -> np.ndarray:
        detector = self._get_detector()

        frame = cv2.flip(frame, 1)

        height, width = frame.shape[:2]

        threshold = int(
            height * self.GESTURE_THRESHOLD_RATIO
        )

        hands, frame = detector.findHands(frame)

        cv2.line(
            frame,
            (0, threshold),
            (width, threshold),
            (0, 255, 0),
            3,
        )

        self._update_state(
            gesture="none",
            finger_count=0,
            hand_detected=bool(hands),
            pointer=None,
            drawing=False,
        )

        if not hands:
            self.smooth_points.clear()
            self._frame_width = width
            self._frame_height = height
            return frame

        hand = hands[0]

        lm_list = hand["lmList"]

        fingers = detector.fingersUp(hand)

        finger_count = sum(fingers)

        index_finger = (
            int(lm_list[8][0]),
            int(lm_list[8][1]),
        )

        _, center_y = hand["center"]

        gesture = "none"
        pointer = None
        drawing = False

        # ------------------------------------------
        # Navigation Zone (above green line)
        # ------------------------------------------

        if center_y <= threshold:

            # PREVIOUS
            if fingers == [1, 0, 0, 0, 0]:

                if self._can_trigger_prev():
                    gesture = "prev"

            # NEXT
            elif fingers == [0, 0, 0, 0, 1]:

                if self._can_trigger_next():
                    gesture = "next"

            # UNDO
            elif fingers == [0, 1, 1, 1, 0]:

                if self._can_trigger_undo():
                    gesture = "undo"

        # ------------------------------------------
        # Drawing Mode
        # ------------------------------------------

        if fingers == [0, 1, 0, 0, 0]:

            gesture = "draw"
            drawing = True

            self.smooth_points.append(
                index_finger
            )

            avg_x = int(
                sum(p[0] for p in self.smooth_points)
                / len(self.smooth_points)
            )

            avg_y = int(
                sum(p[1] for p in self.smooth_points)
                / len(self.smooth_points)
            )

            pointer = (
                avg_x,
                avg_y,
            )

            cv2.circle(
                frame,
                pointer,
                12,
                (0, 0, 255),
                cv2.FILLED,
            )

        else:
            self.smooth_points.clear()

        # ------------------------------------------
        # Pointer Mode
        # ------------------------------------------

        if fingers == [0, 1, 1, 0, 0]:

            gesture = "pointer"

            pointer = index_finger

            cv2.circle(
                frame,
                pointer,
                12,
                (255, 0, 255),
                cv2.FILLED,
            )

        # ------------------------------------------
        # UI Overlay
        # ------------------------------------------

        cv2.putText(
            frame,
            f"Gesture: {gesture}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2,
        )

        self._update_state(
            gesture=gesture,
            finger_count=finger_count,
            hand_detected=True,
            pointer=pointer,
            drawing=drawing,
        )

        self._frame_width = width
        self._frame_height = height

        return frame