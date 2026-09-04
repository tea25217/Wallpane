from pathlib import Path

from PIL import Image, ImageDraw


def draw_icon(size: int = 256) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    mint = (106, 168, 79, 255)
    dark = (45, 74, 34, 255)
    screen = (245, 248, 240, 255)

    def monitor(box: tuple[int, int, int, int], stand: tuple[int, int, int, int]) -> None:
        draw.rounded_rectangle(box, radius=max(4, size // 24), fill=dark, outline=mint, width=max(2, size // 48))
        inner = (box[0] + size // 22, box[1] + size // 22, box[2] - size // 22, box[3] - size // 18)
        draw.rectangle(inner, fill=screen)
        draw.rectangle(stand, fill=dark)

    monitor(
        (int(size * 0.08), int(size * 0.18), int(size * 0.62), int(size * 0.68)),
        (int(size * 0.30), int(size * 0.68), int(size * 0.40), int(size * 0.80)),
    )
    monitor(
        (int(size * 0.40), int(size * 0.28), int(size * 0.92), int(size * 0.78)),
        (int(size * 0.62), int(size * 0.78), int(size * 0.72), int(size * 0.90)),
    )
    return image


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    dest_dir = root / "src" / "wallpane" / "resources"
    dest_dir.mkdir(parents=True, exist_ok=True)
    icon = draw_icon(256)
    icon.save(dest_dir / "wallpane.png")
    packaging = root / "packaging"
    packaging.mkdir(exist_ok=True)
    icon.save(packaging / "wallpane.png")


if __name__ == "__main__":
    main()
