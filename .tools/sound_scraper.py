import os
import json

def find_sounds():
    sound_keys = set()
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == 'sounds.json':
                path = os.path.join(root, file)
                if 'lom' in path.split(os.sep):
                    try:
                        with open(path, 'r') as f:
                            data = json.load(f)
                            sound_keys.update(data.keys())
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON from {path}")
                    except Exception as e:
                        print(f"Error reading {path}: {e}")

    with open('sounds.txt', 'w') as f:
        for key in sorted(list(sound_keys)):
            f.write(f"{key}\n")

if __name__ == '__main__':
    find_sounds()