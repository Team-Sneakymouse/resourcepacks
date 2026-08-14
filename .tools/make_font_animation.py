import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a video into a Minecraft bitmap-font animation.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--pack", default="memes")
    parser.add_argument("--name")
    parser.add_argument("--fps", type=float, default=20)
    parser.add_argument("--key-black", action="store_true")
    args = parser.parse_args()

    name = args.name or args.video.stem.lower()
    root = Path(__file__).resolve().parent.parent
    video = args.video if args.video.is_absolute() else root / args.video
    textures = root / args.pack / "assets/lom/textures/font" / name
    font_file = root / args.pack / "assets/lom/font" / f"{name}.json"
    frames = root / "frames" / name

    shutil.rmtree(frames, ignore_errors=True)
    shutil.rmtree(textures, ignore_errors=True)
    frames.mkdir(parents=True)
    textures.mkdir(parents=True)
    font_file.parent.mkdir(parents=True, exist_ok=True)

    rate = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0", str(video),
    ], text=True).strip()
    numerator, denominator = (int(part) for part in rate.split("/"))
    source_fps = numerator / denominator
    target_fps = min(args.fps, source_fps)

    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vf", f"fps={target_fps}", str(frames / "%03d.png"), "-y",
    ], check=True)

    providers = []
    for index, frame in enumerate(sorted(frames.glob("*.png"))[:999]):
        image = Image.open(frame).convert("RGBA")
        image.thumbnail((256, 256), Image.Resampling.LANCZOS)
        if args.key_black:
            pixels = []
            for red, green, blue, alpha in image.getdata():
                brightness = max(red, green, blue)
                new_alpha = alpha * max(0, min(1, (brightness - 6) / 24))
                pixels.append((red, green, blue, round(new_alpha)))
            image.putdata(pixels)
        canvas = Image.new("RGBA", (256, 256))
        canvas.putpixel((0, 0), (255, 255, 255, 1))
        canvas.putpixel((255, 0), (255, 255, 255, 1))
        canvas.putpixel((0, 255), (255, 255, 255, 1))
        canvas.putpixel((255, 255), (255, 255, 255, 1))
        canvas.alpha_composite(image, ((256 - image.width) // 2, (256 - image.height) // 2))
        canvas.save(textures / f"{index:03}.png", optimize=True)
        providers.append({
            "type": "bitmap",
            "file": f"lom:font/{name}/{index:03}.png",
            "ascent": 136,
            "height": 256,
            "chars": [chr(0xE000 + index)],
        })

    font_file.write_text(json.dumps({"providers": providers}, indent=4), encoding="utf-8")
    shutil.rmtree(frames)
    print(f"Generated {len(providers)} frames at {target_fps:g} FPS")
    print(font_file)


if __name__ == "__main__":
    main()
