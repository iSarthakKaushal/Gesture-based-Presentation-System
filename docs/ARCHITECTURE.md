# Architecture Deep Dive

How the Gesture-based Presentation System works under the hood.

---

## System Overview

```
gesture_presentation.py  ──┐
                           ├──▶  gesture_engine.py  ──▶  HandDetector (cvzone/MediaPipe)
dashboard.py             ──┘         │
                                     ▼
                              slide_utils.py  ──▶  Slide images (PNG)
```

---

## File-by-File Breakdown

### `gesture_presentation.py` — Desktop Application

| Section | What it does |
|---------|--------------|
| File picker | Tkinter dialog to select `.pptx` or cancel for `Presentation/` folder |
| PPT conversion | Calls `slide_utils.convert_ppt_to_images()` |
| Webcam loop | `cv2.VideoCapture(0)` at 1280×720 |
| Hand detection | `HandDetector` finds landmarks each frame |
| Gesture logic | Finger states mapped to slide actions |
| Rendering | Slide + annotations + webcam inset |
| Fullscreen | `cv2.WINDOW_FULLSCREEN` |

### `dashboard.py` — Web Dashboard

| Component | Technology |
|-----------|------------|
| UI | Streamlit columns + sidebar |
| Slide upload | `st.file_uploader` |
| Webcam | `streamlit-webrtc` + `GestureVideoProcessor` |
| Live refresh | `@st.fragment(run_every=0.2)` every 200ms |
| State | `st.session_state` |

### `gesture_engine.py` — Gesture Detection

**`GestureState`** — `gesture`, `hand_detected`, `pointer`, `drawing`

**`HandGestureProcessor`**:
- Green line at 42% of frame height
- 20-frame cooldown after navigation
- Drawing smoothing via `deque(maxlen=10)`

**Finger format:** `[thumb, index, middle, ring, pinky]` as 0/1

**Decision tree:**
```
cy <= threshold (ABOVE line):
  [1,0,0,0,0] → prev
  [0,0,0,0,1] → next
  [0,1,1,1,0] → undo

cy > threshold (BELOW line):
  [0,1,0,0,0] → draw
  [0,1,1,0,0] → pointer
```

### `slide_utils.py` — Slide Management

1. Copy `.pptx` to temp path
2. Open via `win32com` (fallback: `comtypes`)
3. `SaveAs(folder, 17)` — PNG export
4. Return sorted image paths

---

## Hand Tracking Pipeline

```
Camera Frame → flip (mirror) → findHands() → 21 landmarks
    → fingersUp() → gesture mapping → action
```

Landmark **8** = index fingertip. `hand["center"]` = above/below line check.

---

## Annotation System

```python
annotations = [
    [(x1,y1), (x2,y2)],   # stroke 1
    [(x3,y3), (x4,y4)],   # stroke 2
]
```

Undo = `annotations.pop()`. Slide change clears all strokes.

---

## Configuration

| Constant | Value | Purpose |
|----------|-------|---------|
| `gestureThreshold` | 300px | Desktop Y threshold |
| `GESTURE_THRESHOLD_RATIO` | 0.42 | Web Y threshold |
| `brushThickness` | 10 | Draw size |
| `delay` | 20 frames | Gesture cooldown |
| `detectionCon` | 0.8 | Hand confidence |
| `maxHands` | 1 | Single hand |

---

## Extending

- **New gesture:** Add finger pattern in `gesture_engine.py`, handle in both apps
- **New slide format:** Extend `load_slide_paths()` in `slide_utils.py`
- **Brush color:** Edit `brushColor` (desktop) or sidebar picker (web)
