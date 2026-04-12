import os
import json
import re

# Paths
BASE_DIR = "/mnt/files/Workspaces/workspace/resourcepacks"
TEXTURES_DIR = os.path.join(BASE_DIR, "items/assets/lom/textures/item/palettes")
MODELS_DIR = os.path.join(BASE_DIR, "items/assets/lom/models/item/items/palettes")
RABBIT_FOOT_PATH = os.path.join(BASE_DIR, "lom/assets/minecraft/items/rabbit_foot.json")

START_ID = 6000

def format_entry(entry):
    # Format entry as a single line with spaces inside braces
    # Example: { "threshold": 1, "model": { "type": "model", "model": "lom:item/items/d20" } }
    model_str = json.dumps(entry["model"])
    # Put spaces inside the model's braces too if they are there
    model_str = model_str.replace('{"', '{ "').replace('"}', '" }')
    return f'{{ "threshold": {entry["threshold"]}, "model": {model_str} }}'

def main():
    # 1. Ensure models directory exists
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        print(f"Created directory: {MODELS_DIR}")

    # 2. List all PNG files in textures directory
    png_files = sorted([f for f in os.listdir(TEXTURES_DIR) if f.endswith(".png")])
    print(f"Found {len(png_files)} textures.")

    new_entries = []
    current_id = START_ID

    for png_file in png_files:
        name = os.path.splitext(png_file)[0]
        model_filename = f"{name}.json"
        model_path = os.path.join(MODELS_DIR, model_filename)

        # Create model JSON
        model_data = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"lom:item/palettes/{name}"
            }
        }

        with open(model_path, "w") as f:
            json.dump(model_data, f, indent="\t")
        
        # Prepare entry
        entry = {
            "threshold": current_id,
            "model": {
                "type": "model",
                "model": f"lom:item/items/palettes/{name}"
            }
        }
        new_entries.append(entry)
        current_id += 1

    print(f"Generated {len(png_files)} model files.")

    # 3. Update rabbit_foot.json
    if os.path.exists(RABBIT_FOOT_PATH):
        with open(RABBIT_FOOT_PATH, "r") as f:
            data = json.load(f)
        
        if "model" in data and "entries" in data["model"]:
            entries = data["model"]["entries"]
            
            # Remove existing palette entries
            entries = [e for e in entries if not (isinstance(e.get("model"), dict) and "items/palettes/" in str(e["model"].get("model", "")))]
            
            # Append new entries
            entries.extend(new_entries)
            entries.sort(key=lambda x: x["threshold"])
            
            # Custom formatting
            # 1. Start with the top level structure
            header = '{\n  "model": {\n    "type": "range_dispatch",\n    "property": "custom_model_data",\n'
            
            fallback = data["model"]["fallback"]
            fallback_str = json.dumps(fallback).replace('{"', '{ "').replace('"}', '" }')
            header += f'    "fallback": {fallback_str},\n'
            header += '    "entries": [\n'
            
            footer = '\n    ]\n  }\n}'
            
            formatted_entries = []
            for e in entries:
                formatted_entries.append("      " + format_entry(e))
            
            entries_content = ",\n".join(formatted_entries)
            
            final_json = header + entries_content + footer

            with open(RABBIT_FOOT_PATH, "w") as f:
                f.write(final_json)
            
            print(f"Updated {RABBIT_FOOT_PATH} with custom formatting.")
        else:
            print("Error: Could not find entries in rabbit_foot.json")
    else:
        print(f"Error: {RABBIT_FOOT_PATH} not found.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
