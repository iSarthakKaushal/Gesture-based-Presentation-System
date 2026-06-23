# Gesture-based Presentation System

Control slides with your hands — no clicker, no keyboard. Upload a presentation, turn on your webcam, and navigate, draw, and annotate using hand gestures.

[![Live Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://gesture-based-presentation-system.streamlit.app)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/iSarthakKaushal/Gesture-based-Presentation-System)

---

## Live Demo

**Try it in your browser (no install):**

**[Open Live Dashboard](https://gesture-based-presentation-system.streamlit.app)**

> If the link is not active yet, deploy in 2 minutes — see [Deploy Live](#deploy-live-streamlit-cloud).

---

## What This Project Does

| Mode | File | Best For |
|------|------|----------|
| **Web Dashboard** | `dashboard.py` | Browser demo, sharing with others, any OS |
| **Desktop App** | `gesture_presentation.py` | Fullscreen presentations, Windows + PowerPoint |

Both modes use **MediaPipe hand tracking** (via `cvzone`) to detect your hand in real time and map finger positions to slide actions.

---

## Gesture Commands

Position your hand so the **wrist/center is below the green line** on the webcam feed. For slide navigation, move your hand **above the green line**.

| Hand Position | Fingers Up | Action |
|---------------|------------|--------|
| Above green line | Index only `[1,0,0,0,0]` | **Previous slide** |
| Above green line | Pinky only `[0,0,0,0,1]` | **Next slide** |
| Below green line | Index only `[0,1,0,0,0]` | **Draw** on slide |
| Below green line | Index + Middle `[0,1,1,0,0]` | **Pointer** dot |
| Above green line | Index + Middle + Ring `[0,1,1,1,0]` | **Undo** last drawing |

### Visual Guide

```
        ABOVE GREEN LINE
        Index only  = Previous slide
        Pinky only  = Next slide
        Index+Middle+Ring = Undo
======== GREEN THRESHOLD LINE =================
        BELOW GREEN LINE
        Index only  = Draw on slide
        Index+Middle = Pointer dot
```

### Tips for Best Results

- Use **good lighting** — face a light source
- Keep **one hand** in frame
- Hold navigation gestures for ~1 second (built-in delay prevents double-triggers)
- Sit **arm's length** from the webcam
- Desktop app: press **`Q`** to quit

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/iSarthakKaushal/Gesture-based-Presentation-System.git
cd Gesture-based-Presentation-System
```

### 2. Set up Python environment

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

**Windows only** (for `.pptx` conversion):

```bash
pip install pywin32 --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### 3. Run the web dashboard

```bash
streamlit run dashboard.py
```

Open **http://localhost:8501** → upload slide images → enable webcam.

### 4. Run the desktop app (Windows)

```bash
python gesture_presentation.py
```

1. Select a `.pptx` file **or** click **Cancel** to use slides in `Presentation/`
2. Presentation opens fullscreen with webcam inset

---

## How to Use (Step by Step)

### Web Dashboard

1. **Upload slides** — PNG/JPG images (any OS) or `.pptx` (Windows only)
2. Click **Load Images** or **Load PowerPoint**
3. Click **START** on the webcam panel (allow camera permission)
4. Use gestures from the table above
5. Sidebar: **Previous / Next / Clear drawings** as backup controls

### Desktop App

1. Run `python gesture_presentation.py`
2. Pick your PowerPoint file (or Cancel to use `Presentation/` folder)
3. Fullscreen opens with webcam in top-left corner
4. Use gestures; press **`Q`** to quit

### Without PowerPoint

1. Export slides as PNG: **File → Export → PNG**
2. Put images in `Presentation/` folder
3. Run app and click **Cancel** on file picker

---

## Project Architecture

```
Gesture-based-Presentation-System/
├── gesture_presentation.py   # Desktop app (OpenCV fullscreen)
├── dashboard.py              # Streamlit web dashboard
├── gesture_engine.py         # Hand gesture detection
├── slide_utils.py            # PPT to PNG conversion
├── docs/
│   ├── ARCHITECTURE.md       # Deep dive: how it works
│   └── DEPLOY.md             # Deploy live on Streamlit Cloud
└── requirements.txt
```

### Data Flow

```
Webcam → gesture_engine (HandDetector) → Gesture (prev/next/draw/undo)
                                              ↓
                                    Slide canvas + annotations
                                              ↑
                              slide_utils (.pptx → PNG images)
```

### Key Technologies

| Library | Purpose |
|---------|---------|
| OpenCV | Webcam, rendering, drawing |
| cvzone + MediaPipe | Hand landmark detection |
| Streamlit + WebRTC | Web dashboard + browser webcam |
| pywin32 | PowerPoint automation (Windows) |

---

## Deep Dive

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — gesture algorithm, state machine, file breakdown
- **[docs/DEPLOY.md](docs/DEPLOY.md)** — deploy live on Streamlit Cloud

---

## Deploy Live (Streamlit Cloud)

**One-click deploy:**

[![Deploy on Streamlit](https://img.shields.io/badge/Deploy_on-Streamlit-FF4B4B?logo=streamlit)](https://share.streamlit.io/deploy?repository=https://github.com/iSarthakKaushal/Gesture-based-Presentation-System&branch=main&mainModule=dashboard.py)

Or see [docs/DEPLOY.md](docs/DEPLOY.md).

> On Streamlit Cloud, upload **PNG/JPG slides** — `.pptx` needs Windows + PowerPoint.

---

## Requirements

| Requirement | Desktop | Web |
|-------------|---------|-----|
| Python 3.10+ | Yes | Yes |
| Webcam | Yes | Yes |
| Windows + PowerPoint | For `.pptx` | Not needed |
| Browser | — | Chrome/Edge recommended |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Camera not detected | Allow camera in browser/OS settings |
| Gestures not triggering | Ensure hand is visible; check green line |
| PPT conversion fails | Save locally; use PNG export instead |
| Black webcam (desktop) | Try `VideoCapture(1)` for external camera |

---

## Author

**Sarthak Kaushal** — [GitHub @iSarthakKaushal](https://github.com/iSarthakKaushal)
