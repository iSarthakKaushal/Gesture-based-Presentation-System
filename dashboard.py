import os

import cv2
import numpy as np
import streamlit as st
from av import VideoFrame
from PIL import Image
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
    page_title="Hand Gesture Presentation",
    page_icon="🖐️",
    layout="wide",
)

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
if "last_gesture" not in st.session_state:
    st.session_state.last_gesture = "none"
if "gesture_processor" not in st.session_state:
    st.session_state.gesture_processor = None


def reset_annotations():
    st.session_state.annotations = []
    st.session_state.annotation_number = -1


def set_slides(paths: list[str], folder: str = "", cleanup: bool = False):
    if (
        st.session_state.cleanup_folder
        and st.session_state.slide_folder
        and st.session_state.slide_folder != folder
    ):
        clear_folder(st.session_state.slide_folder)

    st.session_state.slide_paths = paths
    st.session_state.slide_folder = folder
    st.session_state.cleanup_folder = cleanup
    st.session_state.current_slide = 0
    reset_annotations()


def render_slide(path: str, width: int, height: int) -> np.ndarray:
    slide = cv2.imread(path)
    if slide is None:
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(
            canvas,
            "Unable to load slide",
            (40, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        return canvas

    slide_h, slide_w = slide.shape[:2]
    scale = min(width / slide_w, height / slide_h)
    new_w = int(slide_w * scale)
    new_h = int(slide_h * scale)
    resized = cv2.resize(slide, (new_w, new_h))

    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x_offset = (width - new_w) // 2
    y_offset = (height - new_h) // 2
    canvas[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = resized
    return canvas


def draw_annotations(canvas: np.ndarray, color: tuple[int, int, int], thickness: int):
    for annotation in st.session_state.annotations:
        if len(annotation) > 1:
            points = np.array(annotation, np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [points], False, color, thickness)
        elif len(annotation) == 1:
            cv2.circle(canvas, annotation[0], thickness, color, cv2.FILLED)


def hex_to_bgr(color_hex: str) -> tuple[int, int, int]:
    value = color_hex.lstrip("#")
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return b, g, r


def apply_navigation_gesture(gesture: str):
    if gesture == st.session_state.last_gesture:
        return

    st.session_state.last_gesture = gesture

    if gesture == "prev" and st.session_state.current_slide > 0:
        st.session_state.current_slide -= 1
        reset_annotations()
    elif (
        gesture == "next"
        and st.session_state.current_slide < len(st.session_state.slide_paths) - 1
    ):
        st.session_state.current_slide += 1
        reset_annotations()
    elif gesture == "undo" and st.session_state.annotations:
        st.session_state.annotations.pop()
        st.session_state.annotation_number -= 1


def append_draw_point(pointer: tuple[int, int]):
    if st.session_state.annotation_number < 0:
        st.session_state.annotation_number = 0
        st.session_state.annotations.append([])

    if not st.session_state.annotations:
        st.session_state.annotations.append([])

    st.session_state.annotations[st.session_state.annotation_number].append(pointer)

def get_gesture_processor() -> HandGestureProcessor:
    if st.session_state.gesture_processor is None:
        st.session_state.gesture_processor = HandGestureProcessor()
    return st.session_state.gesture_processor


class GestureVideoProcessor:
    def __init__(self):
        self.processor = get_gesture_processor()

    def recv(self, frame: VideoFrame) -> VideoFrame:
        image = frame.to_ndarray(format="bgr24")
        processed = self.processor.process(image)
        return VideoFrame.from_ndarray(processed, format="bgr24")


st.title("Hand Gesture Presentation Dashboard")
st.caption("Upload slides, enable your webcam, and control the deck with hand gestures.")

with st.sidebar:
    st.header("Upload Slides")

    ppt_file = st.file_uploader("PowerPoint (.pptx)", type=["pptx"])
    image_files = st.file_uploader(
        "Or upload slide images",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
    )

    if st.button("Load PowerPoint", use_container_width=True, disabled=ppt_file is None):
        folder, cleanup = prepare_slide_folder()
        temp_ppt = os.path.join(folder, "upload.pptx")
        with open(temp_ppt, "wb") as handle:
            handle.write(ppt_file.getbuffer())

        try:
            convert_ppt_to_images(os.path.abspath(temp_ppt), folder)
            paths = load_slide_paths(folder)
            if not paths:
                st.error("No slides were generated. Make sure PowerPoint is installed.")
            else:
                set_slides(paths, folder, cleanup)
                st.success(f"Loaded {len(paths)} slides from PowerPoint.")
        except Exception as exc:
            clear_folder(folder)
            st.error(f"PowerPoint conversion failed: {exc}")
            st.info("On non-Windows hosts, upload PNG/JPG slide images instead.")

    if st.button("Load Images", use_container_width=True, disabled=not image_files):
        folder, cleanup = prepare_slide_folder()
        paths = save_uploaded_images(image_files, folder)
        set_slides(paths, folder, cleanup)
        st.success(f"Loaded {len(paths)} slide images.")

    st.divider()
    st.header("Controls")
    brush_color = st.color_picker("Brush color", "#FF0000")
    brush_thickness = st.slider("Brush thickness", 2, 20, 10)

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("Previous", use_container_width=True):
            if st.session_state.current_slide > 0:
                st.session_state.current_slide -= 1
                reset_annotations()
    with col_next:
        if st.button("Next", use_container_width=True):
            if st.session_state.current_slide < len(st.session_state.slide_paths) - 1:
                st.session_state.current_slide += 1
                reset_annotations()

    if st.button("Clear drawings", use_container_width=True):
        reset_annotations()

    st.divider()
    st.markdown(
        """
        **Gestures**
        - Point up above the green line + index finger: previous slide
        - Point up above the green line + pinky: next slide
        - Index finger only: draw on slide
        - Index + middle: pointer dot
        - Index + middle + ring above line: undo drawing
        """
    )

left_col, right_col = st.columns([1.4, 1])


@st.fragment(run_every=0.2)
def live_slide_panel(brush_color: str, brush_thickness: int):
    st.subheader("Live Slide")

    if not st.session_state.slide_paths:
        st.info("Upload a PowerPoint file or slide images to begin.")
        slide_canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(
            slide_canvas,
            "Waiting for slides...",
            (420, 360),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (180, 180, 180),
            2,
        )
        st.image(cv2.cvtColor(slide_canvas, cv2.COLOR_BGR2RGB), use_container_width=True)
        return

    total = len(st.session_state.slide_paths)
    current = st.session_state.current_slide + 1
    st.progress(current / total, text=f"Slide {current} of {total}")

    slide_canvas = render_slide(
        st.session_state.slide_paths[st.session_state.current_slide],
        1280,
        720,
    )

    processor = get_gesture_processor()
    gesture = processor.state.gesture
    pointer = processor.state.pointer
    brush_bgr = hex_to_bgr(brush_color)

    if gesture in {"prev", "next", "undo"}:
        apply_navigation_gesture(gesture)
    elif processor.state.drawing and pointer is not None:
        append_draw_point(pointer)
    elif gesture == "pointer" and pointer is not None:
        cv2.circle(slide_canvas, pointer, brush_thickness, brush_bgr, cv2.FILLED)

    draw_annotations(slide_canvas, brush_bgr, brush_thickness)
    st.image(cv2.cvtColor(slide_canvas, cv2.COLOR_BGR2RGB), use_container_width=True)

    if processor.state.hand_detected:
        st.success(f"Hand detected - gesture: `{gesture}`")
    else:
        st.warning("No hand detected. Enable the webcam on the right.")


with left_col:
    live_slide_panel(brush_color, brush_thickness)

with right_col:
    st.subheader("Webcam")
    webrtc_streamer(
        key="hand-gesture-webcam",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
        video_processor_factory=GestureVideoProcessor,
    )

    if st.session_state.slide_paths:
        st.markdown("**Quick jump**")
        thumb_cols = st.columns(3)
        for index, path in enumerate(st.session_state.slide_paths[:6]):
            with thumb_cols[index % 3]:
                if st.button(f"Slide {index + 1}", key=f"thumb_{index}", use_container_width=True):
                    st.session_state.current_slide = index
                    reset_annotations()
                st.image(Image.open(path), use_container_width=True)
