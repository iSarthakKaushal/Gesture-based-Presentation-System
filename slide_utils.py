import os
import shutil
import tempfile
from pathlib import Path


def normalize_path(path: str) -> str:
    return os.path.normpath(os.path.abspath(path))


def convert_ppt_to_images(ppt_path: str, output_folder: str) -> None:
    """Convert PowerPoint to PNG slides using Microsoft PowerPoint on Windows."""
    ppt_path = normalize_path(ppt_path)
    output_folder = normalize_path(output_folder)

    if not os.path.isfile(ppt_path):
        raise FileNotFoundError(f"PowerPoint file not found:\n  {ppt_path}")

    os.makedirs(output_folder, exist_ok=True)

    temp_dir = tempfile.mkdtemp(prefix="hand_ppt_")
    ext = Path(ppt_path).suffix.lower() or ".pptx"
    temp_ppt = os.path.join(temp_dir, f"slides{ext}")

    try:
        shutil.copy2(ppt_path, temp_ppt)
        if not os.path.isfile(temp_ppt):
            raise FileNotFoundError(f"Could not copy file to temp path:\n  {temp_ppt}")

        last_error = None
        for exporter in (_export_with_win32com, _export_with_comtypes):
            try:
                exporter(temp_ppt, output_folder)
                if load_slide_paths(output_folder):
                    return
            except Exception as exc:
                last_error = exc

        raise RuntimeError(
            f"PowerPoint could not export slides.\nLast error: {last_error}"
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _export_with_win32com(ppt_path: str, output_folder: str) -> None:
    import win32com.client

    powerpoint = None
    presentation = None
    try:
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.DisplayAlerts = 0
        presentation = powerpoint.Presentations.Open(
            ppt_path,
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
        presentation.SaveAs(output_folder, 17)
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        if powerpoint is not None:
            try:
                powerpoint.Quit()
            except Exception:
                pass


def _export_with_comtypes(ppt_path: str, output_folder: str) -> None:
    import comtypes.client

    ppt_app = None
    presentation = None
    try:
        ppt_app = comtypes.client.CreateObject("PowerPoint.Application")
        presentation = ppt_app.Presentations.Open(
            ppt_path,
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )
        presentation.SaveAs(output_folder, 17)
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        if ppt_app is not None:
            try:
                ppt_app.Quit()
            except Exception:
                pass


def load_slide_paths(folder: str) -> list[str]:
    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    paths = [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if Path(name).suffix.lower() in extensions
    ]
    return sorted(paths, key=lambda p: len(os.path.basename(p)))


def save_uploaded_images(uploaded_files, output_folder: str) -> list[str]:
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
    folder = tempfile.mkdtemp(prefix="hand_presentation_")
    return folder, True


def clear_folder(folder: str) -> None:
    if folder and os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)
