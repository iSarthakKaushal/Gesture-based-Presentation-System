import os
import threading
from dataclasses import dataclass

import cv2
import numpy as np
import streamlit as st
from av import VideoFrame
from PIL import Image
from streamlit_webrtc import (
    WebRtcMode,
    webrtc_streamer,
)

from gesture_engine import HandGestureProcessor
from slide_utils import (
    clear_folder,
    convert_ppt_to_images,
    load_slide_paths,
    prepare_slide_folder,
    save_uploaded_images,
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Gesture Presentation System",
    page_icon="🖐️",
    layout="wide",
)

# ============================================================
# THREAD SAFE SHARED STATE
# ============================================================

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

shared_state = st.session_state.shared_gesture_state
gesture_processor = st.session_state.gesture_processor

# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "slide_paths": [],
    "slide_folder": "",
    "cleanup_folder": False,
    "current_slide": 0,
    "annotations": [],
    "annotation_number": -1,
    "last_timestamp": 0.0,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# VIDEO PROCESSOR
# ============================================================

class GestureVideoProcessor:

    def recv(self, frame: VideoFrame):

        image = frame.to_ndarray(
            format="bgr24"
        )

        processed = gesture_processor.process(
            image
        )

        state = (
            gesture_processor
            .get_state_snapshot()
        )

        with shared_lock:
            shared_state.gesture = state["gesture"]
            shared_state.pointer = state["pointer"]
            shared_state.drawing = state["drawing"]
            shared_state.hand_detected = state["hand_detected"]
            shared_state.timestamp = state["timestamp"]
            shared_state.frame_width = state.get("frame_width", 640)
            shared_state.frame_height = state.get("frame_height", 480)

        return VideoFrame.from_ndarray(
            processed,
            format="bgr24",
        )

# ============================================================
# HELPERS
# ============================================================

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

    st.session_state.annotations[idx].append(
        point
    )


def set_slides(
    slide_paths,
    folder="",
    cleanup=False,
):

    old_folder = st.session_state.slide_folder

    if (
        st.session_state.cleanup_folder
        and old_folder
        and old_folder != folder
    ):
        clear_folder(old_folder)

    st.session_state.slide_paths = slide_paths
    st.session_state.slide_folder = folder
    st.session_state.cleanup_folder = cleanup
    st.session_state.current_slide = 0

    reset_annotations()


def hex_to_bgr(color_hex):

    color_hex = color_hex.lstrip("#")

    r = int(color_hex[0:2], 16)
    g = int(color_hex[2:4], 16)
    b = int(color_hex[4:6], 16)

    return (b, g, r)


def render_slide(
    image_path,
    width=1280,
    height=720,
):

    slide = cv2.imread(image_path)

    if slide is None:

        canvas = np.zeros(
            (height, width, 3),
            dtype=np.uint8,
        )

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

    scale = min(
        width / w,
        height / h,
    )

    new_w = int(w * scale)
    new_h = int(h * scale)

    slide = cv2.resize(
        slide,
        (new_w, new_h),
    )

    canvas = np.zeros(
        (height, width, 3),
        dtype=np.uint8,
    )

    x = (width - new_w) // 2
    y = (height - new_h) // 2

    canvas[
        y:y + new_h,
        x:x + new_w
    ] = slide

    return canvas


def draw_annotations(
    canvas,
    color,
    thickness,
):

    for annotation in st.session_state.annotations:

        if len(annotation) > 1:

            pts = np.array(
                annotation,
                np.int32,
            ).reshape((-1, 1, 2))

            cv2.polylines(
                canvas,
                [pts],
                False,
                color,
                thickness,
            )

        elif len(annotation) == 1:

            cv2.circle(
                canvas,
                annotation[0],
                thickness,
                color,
                cv2.FILLED,
            )


def scale_pointer(
    pointer: tuple[int, int],
    src_width: int,
    src_height: int,
    dst_width: int = 1280,
    dst_height: int = 720,
) -> tuple[int, int]:
    """Map webcam coordinates onto the slide canvas."""
    if src_width <= 0 or src_height <= 0:
        return pointer
    x = int(pointer[0] * dst_width / src_width)
    y = int(pointer[1] * dst_height / src_height)
    x = max(0, min(x, dst_width - 1))
    y = max(0, min(y, dst_height - 1))
    return x, y


def apply_gesture(gesture):

    total_slides = len(
        st.session_state.slide_paths
    )

    if gesture == "prev":

        if st.session_state.current_slide > 0:

            st.session_state.current_slide -= 1
            reset_annotations()

    elif gesture == "next":

        if (
            st.session_state.current_slide
            < total_slides - 1
        ):

            st.session_state.current_slide += 1
            reset_annotations()

    elif gesture == "undo":

        if st.session_state.annotations:

            st.session_state.annotations.pop()

            st.session_state.annotation_number -= 1


# ============================================================
# HEADER
# ============================================================

st.title(
    "🖐️ Gesture Based Presentation System"
)

st.caption(
    "Control presentations using hand gestures."
)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("Slides")

    ppt_file = st.file_uploader(
        "Upload PowerPoint",
        type=["pptx"]
    )

    image_files = st.file_uploader(
        "Upload Slide Images",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],
        accept_multiple_files=True,
    )

    # --------------------------------------
    # PowerPoint
    # --------------------------------------

    if st.button(
        "Load PowerPoint",
        use_container_width=True,
        disabled=ppt_file is None,
    ):

        folder, cleanup = (
            prepare_slide_folder()
        )

        ppt_path = os.path.join(
            folder,
            "presentation.pptx"
        )

        with open(
            ppt_path,
            "wb"
        ) as f:

            f.write(
                ppt_file.getbuffer()
            )

        try:

            convert_ppt_to_images(
                ppt_path,
                folder
            )

            slides = load_slide_paths(
                folder
            )

            set_slides(
                slides,
                folder,
                cleanup,
            )

            st.success(
                f"{len(slides)} slides loaded."
            )

        except Exception as exc:
            clear_folder(folder)
            st.error(str(exc))
            st.info("On cloud/Linux hosting, upload PNG/JPG images instead of .pptx.")

    if st.button(
        "Load Images",
        use_container_width=True,
        disabled=not image_files,
    ):

        folder, cleanup = (
            prepare_slide_folder()
        )

        slides = save_uploaded_images(
            image_files,
            folder
        )

        set_slides(
            slides,
            folder,
            cleanup,
        )

        st.success(
            f"{len(slides)} slides loaded."
        )

    st.divider()

    brush_color = st.color_picker(
        "Brush Color",
        "#FF0000"
    )

    brush_thickness = st.slider(
        "Brush Thickness",
        min_value=2,
        max_value=20,
        value=8,
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "◀ Previous",
            use_container_width=True,
        ):

            if (
                st.session_state.current_slide
                > 0
            ):

                st.session_state.current_slide -= 1
                reset_annotations()

    with col2:

        if st.button(
            "Next ▶",
            use_container_width=True,
        ):

            if (
                st.session_state.current_slide
                < len(
                    st.session_state.slide_paths
                ) - 1
            ):

                st.session_state.current_slide += 1
                reset_annotations()

    if st.button(
        "Clear Drawings",
        use_container_width=True,
    ):
        reset_annotations()

    st.divider()

    st.markdown(
        """
### Gestures (hand above green line = top zone)

| Fingers | Action |
|---------|--------|
| Thumb only | Previous slide |
| Pinky only | Next slide |
| Index only | Draw |
| Index + Middle | Pointer |
| Index + Middle + Ring | Undo |
"""
    )

    st.info("Click **START** on the webcam panel, then allow camera access.")

# ============================================================
# LAYOUT
# ============================================================

left_col, right_col = st.columns(
    [1.5, 1]
)

# ============================================================
# LIVE SLIDE PANEL
# IMPORTANT:
# This fragment refreshes every 200ms.
# This fixes the "No hand detected"
# issue because Streamlit reruns it.
# ============================================================

@st.fragment(run_every=0.2)
def live_slide_panel():

    with left_col:

        st.subheader(
            "Presentation"
        )

        # ----------------------------------
        # No Slides Loaded
        # ----------------------------------

        if not st.session_state.slide_paths:

            placeholder = np.zeros(
                (
                    720,
                    1280,
                    3,
                ),
                dtype=np.uint8,
            )

            cv2.putText(
                placeholder,
                "Upload slides to begin",
                (320, 360),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (255, 255, 255),
                2,
            )

            st.image(
                cv2.cvtColor(
                    placeholder,
                    cv2.COLOR_BGR2RGB,
                ),
                use_container_width=True,
            )

            return

        slide_count = len(
            st.session_state.slide_paths
        )

        slide_index = (
            st.session_state.current_slide
        )

        slide_canvas = render_slide(
            st.session_state.slide_paths[
                slide_index
            ]
        )

        brush_bgr = hex_to_bgr(
            brush_color
        )

        # ----------------------------------
        # READ SHARED STATE
        # ----------------------------------

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
            scaled_pointer = scale_pointer(
                pointer,
                frame_width,
                frame_height,
            )

        if timestamp != st.session_state.last_timestamp:
            st.session_state.last_timestamp = timestamp
            if gesture in ("prev", "next", "undo"):
                apply_gesture(gesture)

        if drawing and scaled_pointer is not None:
            add_annotation_point(scaled_pointer)

        if gesture == "pointer" and scaled_pointer is not None:
            cv2.circle(
                slide_canvas,
                scaled_pointer,
                brush_thickness,
                brush_bgr,
                cv2.FILLED,
            )

        draw_annotations(slide_canvas, brush_bgr, brush_thickness)

        st.progress(
            (slide_index + 1) / slide_count,
            text=f"Slide {slide_index + 1} of {slide_count}",
        )

        st.image(
            cv2.cvtColor(slide_canvas, cv2.COLOR_BGR2RGB),
            use_container_width=True,
        )

        if hand_detected:
            st.success(f"Gesture: **{gesture}**")
        else:
            st.warning("No hand detected — click START on the webcam and allow camera access.")


# ============================================================
# WEBCAM PANEL
# ============================================================

with right_col:

    st.subheader("Webcam")

    webrtc_streamer(
        key="gesture-webcam",
        mode=WebRtcMode.SENDRECV,
        async_processing=True,
        rtc_configuration={
            "iceServers": [
                {
                    "urls": [
                        "stun:stun.l.google.com:19302"
                    ]
                }
            ]
        },
        media_stream_constraints={
            "video": True,
            "audio": False,
        },
        video_processor_factory=GestureVideoProcessor,
    )

# ============================================================
# START LIVE PANEL
# ============================================================

live_slide_panel()

# ============================================================
# THUMBNAILS
# ============================================================

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
                if st.button(
                    f"Slide {index + 1}",
                    key=f"slide_{index}",
                    use_container_width=True,
                ):
                    st.session_state.current_slide = index
                    reset_annotations()

# ============================================================
# DEBUG PANEL
# REMOVE LATER IF YOU WANT
# ============================================================

with st.expander(
    "Debug Info",
    expanded=False,
):

    with shared_lock:

        st.write(
            {
                "gesture":
                    shared_state.gesture,

                "pointer":
                    shared_state.pointer,

                "drawing":
                    shared_state.drawing,

                "hand_detected":
                    shared_state.hand_detected,

                "timestamp":
                    shared_state.timestamp,
            }
        )

# ============================================================
# CLEANUP
# ============================================================

def cleanup():

    folder = st.session_state.get(
        "slide_folder",
        ""
    )

    cleanup_enabled = (
        st.session_state.get(
            "cleanup_folder",
            False,
        )
    )

    if (
        cleanup_enabled
        and folder
        and os.path.exists(folder)
    ):

        try:

            clear_folder(folder)

        except Exception:
            pass

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Gesture Based Presentation System"
)