# /// script
# dependencies = [
#     "pillow",
# ]
# ///

"""
Crop 700x500 PNG/JPEG images down to position (15, 296) with size (668, 184).

Usage:
    uv run crop_images.py [DIRECTORY] [--in-place] [--output-dir DIR] [--dry-run]
"""

import argparse
import sys
from pathlib import Path
from PIL import Image

# Target input dimensions
TARGET_WIDTH = 700
TARGET_HEIGHT = 500

# Crop region specification: position (x, y) = (15, 296), size (w, h) = (668, 184)
CROP_X = 15
CROP_Y = 296
CROP_WIDTH = 668
CROP_HEIGHT = 184

CROP_BOX = (CROP_X, CROP_Y, CROP_X + CROP_WIDTH, CROP_Y + CROP_HEIGHT)  # (15, 296, 683, 480)


def process_images(directory: Path, output_dir: Path | None, in_place: bool, dry_run: bool):
    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    files = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in image_extensions]
    
    if not files:
        print(f"No image files found in '{directory}'.")
        return

    print(f"Scanning {len(files)} image file(s) in '{directory.resolve()}'...")
    if dry_run:
        print("[DRY RUN MODE - No files will be modified]")

    matching_count = 0
    processed_count = 0

    for file_path in sorted(files):
        # Ignore script itself or hidden files if any match extension
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                if w == TARGET_WIDTH and h == TARGET_HEIGHT:
                    matching_count += 1
                    dest_path = file_path if in_place else (output_dir / file_path.name if output_dir else file_path)

                    print(f"  [MATCH] {file_path.name}: {w}x{h} -> Crop box {CROP_BOX} (Size: {CROP_WIDTH}x{CROP_HEIGHT})")

                    if not dry_run:
                        # Copy image content before crop to avoid modifying during open
                        cropped_img = img.crop(CROP_BOX)
                        if output_dir and not in_place:
                            output_dir.mkdir(parents=True, exist_ok=True)
                        cropped_img.save(dest_path)
                        processed_count += 1
                else:
                    print(f"  [SKIP]  {file_path.name}: dimensions are {w}x{h} (does not match {TARGET_WIDTH}x{TARGET_HEIGHT})")
        except Exception as e:
            print(f"  [ERROR] Could not process {file_path.name}: {e}")

    print("\n" + "=" * 50)
    if dry_run:
        print(f"Dry run complete. Found {matching_count} matching image(s) out of {len(files)} total.")
    else:
        print(f"Done! Successfully cropped {processed_count} image(s) out of {matching_count} matching image(s).")


def main():
    parser = argparse.ArgumentParser(
        description=f"Crop images of size {TARGET_WIDTH}x{TARGET_HEIGHT} to position ({CROP_X}, {CROP_Y}) with size ({CROP_WIDTH}x{CROP_HEIGHT})."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory containing images to process (default: current directory)."
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite matching image files in place."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Output directory to save cropped images (if not --in-place)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check image sizes and report which files would be cropped without saving."
    )

    args = parser.parse_args()

    dir_path = Path(args.directory)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Error: Directory '{args.directory}' does not exist.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else None

    # If neither --in-place nor --output-dir is specified, default to overwriting in-place with prompt or clean execution
    if not args.in_place and not out_dir and not args.dry_run:
        # Default behavior: in-place overwrite
        in_place_flag = True
    else:
        in_place_flag = args.in_place

    process_images(dir_path, out_dir, in_place_flag, args.dry_run)


if __name__ == "__main__":
    main()
