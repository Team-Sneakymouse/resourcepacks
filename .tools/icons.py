import os
import json

images = "lom/assets/lom/textures/item/icons"
models = "lom/assets/lom/models/item/icons"
jigsaw = "lom/assets/minecraft/models/item/jigsaw.json"

jigsaw_data = json.load(open(jigsaw))
# format:
# {
# 	"parent": "minecraft:block/jigsaw",
# 	"overrides": [
# 		{ "predicate": { "custom_model_data": 1 }, "model": "lom:item/icons/bigjugs" },
# 		{ "predicate": { "custom_model_data": 2 }, "model": "lom:item/icons/aquaaffinity" },
#       { "predicate": { "custom_model_data": 1001 }, "model": "special:item/special1 },
#       { "predicate": { "custom_model_data": 1002 }, "model": "special:item/special2 },
#       ...
# 	]
# }
jigsaw_header = """{
	"parent": "minecraft:block/jigsaw",
	"overrides": [
"""
jigsaw_footer = """
	]
}
"""

# largest icon exluding special models
largest_model = max([override["predicate"]["custom_model_data"] for override in jigsaw_data["overrides"] if override["predicate"]["custom_model_data"] < 1000])


for icon in os.listdir(images):
	model_data = {
		"parent": "minecraft:item/generated",
		"textures": {
			"layer0": "lom:item/icons/" + icon[:-4]
		}
	}

	# Add override if it doesn't exist yet
	if not any([override["model"] == "lom:item/icons/" + icon[:-4] for override in jigsaw_data["overrides"]]):
		jigsaw_data["overrides"].append({
			"predicate": { "custom_model_data": largest_model + 1 },
			"model": "lom:item/icons/" + icon[:-4]
		})
		largest_model += 1
		
	with open(os.path.join(models, icon[:-4] + ".json"), "w") as f:
		f.write(json.dumps(model_data, indent="	")+ "\n")
	

with open(jigsaw, "w") as f:
	# Sort overrides by custom_model_data
	jigsaw_data["overrides"].sort(key=lambda override: override["predicate"]["custom_model_data"])

	# keep overrides in single line
	overrides = list(map(lambda override: "		"+json.dumps(override, separators=(", ", ": ")), jigsaw_data["overrides"]))
	data = jigsaw_header + ",\n".join(overrides).replace("{", "{ ").replace("}", " }") + jigsaw_footer

	# write to file
	f.write(data)
	