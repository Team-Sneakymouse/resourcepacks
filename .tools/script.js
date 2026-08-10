const fs = require("fs")

const data = fs.readFileSync("data.txt", "utf8")
const rawSounds = data.split("\n")
const sounds = {}

for (let sound of rawSounds) {
	if (sound.trim() == "") continue
	let basename = sound.replace(/\d$/, "")
	if (!sounds[basename]) sounds[basename] = { sounds: [] }
	sounds[basename].sounds.push(`lom:prototypekit/${sound}`)
}

fs.writeFileSync("sounds1.json", JSON.stringify(sounds, null, 2))
for (let key in sounds) {
	console.log("lom:" + key)
}