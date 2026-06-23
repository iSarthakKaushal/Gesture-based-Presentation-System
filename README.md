# Hand Gesture Presentation

Control PowerPoint-style slides with hand gestures using your webcam. Includes a desktop app and a live web dashboard.

## Features

- Upload `.pptx` files or slide images
- Navigate slides with hand gestures (previous / next)
- Draw and annotate on slides in real time
- Live webcam dashboard built with Streamlit

## Gesture Controls

| Gesture | Action |
|---------|--------|
| Index finger up, hand above green line | Previous slide |
| Pinky up, hand above green line | Next slide |
| Index finger only | Draw on slide |
| Index + middle finger | Pointer dot |
| Index + middle + ring, above line | Undo last drawing |

## Local Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Use the **`venv`** environment only. An older duplicate `gesture-env` pointed at Python 3.13 and is broken on this machine — it has been removed.

### Desktop app (fullscreen OpenCV)

```bash
python gesture_presentation.py
```

### Live web dashboard

```bash
streamlit run dashboard.py
```

Open `http://localhost:8501` in your browser, upload slides, and enable the webcam.

> **Note:** PowerPoint conversion requires Windows with Microsoft PowerPoint installed. On other platforms, upload PNG/JPG slide images instead.

## Deploy Live Dashboard (Streamlit Cloud)

1. Push this repo to GitHub (see below).
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Click **New app** and connect your GitHub repo.
4. Set **Main file path** to `dashboard.py`.
5. Deploy.

Streamlit Cloud runs on Linux, so use **slide image uploads** there instead of `.pptx` conversion.

## Push to GitHub

```bash
git init
git add .
git commit -m "Add hand gesture presentation app and live dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/hand-presentation.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username and create the empty repo on GitHub first.

## Project Structure

```
gesture_presentation.py   # Desktop fullscreen app
dashboard.py              # Streamlit live dashboard
gesture_engine.py         # Hand gesture detection logic
slide_utils.py            # Slide loading and conversion helpers
requirements.txt
```

## Requirements

- Python 3.10+
- Webcam
- Windows + PowerPoint (only for `.pptx` conversion in desktop/local mode)
