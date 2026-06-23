import os
import shutil
import tempfile
from pathlib import Path


def convert_ppt_to_images(ppt_path: str, output_folder: str) -> None:
    """Convert a PowerPoint file to PNG slides (Windows + PowerPoint required)."""
    import comtypes.client

    ppt_app = comtypes.client.CreateObject("PowerPoint.Application")
    ppt_app.Visible = False

    presentation = ppt_app.Presentations.Open(ppt_path, WithWindow=False)
    presentation.SaveAs(output_folder, 17)  # 17 = PNG
    presentation.Close()
    ppt_app.Quit()


def load_slide_paths(folder: str) -> list[str]:
    """Return sorted image paths from a slide folder."""
    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    paths = [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if Path(name).suffix.lower() in extensions
    ]
    return sorted(paths, key=lambda p: len(os.path.basename(p)))


def save_uploaded_images(uploaded_files, output_folder: str) -> list[str]:
    """Save uploaded image files and return their paths."""
    os.makedirs(output_folder, exist_ok=True)
    paths = []

    for index, uploaded in enumerate(uploaded_files):
        ext = Path(uploaded.name).suffix.lower() or ".png"
        dest = os.path.join(output_folder, f"slide_{index + 1:03d}{ext}")
        with open(dest, "wb") as handle:
            handle.write(uploaded.getbuffer())
        paths.append(dest)

    return paths


def prepare_slide_folder() -> tuple[str, bool]:
    """Create a fresh temp folder for slides. Returns (path, should_cleanup)."""
    folder = tempfile.mkdtemp(prefix="hand_presentation_")
    return folder, True


def clear_folder(folder: str) -> None:
    if folder and os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)
