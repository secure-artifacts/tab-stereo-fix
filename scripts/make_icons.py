"""Build app.png / app-48.png / app.ico from desktop/assets/app-source.jpg."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "desktop" / "assets"
SOURCE = ASSETS / "app-source.jpg"
SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit("missing desktop/assets/app-source.jpg")
    image = Image.open(SOURCE).convert("RGBA")
    ASSETS.mkdir(parents=True, exist_ok=True)
    image.save(ASSETS / "app.png", format="PNG")
    image.resize((48, 48), Image.Resampling.LANCZOS).save(ASSETS / "app-48.png", format="PNG")
    image.save(ASSETS / "app.ico", format="ICO", sizes=SIZES)


if __name__ == "__main__":
    main()
