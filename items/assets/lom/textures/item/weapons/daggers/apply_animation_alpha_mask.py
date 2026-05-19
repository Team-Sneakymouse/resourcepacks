# /// script
# dependencies = [
#   "pillow>=10.0.0",
# ]
# ///

import argparse
from pathlib import Path
from PIL import Image


def apply_alpha_mask(base_path: Path, animation_path: Path, output_path: Path) -> None:
    with Image.open(base_path) as base_image, Image.open(animation_path) as animation_image:
        base = base_image.convert("RGBA")
        animation = animation_image.convert("RGBA")

    if animation.height % animation.width != 0:
        raise ValueError(
            f"Animation height must be a whole number of square frames; got {animation.size}"
        )

    frame_count = animation.height // animation.width
    frame_size = base.width

    if base.height < frame_size:
        raise ValueError(
            f"Base texture must be at least {frame_size}px tall to provide a square alpha mask; got {base.size}"
        )

    # Scale the animation so each frame is as wide as the base texture.
    # NEAREST means no interpolation: pixels are hard-scaled.
    scaled_animation_size = (frame_size, frame_size * frame_count)
    if animation.size != scaled_animation_size:
        animation = animation.resize(scaled_animation_size, Image.Resampling.NEAREST)

    # Use the top-left square of the base texture matching the scaled animation frame size.
    base_alpha = base.crop((0, 0, frame_size, frame_size)).getchannel("A")
    base_alpha_pixels = base_alpha.tobytes()

    output = Image.new("RGBA", animation.size)

    for frame_index in range(frame_count):
        y = frame_index * frame_size
        frame = animation.crop((0, y, frame_size, y + frame_size))
        r, g, b, animation_alpha = frame.split()

        combined_alpha = Image.new("L", (frame_size, frame_size))
        combined_alpha.putdata([
            animation_a * base_a // 255
            for animation_a, base_a in zip(animation_alpha.tobytes(), base_alpha_pixels)
        ])

        output.paste(Image.merge("RGBA", (r, g, b, combined_alpha)), (0, y))

    output.save(output_path)


def default_output_path(base_path: Path) -> Path:
    return base_path.with_name(f"{base_path.stem}_mana{base_path.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the alpha channel from the top-left region of a base texture "
            "to every frame of a vertical animated texture, multiplying alpha values."
        )
    )
    parser.add_argument("base_texture", type=Path, help="Base texture, e.g. iron_dagger.png")
    parser.add_argument("animation_texture", type=Path, help="Vertical animation texture, e.g. mana_knife_blade.png")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file. Defaults to <base>_mana.png next to the base texture.",
    )

    args = parser.parse_args()
    output_path = args.output or default_output_path(args.base_texture)

    apply_alpha_mask(args.base_texture, args.animation_texture, output_path)
    print(f"Created {output_path}")


if __name__ == "__main__":
    main()
