import os
import threading
from dataclasses import dataclass

import cv2
import numpy as np
import streamlit as st
from av import VideoFrame
from PIL import Image
from streamlit_autorefresh import st_autorefresh
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from gesture_engine import HandGestureProcessor
from slide_utils import (
    clear_folder,
    convert_ppt_to_images,
    load_slide_paths,
    prepare_slide_folder,
    save_uploaded_images,
)

st.set_page_config(
    page_title="Gesture Presentation System",
    page_icon="🖐️",
    layout="wide",
)


@dataclass
class SharedGestureState:
    gesture: str = "none"
    pointer: tuple | None = None
    drawing: bool = False
    hand_detected: bool = False
    timestamp: float = 0.0
    frame_width: int = 640
    frame_height: int = 480


shared_lock = threading.Lock()

if "shared_gesture_state" not in st.session_state:
    st.session_state.shared_gesture_state = SharedGestureState()
if "gesture_processor" not in st.session_state:
    st.session_state.gesture_processor = HandGestureProcessor()
if "slide_paths" not in st.session_state:
    st.session_state.slide_paths = []
if "slide_folder" not in st.session_state:
    st.session_state.slide_folder = ""
if "cleanup_folder" not in st.session_state:
    st.session_state.cleanup_folder = False
if "current_slide" not in st.session_state:
    st.session_state.current_slide = 0
if "annotations" not in st.session_state:
    st.session_state.annotations = []
if "annotation_number" not in st.session_state:
    st.session_state.annotation_number = -1
if "last_timestamp" not in st.session_state:
    st.session_state.last_timestamp = 0.0
if "brush_color" not in st.session_state:
    st.session_state.brush_color = "#FF0000"
if "brush_thickness" not in st.session_state:
    st.session_state.brush_thickness = 8

shared_state = st.session_state.shared_gesture_state
gesture_processor = st.session_state.gesture_processor


class GestureVideoProcessor:
    def recv(self, frame: VideoFrame) -> VideoFrame:
        image = frame.to_ndarray(format="bgr24")
        processed = gesture_processor.process(image)
        state = gesture_processor.get_state_snapshot()

        with shared_lock:
            shared_state.gesture = state["gesture"]
            shared_state.pointer = state["pointer"]
            shared_state.drawing = state["drawing"]
            shared_state.hand_detected = state["hand_detected"]
            shared_state.timestamp = state["timestamp"]
            shared_state.frame_width = state.get("frame_width", 640)
            shared_state.frame_height = state.get("frame_height", 480)

        return VideoFrame.from_ndarray(processed, format="bgr24")


def reset_annotations():
    st.session_state.annotations = []
    st.session_state.annotation_number = -1


def add_annotation_point(point):
    if st.session_state.annotation_number < 0:
        st.session_state.annotation_number = 0
        st.session_state.annotations.append([])
    idx = st.session_state.annotation_number
    if idx >= len(st.session_state.annotations):
        st.session_state.annotations.append([])
    st.session_state.annotations[idx].append(point)


def set_slides(slide_paths, folder="", cleanup=False):
    if (
        st.session_state.cleanup_folder
        and st.session_state.slide_folder
        and st.session_state.slide_folder != folder
    ):
        clear_folder(st.session_state.slide_folder)

    st.session_state.slide_paths = slide_paths
    st.session_state.slide_folder = folder
    st.session_state.cleanup_folder = cleanup
    st.session_state.current_slide = 0
    reset_annotations()


def hex_to_bgr(color_hex: str) -> tuple[int, int, int]:
    value = color_hex.lstrip("#")
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return b, g, r


def render_slide(image_path: str, width: int = 1280, height: int = 720) -> np.ndarray:
    slide = cv2.imread(image_path)
    if slide is None:
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(
            canvas,
            "Unable to load slide",
            (50, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        return canvas

    h, w = slide.shape[:2]
    scale = min(width / w, height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(slide, (new_w, new_h))

    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x = (width - new_w) // 2
    y = (height - new_h) // 2
    canvas[y : y + new_h, x : x + new_w] = resized
    return canvas


def draw_annotations(canvas, color, thickness):
    for annotation in st.session_state.annotations:
        if len(annotation) > 1:
            pts = np.array(annotation, np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts], False, color, thickness)
        elif len(annotation) == 1:
            cv2.circle(canvas, annotation[0], thickness, color, cv2.FILLED)


def scale_pointer(pointer, src_width, src_height, dst_width=1280, dst_height=720):
    if src_width <= 0 or src_height <= 0:
        return pointer
    x = int(pointer[0] * dst_width / src_width)
    y = int(pointer[1] * dst_height / src_height)
    return max(0, min(x, dst_width - 1)), max(0, min(y, dst_height - 1))


def apply_gesture(gesture):
    total = len(st.session_state.slide_paths)
    if gesture == "prev" and st.session_state.current_slide > 0:
        st.session_state.current_slide -= 1
        reset_annotations()
    elif gesture == "next" and st.session_state.current_slide < total - 1:
        st.session_state.current_slide += 1
        reset_annotations()
    elif gesture == "undo" and st.session_state.annotations:
        st.session_state.annotations.pop()
        st.session_state.annotation_number -= 1


def render_slide_panel():
    if not st.session_state.slide_paths:
        placeholder = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(
            placeholder,
            "Upload slides to begin",
            (320, 360),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 255, 255),
            2,
        )
        st.image(cv2.cvtColor(placeholder, cv2.COLOR_BGR2RGB), use_container_width=True)
        return

    slide_index = st.session_state.current_slide
    slide_count = len(st.session_state.slide_paths)
    slide_canvas = render_slide(st.session_state.slide_paths[slide_index])
    brush_bgr = hex_to_bgr(st.session_state.brush_color)
    thickness = st.session_state.brush_thickness

    with shared_lock:
        gesture = shared_state.gesture
        pointer = shared_state.pointer
        drawing = shared_state.drawing
        hand_detected = shared_state.hand_detected
        timestamp = shared_state.timestamp
        frame_width = shared_state.frame_width
        frame_height = shared_state.frame_height

    scaled_pointer = None
    if pointer is not None:
        scaled_pointer = scale_pointer(pointer, frame_width, frame_height)

    if timestamp != st.session_state.last_timestamp:
        st.session_state.last_timestamp = timestamp
        if gesture in ("prev", "next", "undo"):
            apply_gesture(gesture)

    if drawing and scaled_pointer is not None:
        add_annotation_point(scaled_pointer)

    if gesture == "pointer" and scaled_pointer is not None:
        cv2.circle(slide_canvas, scaled_pointer, thickness, brush_bgr, cv2.FILLED)

    draw_annotations(slide_canvas, brush_bgr, thickness)

    st.progress(
        (slide_index + 1) / slide_count,
        text=f"Slide {slide_index + 1} of {slide_count}",
    )
    st.image(cv2.cvtColor(slide_canvas, cv2.COLOR_BGR2RGB), use_container_width=True)

    if hand_detected:
        st.success(f"Gesture: **{gesture}**")
    else:
        st.warning("No hand detected — click **START** on the webcam and allow camera access.")


# --- Header ---
st.title("🖐️ Gesture Based Presentation System")
st.caption("Control presentations using hand gestures.")

# --- Sidebar ---
with st.sidebar:
    st.header("Slides")

    ppt_file = st.file_uploader("Upload PowerPoint", type=["pptx"])
    image_files = st.file_uploader(
        "Upload Slide Images",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
    )

    if st.button("Load PowerPoint", use_container_width=True, disabled=ppt_file is None):
        folder, cleanup = prepare_slide_folder()
        ppt_path = os.path.join(folder, "presentation.pptx")
        with open(ppt_path, "wb") as handle:
            handle.write(ppt_file.getbuffer())
        try:
            convert_ppt_to_images(ppt_path, folder)
            slides = load_slide_paths(folder)
            set_slides(slides, folder, cleanup)
            st.success(f"{len(slides)} slides loaded.")
        except Exception as exc:
            clear_folder(folder)
            st.error(str(exc))
            st.info("On cloud hosting, upload PNG/JPG images instead of .pptx.")

    if st.button("Load Images", use_container_width=True, disabled=not image_files):
        folder, cleanup = prepare_slide_folder()
        slides = save_uploaded_images(image_files, folder)
        set_slides(slides, folder, cleanup)
        st.success(f"{len(slides)} slides loaded.")

    st.divider()

    st.session_state.brush_color = st.color_picker(
        "Brush Color",
        st.session_state.brush_color,
    )
    st.session_state.brush_thickness = st.slider(
        "Brush Thickness",
        min_value=2,
        max_value=20,
        value=st.session_state.brush_thickness,
    )

    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("◀ Previous", use_container_width=True):
            if st.session_state.current_slide > 0:
                st.session_state.current_slide -= 1
                reset_annotations()
    with next_col:
        if st.button("Next ▶", use_container_width=True):
            if st.session_state.current_slide < len(st.session_state.slide_paths) - 1:
                st.session_state.current_slide += 1
                reset_annotations()

    if st.button("Clear Drawings", use_container_width=True):
        reset_annotations()

    st.divider()
    st.markdown(
        """
**Gestures** (above green line = navigate)

| Fingers | Action |
|---------|--------|
| Thumb only | Previous |
| Pinky only | Next |
| Index only | Draw |
| Index + Middle | Pointer |
| Index + Middle + Ring | Undo |
"""
    )
    st.info("Click **START** on the webcam, then allow camera access.")

# Refresh slide panel while webcam is running (no fragment — avoids white screen)
st_autorefresh(interval=400, key="gesture_refresh")

# --- Main layout ---
left_col, right_col = st.columns([1.5, 1])

with left_col:
    st.subheader("Presentation")
    render_slide_panel()

with right_col:
    st.subheader("Webcam")
    webrtc_streamer(
        key="gesture-webcam",
        mode=WebRtcMode.SENDRECV,
        async_processing=True,
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
        media_stream_constraints={"video": True, "audio": False},
        video_processor_factory=GestureVideoProcessor,
    )

# --- Thumbnails ---
if st.session_state.slide_paths:
    st.divider()
    st.subheader("Slides")
    cols_per_row = 4
    for row_start in range(0, len(st.session_state.slide_paths), cols_per_row):
        row_slides = st.session_state.slide_paths[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_index, slide_path in enumerate(row_slides):
            index = row_start + col_index
            with cols[col_index]:
                try:
                    st.image(Image.open(slide_path), use_container_width=True)
                except Exception:
                    st.error("Thumbnail error")
                if st.button(f"Slide {index + 1}", key=f"slide_{index}", use_container_width=True):
                    st.session_state.current_slide = index
                    reset_annotations()

st.markdown("---")
st.caption("Gesture Based Presentation System · [GitHub](https://github.com/iSarthakKaushal/Gesture-based-Presentation-System)")
