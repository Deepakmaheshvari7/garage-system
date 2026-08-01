"""One-time helper: render preset Hindi invoice text as PNG images via Chrome."""
import base64
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

APP_DIR = Path(__file__).resolve().parent.parent / "app"
ASSETS = APP_DIR / "assets" / "invoice"
FONTS = APP_DIR / "fonts"


def _b64_font(name: str) -> str:
    data = (FONTS / name).read_bytes()
    return base64.b64encode(data).decode()


BOLD_B64 = _b64_font("NotoSansDevanagari-Bold.ttf")
REG_B64 = _b64_font("NotoSansDevanagari-Regular.ttf")

FONT_CSS = f"""
@font-face {{
  font-family: 'Noto';
  src: url(data:font/truetype;base64,{BOLD_B64}) format('truetype');
  font-weight: bold;
}}
@font-face {{
  font-family: 'Noto';
  src: url(data:font/truetype;base64,{REG_B64}) format('truetype');
  font-weight: normal;
}}
"""

# (filename, text, css, window_w, window_h, align)
PRESETS = [
    ("shop_name.png", "श्री पार्वती मोटर्स",
     "font-weight:bold;font-size:26px;color:#c0392b;", 440, 44, "left"),
    ("tagline.png", "सभी गाड़ियों की सर्विस एवं ऑरिजिनल पार्ट्स उपलब्ध है।",
     "font-size:13px;color:#777;", 540, 30, "left"),
    ("address.png", "बस स्टैंड, अमलाहा",
     "font-size:12px;color:#777;", 260, 30, "left"),
    ("owner.png", "हेमेन्द्रसिंह मेवाड़ा",
     "font-size:12px;color:#777;", 280, 30, "left"),
    ("footer1.png", "✅ सभी पार्ट्स ऑरिजिनल हैं।",
     "font-size:12px;color:#777;", 280, 26, "left"),
    ("footer2.png", "कृपया बिल साथ रखें।",
     "font-size:12px;color:#777;", 220, 26, "left"),
]


def _find_chrome() -> str:
    for path in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ):
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Chrome or Edge not found.")


def _trim_whitespace(path: Path) -> None:
    """Crop PNG to content bounds so images align cleanly in the PDF."""
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if not bbox or bbox[2] - bbox[0] < 8 or bbox[3] - bbox[1] < 8:
        return
    im.crop(bbox).save(path)


def _render(browser: str, text: str, style: str, out: Path,
            w: int, h: int, align: str = "left") -> None:
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
{FONT_CSS}
body {{ margin:0; padding:2px 4px; background:white; }}
span {{ font-family:Noto,sans-serif; white-space:nowrap; {style} }}
</style></head><body><span>{text}</span></body></html>"""

    tmp = Path(tempfile.gettempdir()) / f"invoice_{out.stem}.html"
    tmp.write_text(html, encoding="utf-8")
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={w},{h}",
         f"--screenshot={out.resolve()}",
         tmp.resolve().as_uri()],
        check=True, capture_output=True,
    )
    tmp.unlink(missing_ok=True)
    _trim_whitespace(out)


def main():
    browser = _find_chrome()
    ASSETS.mkdir(parents=True, exist_ok=True)
    for filename, text, style, w, h, align in PRESETS:
        out = ASSETS / filename
        print(f"Rendering {filename} ...")
        _render(browser, text, style, out, w, h, align)
        print(f"  -> {out.stat().st_size} bytes")
    print("Done.")


if __name__ == "__main__":
    main()
