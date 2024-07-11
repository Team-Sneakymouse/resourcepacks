import os
import subprocess
from PIL import Image
import json
import shutil
import math

# Get the first WebM file in the working directory
webm_file = next(file for file in os.listdir('.') if file.endswith('.webm'))
video_name = os.path.splitext(webm_file)[0].lower()

# Create the output directory if it doesn't exist
frames_dir = 'frames'
if os.path.exists(frames_dir):
    if os.path.isdir(frames_dir):
        shutil.rmtree(frames_dir)
os.makedirs(frames_dir, exist_ok=True)
output_dir = f'lom/assets/lom/textures/font/{video_name}'
os.makedirs(output_dir, exist_ok=True)

# Define ffprobe command to get video information
ffprobe_command = [
    'ffprobe',
    '-v', 'error',
    '-select_streams', 'v:0',
    '-show_entries', 'stream=avg_frame_rate',
    '-of', 'default=noprint_wrappers=1:nokey=1',
    webm_file
]

# Execute ffprobe command and capture output
ffprobe_output = subprocess.check_output(ffprobe_command).decode().strip()

# Parse the output to obtain the average frame rate
current_fps = eval(ffprobe_output)

# Calculate the target frame rate
if current_fps >= 20:
    target_fps = 20
else:
    target_fps = max(1, math.ceil(20 / (20 // current_fps)))

# Run the ffmpeg command to extract frames
command = [
    'ffmpeg',
    '-codec:v', 'libvpx',
    '-i', webm_file,
    '-vf', f'fps={target_fps}',
    f'{frames_dir}/%03d.png'
]

subprocess.run(command)

# Counter for resized frames
counter = 0

# List to store provider dictionaries
providers = []

# Iterate over images in the "frames" folder
for frame_file in os.listdir(frames_dir):
    if frame_file.endswith('.png'):
        # Check if the counter has reached the limit
        if counter >= 999:
            break
    
        frame_path = os.path.join(frames_dir, frame_file)
        
        # Open the image
        image = Image.open(frame_path)
        
        # Resize the image while maintaining aspect ratio
        image.thumbnail((256, 256), Image.LANCZOS)
        
        # Create a new blank image with transparency
        new_image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))  # Initialize with transparent black

        # Set the four outer corners to white with 1% alpha
        corner_pixels = [(0, 0), (255, 0), (0, 255), (255, 255)]
        for pixel in corner_pixels:
            new_image.putpixel(pixel, (255, 255, 255, 1))  # Set white pixel with 1% alpha
        
        # Calculate the position to paste the resized image
        # Change the integer at the end to do pixel by pixel moving
        x_offset = ((256 - image.width) // 2) - 0
        y_offset = ((256 - image.height) // 2) - 0
        
        # Paste the resized image onto the new blank image
        new_image.paste(image, (x_offset, y_offset))
        
        # Save the resized image to the output directory while preserving transparency
        output_file = os.path.join(output_dir, f'{counter:03}.png')
        new_image.save(output_file)
        
        # Generate provider dictionary
        provider = {
            "type": "bitmap",
            "file": f"lom:font/{video_name}/{counter:03}.png",
            "ascent": 136,
            "height": 256,
            "chars": [f"\\uE{counter:03}"]
        }
        providers.append(provider)
        
        # Increment the counter
        counter += 1

# Generate JSON object
json_data = {
    "providers": providers
}

# Determine the JSON file path
json_file_path = os.path.join("lom", "assets", "lom", "font", f"{video_name}.json")

# Create the directory if it doesn't exist
os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

# Convert JSON object to string
json_string = json.dumps(json_data, indent=4)

# Replace double backslashes with single backslashes
json_string = json_string.replace('\\\\', '\\')

# Write JSON string to file
with open(json_file_path, 'w') as json_file:
    json_file.write(json_string)

print(f"Image resizing and saving completed. Total resized frames: {counter}")
print(f"JSON file '{json_file_path}' generated successfully.")