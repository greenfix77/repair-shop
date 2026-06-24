import base64
import json
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon

SETTINGS_PATH = "shop_settings.json"


def _load_settings():
    try:
        if Path(SETTINGS_PATH).exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}


def load_logo_path():
    settings = _load_settings()
    return settings.get("logo", "")


def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        ext = Path(image_path).suffix.lower()
        mime = "png"
        if ext in (".jpg", ".jpeg"):
            mime = "jpeg"
        elif ext == ".gif":
            mime = "gif"
        elif ext == ".bmp":
            mime = "bmp"
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:image/{mime};base64,{encoded}"
    except:
        return ""


def get_invoice_logo_html(settings=None):
    if settings is None:
        settings = _load_settings()
    logo_path = settings.get("logo", "")
    if not logo_path or not Path(logo_path).exists():
        return ""

    # Safety guard: skip files larger than 2 MB
    if Path(logo_path).stat().st_size > 2 * 1024 * 1024:
        return ""

    size = settings.get("invoice_logo_size", 96)

    # Load image, scale to invoice size, encode scaled version
    try:
        from PyQt5.QtCore import QBuffer, QIODevice

        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            return ""
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        scaled.save(buffer, "PNG")
        data = buffer.data()
        buffer.close()

        encoded = base64.b64encode(data).decode("utf-8")
        data_uri = f"data:image/png;base64,{encoded}"
        return f'<img src="{data_uri}" style="max-width: {size}px; max-height: {size}px;">'
    except:
        return ""


def get_header_logo_pixmap():
    settings = _load_settings()
    logo_path = settings.get("logo", "")
    if not logo_path or not Path(logo_path).exists():
        return None
    size = settings.get("header_logo_size", 32)
    pixmap = QPixmap(logo_path)
    if pixmap.isNull():
        return None
    return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def get_app_icon():
    settings = _load_settings()
    logo_path = settings.get("logo", "")
    use_as_icon = settings.get("use_logo_as_app_icon", False)
    if not use_as_icon or not logo_path or not Path(logo_path).exists():
        return None
    icon = QIcon(logo_path)
    if icon.isNull():
        return None
    return icon
