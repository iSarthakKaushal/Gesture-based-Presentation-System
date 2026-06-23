from collections import deque

import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector


class GestureState:
    """Shared state between the webcam processor and Streamlit UI."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.gesture = "none"
        self.finger_count = 0
        self.hand_detected = False
        self.pointer = None
        self.drawing = False


class HandGestureProcessor:
    """Detect hand gestures for slide control and drawing."""

    GESTURE_THRESHOLD_RATIO = 0.42

    def __init__(self):
        self.detector = None
        self.state = GestureState()
        self.button_pressed = False
        self.counter = 0
        self.delay = 20
        self.smooth_points = deque(maxlen=10)

    def _get_detector(self) -> HandDetector:
        if self.detector is None:
            self.detector = HandDetector(detectionCon=0.8, maxHands=1)
        return self.detector

    def process(self, frame: np.ndarray) -> np.ndarray:
        detector = self._get_detector()
        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        threshold = int(height * self.GESTURE_THRESHOLD_RATIO)

        hands, frame = detector.findHands(frame)
        cv2.line(frame, (0, threshold), (width, threshold), (0, 255, 0), 3)

        self.state.gesture = "none"
        self.state.hand_detected = bool(hands)
        self.state.pointer = None
        self.state.drawing = False

        if hands and not self.button_pressed:
            hand = hands[0]
            lm_list = hand["lmList"]
            fingers = detector.fingersUp(hand)
            self.state.finger_count = sum(fingers)

            index_finger = (int(lm_list[8][0]), int(lm_list[8][1]))
            _, cy = hand["center"]

            if cy <= threshold:
                if fingers == [1, 0, 0, 0, 0]:
                    self.state.gesture = "prev"
                    self._press_button()
                elif fingers == [0, 0, 0, 0, 1]:
                    self.state.gesture = "next"
                    self._press_button()
                elif fingers == [0, 1, 1, 1, 0]:
                    self.state.gesture = "undo"
                    self._press_button()

            if fingers == [0, 1, 0, 0, 0]:
                self.state.gesture = "draw"
                self.state.drawing = True
                self.smooth_points.append(index_finger)
                avg_x = int(sum(point[0] for point in self.smooth_points) / len(self.smooth_points))
                avg_y = int(sum(point[1] for point in self.smooth_points) / len(self.smooth_points))
                self.state.pointer = (avg_x, avg_y)
            else:
                self.smooth_points.clear()

            if fingers == [0, 1, 1, 0, 0]:
                self.state.gesture = "pointer"
                self.state.pointer = index_finger

        if self.button_pressed:
            self.counter += 1
            if self.counter > self.delay:
                self.counter = 0
                self.button_pressed = False

        return frame

    def _press_button(self):
        self.button_pressed = True
        self.counter = 0
