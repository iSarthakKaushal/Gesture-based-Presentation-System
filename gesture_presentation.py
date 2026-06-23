from cvzone.HandTrackingModule import HandDetector
import cv2
import os
import numpy as np
from tkinter import filedialog, Tk
from collections import deque
import shutil

from slide_utils import convert_ppt_to_images, load_slide_paths, normalize_path

# ---------------------- Select PowerPoint File ----------------------
root = Tk()
root.withdraw()

ppt_file = filedialog.askopenfilename(
    title="Select PowerPoint (Cancel = use existing Presentation folder)",
    filetypes=[
        ("PowerPoint files", "*.pptx;*.ppt"),
        ("All files", "*.*"),
    ],
)

folderPath = "Presentation"

if not ppt_file:
    pathImages = [os.path.basename(p) for p in load_slide_paths(folderPath)]
    if pathImages:
        print(f"Using {len(pathImages)} existing slides in Presentation/")
    else:
        print("No file selected and Presentation folder is empty.")
        exit()
else:
    ppt_file = normalize_path(ppt_file)
    print(f"Opening: {ppt_file}")

    if not os.path.isfile(ppt_file):
        print(f"File does not exist: {ppt_file}")
        print("If on OneDrive: right-click file -> Always keep on this device")
        exit(1)

    if os.path.exists(folderPath):
        shutil.rmtree(folderPath)
    os.makedirs(folderPath)

    try:
        convert_ppt_to_images(ppt_file, folderPath)
    except Exception as exc:
        print(f"\nPowerPoint conversion failed: {exc}")
        print("\nTips:")
        print("  - Save the file locally (not OneDrive online-only)")
        print("  - Close PowerPoint if that file is already open")
        print("  - Put PNG slides in Presentation/ and run again (click Cancel)")
        exit(1)

    pathImages = [os.path.basename(p) for p in load_slide_paths(folderPath)]
    if not pathImages:
        print("No slide images found after conversion.")
        exit(1)

    print(f"Loaded {len(pathImages)} slides.")

# ---------------------- Webcam Setup ----------------------
width, height = 1280, 720

cap = cv2.VideoCapture(0)
cap.set(3, width)
cap.set(4, height)

detector = HandDetector(detectionCon=0.8, maxHands=1)

# ---------------------- Variables ----------------------
imgNumber = 0
gestureThreshold = 300

annotations = []
annotationNumber = -1
annotationStart = False

brushColor = (0, 0, 255)
brushThickness = 10

buttonPressed = False
counter = 0
delay = 20

ws, hs = 213, 120

smoothPoints = deque(maxlen=10)

# ---------------------- Fullscreen Window ----------------------
cv2.namedWindow("Slides", cv2.WINDOW_NORMAL)
cv2.setWindowProperty(
    "Slides",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)

# ---------------------- Main Loop ----------------------
while True:

    success, img = cap.read()

    if not success:
        break

    img = cv2.flip(img, 1)

    # ---------------------- Load Slide ----------------------
    pathFullImage = os.path.join(folderPath, pathImages[imgNumber])

    imgSlide = cv2.imread(pathFullImage)

    h0, w0 = imgSlide.shape[:2]

    scale = min(width / w0, height / h0)

    new_w = int(w0 * scale)
    new_h = int(h0 * scale)

    imgSlide = cv2.resize(imgSlide, (new_w, new_h))

    canvas = np.zeros((height, width, 3), dtype=np.uint8)

    x_offset = (width - new_w) // 2
    y_offset = (height - new_h) // 2

    canvas[
        y_offset:y_offset + new_h,
        x_offset:x_offset + new_w
    ] = imgSlide

    # ---------------------- Hand Detection ----------------------
    hands, img = detector.findHands(img)

    cv2.line(
        img,
        (0, gestureThreshold),
        (width, gestureThreshold),
        (0, 255, 0),
        5
    )

    if hands and not buttonPressed:

        hand = hands[0]

        lmList = hand["lmList"]
        fingers = detector.fingersUp(hand)

        indexFinger = (
            int(lmList[8][0]),
            int(lmList[8][1])
        )

        cx, cy = hand["center"]

        # ---------------------- Previous Slide ----------------------
        if cy <= gestureThreshold:

            # Left gesture
            if fingers == [1, 0, 0, 0, 0]:

                if imgNumber > 0:
                    imgNumber -= 1

                    annotations = []
                    annotationNumber = -1
                    annotationStart = False

                    buttonPressed = True

            # Right gesture
            elif fingers == [0, 0, 0, 0, 1]:

                if imgNumber < len(pathImages) - 1:
                    imgNumber += 1

                    annotations = []
                    annotationNumber = -1
                    annotationStart = False

                    buttonPressed = True

        # ---------------------- Drawing Mode ----------------------
        if fingers == [0, 1, 0, 0, 0]:

            smoothPoints.append(indexFinger)

            avgX = int(sum(p[0] for p in smoothPoints) / len(smoothPoints))
            avgY = int(sum(p[1] for p in smoothPoints) / len(smoothPoints))

            smoothedPoint = (avgX, avgY)

            if not annotationStart:

                annotationStart = True
                annotationNumber += 1

                annotations.append([])

            annotations[annotationNumber].append(smoothedPoint)

        else:

            annotationStart = False
            smoothPoints.clear()

        # ---------------------- Pointer Mode ----------------------
        if fingers == [0, 1, 1, 0, 0]:

            cv2.circle(
                canvas,
                indexFinger,
                brushThickness,
                brushColor,
                cv2.FILLED
            )

        # ---------------------- Undo Gesture ----------------------
        if fingers == [0, 1, 1, 1, 0]:

            if len(annotations) > 0:

                annotations.pop()

                annotationNumber -= 1

                buttonPressed = True

    # ---------------------- Gesture Delay ----------------------
    if buttonPressed:

        counter += 1

        if counter > delay:

            counter = 0
            buttonPressed = False

    # ---------------------- Draw Annotations ----------------------
    for annotation in annotations:

        if len(annotation) > 1:

            pts = np.array(annotation, np.int32)
            pts = pts.reshape((-1, 1, 2))

            cv2.polylines(
                canvas,
                [pts],
                False,
                brushColor,
                brushThickness
            )

    # ---------------------- Webcam Inset ----------------------
    imgSmall = cv2.resize(img, (ws, hs))

    canvas[10:10 + hs, 10:10 + ws] = imgSmall

    # ---------------------- Display ----------------------
    cv2.imshow("Slides", canvas)

    key = cv2.waitKey(1)

    if key == ord('q'):
        break

# ---------------------- Cleanup ----------------------
cap.release()
cv2.destroyAllWindows()