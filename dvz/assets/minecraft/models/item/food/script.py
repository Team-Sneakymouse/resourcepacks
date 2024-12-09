for i in range(1,494):
  print("summon item ~ ~ ~ {Item:{id:\"minecraft:apple\",Count:1b,tag:{display:{Name:'{\"text\":\"Dubious Ingredient\",\"color\":\"green\",\"italic\":false}'},CustomModelData:"+str(i)+"}}}")
exit()

import os
import json

# Get the list of all files in the current directory
files = os.listdir('.')

# Iterate through the files
for filename in files:
    # Check if the file is a .json file
    if filename.endswith('.json'):
        # Get the filename without the extension
        file_base = os.path.splitext(filename)[0]
        
        # Create the new content
        new_content = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"item/food/{file_base}"
            }
        }
        
        # Write the new content to the .json file
        with open(filename, 'w') as json_file:
            json.dump(new_content, json_file, indent=4)

print("All .json files have been updated.")


# Get the list of all files in the current directory
files = os.listdir('.')

# Filter out only .json files
json_files = [f for f in files if f.endswith('.json')]

# Start custom_model_data at 12
custom_model_data = 12

# Iterate through the JSON files
for file_base in json_files:
    # Get the filename without the extension
    file_base_name = os.path.splitext(file_base)[0]
    
    # Print the desired format to stdout
    print(f'{{ "predicate": {{ "custom_model_data": {custom_model_data} }}, "model": "item/food/{file_base_name}" }},')

    # Increment custom_model_data for the next file
    custom_model_data += 1
