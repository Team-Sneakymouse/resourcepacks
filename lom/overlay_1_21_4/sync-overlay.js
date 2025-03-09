const fs = require('fs')
const path = require('path')

const modelPath = "../assets/minecraft/models/item"
const itemPath = "assets/minecraft/items"

const blacklist = ["bow"]

const models = fs.readdirSync(modelPath)
for (const model of models) {
	// check if it's a directory
	if (!fs.lstatSync(path.join(modelPath, model)).isFile()) {
		continue
	}
	const name = path.basename(model, '.json')
	if (blacklist.includes(name)) continue
	
	const contents = JSON.parse(fs.readFileSync(path.join(modelPath, model)))
	
	const result = {
		"model": {
			"type": "range_dispatch",
			"property": "custom_model_data",
			"fallback": { "type": "model", "model": `minecraft:item/${name}` },
			"entries": contents.overrides.map(override => ({
				"threshold": override.predicate.custom_model_data,
				"model": { "type": "model", "model": override.model }
			}))
		}
	}

	fs.writeFileSync(path.join(itemPath, `${name}.json`), JSON.stringify(result, null, 2))
}