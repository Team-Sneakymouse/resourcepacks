#!/usr/bin/env python3
"""Idempotently migrate this resource-pack repository to Minecraft 26.2.

Run with no mode flag to apply changes.  ``--check`` is read-only and exits
non-zero when the repository does not match the migration specification.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - dependency error is user-facing
    raise SystemExit("Pillow is required (for example: uv run --with pillow python ...)") from exc


PACKS = (
    "city", "dev", "dvz", "entities", "hats", "items", "leveling", "lom",
    "memes", "music", "paladins", "quests", "seasonal_halloween",
    "seasonal_xmas", "spells", "systems", "tutorial",
)
METADATA_PACKS = tuple(p for p in PACKS if p != "seasonal_halloween")
ITEM_DEFINITION_DIRS = (
    ("lom/assets/minecraft/items", 47),
    ("quests/assets/lom/items", 48),
    ("systems/assets/lom/items", 3),
)
RENAMES = {
    "chain": "iron_chain",
    "quartz_pillar": "quartz_pillar_side",
    "purpur_pillar": "purpur_pillar_side",
}
OVERLAYS = {
    "city": (
        "dark_oak_door_bottom", "glass", "gold_block", "nether_portal",
    ),
    "dvz": (
        "gold_block", "honey_block_top", "lime_wool", "orange_wool",
        "redstone_block", "sculk_sensor_tendril_active", "yellow_wool",
    ),
}
ENTITY_MOVES = {
    "city": {
        "blaze.png": "blaze/blaze.png",
        "endermite.png": "endermite/endermite.png",
        "silverfish.png": "silverfish/silverfish.png",
        "fox/snow_fox.png": "fox/fox_snow.png",
        "fox/snow_fox_sleep.png": "fox/fox_snow_sleep.png",
        "panda/aggressive_panda.png": "panda/panda_aggressive.png",
        "panda/lazy_panda.png": "panda/panda_lazy.png",
        "panda/playful_panda.png": "panda/panda_playful.png",
        "panda/weak_panda.png": "panda/panda_weak.png",
        "panda/worried_panda.png": "panda/panda_worried.png",
        "pig/pig.png": "pig/pig_temperate.png",
        "rabbit/brown.png": "rabbit/rabbit_brown.png",
        "turtle/big_sea_turtle.png": "turtle/turtle.png",
    },
    "dvz": {
        "beacon_beam.png": "beacon/beacon_beam.png",
        "blaze.png": "blaze/blaze.png",
        "endermite.png": "endermite/endermite.png",
        "phantom.png": "phantom/phantom.png",
        "silverfish.png": "silverfish/silverfish.png",
        "panda/aggressive_panda.png": "panda/panda_aggressive.png",
        "panda/brown_panda.png": "panda/panda_brown.png",
        "panda/lazy_panda.png": "panda/panda_lazy.png",
        "panda/playful_panda.png": "panda/panda_playful.png",
        "panda/weak_panda.png": "panda/panda_weak.png",
        "panda/worried_panda.png": "panda/panda_worried.png",
    },
    "items": {"fishing_hook.png": "fishing/fishing_hook.png"},
}
MOON_NAMES = (
    "full_moon", "waning_gibbous", "third_quarter", "waning_crescent",
    "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous",
)


class Migration:
    def __init__(self, root: Path, assets: Path, check: bool):
        self.root = root.resolve()
        self.assets = assets.resolve()
        self.check = check
        self.problems: list[str] = []
        self.changes: list[str] = []

    def problem(self, message: str) -> None:
        self.problems.append(message)

    def write_json(self, path: Path, value: Any) -> None:
        wanted = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == wanted:
            return
        if self.check:
            self.problem(f"stale JSON: {path.relative_to(self.root)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(wanted, encoding="utf-8")
            self.changes.append(str(path.relative_to(self.root)))

    def write_text(self, path: Path, wanted: str) -> None:
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == wanted:
            return
        if self.check:
            self.problem(f"stale JSON: {path.relative_to(self.root)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(wanted, encoding="utf-8")
            self.changes.append(str(path.relative_to(self.root)))

    def copy_exact(self, source: Path, target: Path, required: bool = True) -> None:
        if not source.is_file():
            if required:
                self.problem(f"required source missing: {source}")
            return
        if target.is_file() and target.read_bytes() == source.read_bytes():
            return
        if self.check:
            self.problem(f"missing/stale copy: {target.relative_to(self.root)}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            self.changes.append(str(target.relative_to(self.root)))

    def remove(self, path: Path) -> None:
        if not path.exists():
            return
        if self.check:
            self.problem(f"obsolete path remains: {path.relative_to(self.root)}")
        else:
            path.unlink()
            self.changes.append(str(path.relative_to(self.root)))

    def metadata(self) -> None:
        for pack in METADATA_PACKS:
            path = self.root / pack / "pack.mcmeta"
            if not path.is_file():
                self.problem(f"missing metadata: {pack}/pack.mcmeta")
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            pack_data = data.setdefault("pack", {})
            for old in ("pack_format", "supported_formats", "supporetd_formats"):
                pack_data.pop(old, None)
            pack_data["min_format"] = [88, 0]
            pack_data["max_format"] = 2147483647
            self.write_json(path, data)
        halloween = self.root / "seasonal_halloween/pack.mcmeta"
        if halloween.exists():
            self.problem("seasonal_halloween/pack.mcmeta must remain absent")

    def item_definitions(self) -> None:
        total = 0
        for relative, expected in ITEM_DEFINITION_DIRS:
            directory = self.root / relative
            files = sorted(directory.rglob("*.json"))
            if len(files) != expected:
                self.problem(f"{relative}: expected {expected} JSON files, found {len(files)}")
            for path in files:
                raw = path.read_text(encoding="utf-8")
                data = json.loads(raw)
                if data.get("oversized_in_gui") is not True:
                    closing = raw.rfind("}")
                    if closing < 0 or not isinstance(data, dict):
                        self.problem(f"item definition is not an object: {path.relative_to(self.root)}")
                        continue
                    prefix = raw[:closing].rstrip()
                    separator = "" if prefix.endswith("{") else ","
                    wanted = prefix + separator + '\n  "oversized_in_gui": true\n' + raw[closing:]
                    self.write_text(path, wanted)
            total += len(files)
        if total != 98:
            self.problem(f"expected 98 item definitions, found {total}")

    @staticmethod
    def rewrite_texture_value(value: str) -> tuple[str, str | None]:
        raw = value
        if raw.startswith("minecraft:block/"):
            name = raw[len("minecraft:block/"):]
        elif raw.startswith("block/"):
            name = raw[len("block/"):]
        else:
            return value, None
        name = RENAMES.get(name, name)
        return f"lom:item/block/{name}", name

    def rewrite_item_model(self, node: Any) -> tuple[Any, set[str]]:
        used: set[str] = set()
        if isinstance(node, dict):
            result = {}
            for key, value in node.items():
                if key == "textures" and isinstance(value, dict):
                    textures = {}
                    for texture_key, texture_value in value.items():
                        if isinstance(texture_value, str):
                            texture_value, name = self.rewrite_texture_value(texture_value)
                            if name:
                                used.add(name)
                        textures[texture_key] = texture_value
                    result[key] = textures
                else:
                    result[key], nested = self.rewrite_item_model(value)
                    used.update(nested)
            return result, used
        if isinstance(node, list):
            result = []
            for value in node:
                value, nested = self.rewrite_item_model(value)
                result.append(value)
                used.update(nested)
            return result, used
        return node, used

    @staticmethod
    def collect_lom_textures(node: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "textures" and isinstance(value, dict):
                    for texture in value.values():
                        if isinstance(texture, str) and texture.startswith("lom:item/block/"):
                            found.add(texture[len("lom:item/block/"):])
                found.update(Migration.collect_lom_textures(value))
        elif isinstance(node, list):
            for value in node:
                found.update(Migration.collect_lom_textures(value))
        return found

    def rewrite_item_model_text(self, raw: str) -> str:
        """Rewrite texture-object values while retaining the document's layout."""
        json.loads(raw)  # transformations are only performed on valid JSON
        starts = list(re.finditer(r'"textures"\s*:\s*\{', raw))
        for match in reversed(starts):
            opening = raw.find("{", match.start())
            depth, in_string, escaped, closing = 0, False, False, None
            for index in range(opening, len(raw)):
                char = raw[index]
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                elif char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        closing = index + 1
                        break
            if closing is None:
                raise ValueError("unterminated textures object")
            segment = raw[opening:closing]
            if not isinstance(json.loads(segment), dict):
                continue

            def replace_value(value_match: re.Match[str]) -> str:
                prefix, namespace, name = value_match.groups()
                name = RENAMES.get(name, name)
                return f'{prefix}"lom:item/block/{name}"'

            segment = re.sub(
                r'(:\s*)"(minecraft:)?block/([^"\\]+)"', replace_value, segment
            )
            raw = raw[:opening] + segment + raw[closing:]
        return raw

    def item_atlas(self) -> None:
        models: list[Path] = []
        for pack in PACKS:
            assets = self.root / pack / "assets"
            if assets.is_dir():
                models.extend(assets.glob("*/models/item/**/*.json"))
        used: set[str] = set()
        for path in sorted(models):
            raw = path.read_text(encoding="utf-8")
            rewritten = self.rewrite_item_model_text(raw)
            self.write_text(path, rewritten)
            used.update(self.collect_lom_textures(json.loads(rewritten)))

        vanilla = self.assets / "minecraft/textures/block"
        base = self.root / "lom/assets/lom/textures/item/block"
        for name in sorted(used):
            if name == "gray_stained_glass_pane":
                continue
            source = vanilla / f"{name}.png"
            target = base / f"{name}.png"
            self.copy_exact(source, target)
            self.copy_exact(Path(str(source) + ".mcmeta"), Path(str(target) + ".mcmeta"), required=False)

        for pack, names in OVERLAYS.items():
            source_root = self.root / pack / "assets/minecraft/textures/block"
            target_root = self.root / pack / "assets/lom/textures/item/block"
            for name in names:
                source = source_root / f"{name}.png"
                target = target_root / f"{name}.png"
                self.copy_exact(source, target)
                self.copy_exact(Path(str(source) + ".mcmeta"), Path(str(target) + ".mcmeta"), required=False)

        pane_source = self.root / "city/assets/minecraft/textures/block/gray_stained_glass_pane.png"
        pane_target = self.root / "city/assets/lom/textures/item/block/gray_stained_glass_pane.png"
        self.copy_exact(pane_source, pane_target)
        self.copy_exact(Path(str(pane_source) + ".mcmeta"), Path(str(pane_target) + ".mcmeta"), required=False)

    @staticmethod
    def contains_missing_face(node: Any) -> bool:
        if isinstance(node, dict):
            return any(
                (key == "texture" and value == "#missing")
                or Migration.contains_missing_face(value)
                for key, value in node.items()
            )
        if isinstance(node, list):
            return any(Migration.contains_missing_face(value) for value in node)
        return False

    @staticmethod
    def add_texture_binding(raw: str, key: str, resource: str) -> str:
        """Add one binding to the root textures object without reformatting."""
        data = json.loads(raw)
        textures = data.get("textures")
        if not isinstance(textures, dict):
            raise ValueError("model has no root textures object")
        if textures.get(key) == resource:
            return raw
        match = re.search(r'("textures"\s*:\s*\{)(\s*\n)([ \t]*)', raw)
        if not match:
            raise ValueError("textures object is not in a supported multiline layout")
        insertion = f'{match.group(1)}{match.group(2)}{match.group(3)}"{key}": "{resource}",{match.group(2)}{match.group(3)}'
        return raw[:match.start()] + insertion + raw[match.end():]

    def atlas_compatibility(self) -> None:
        missing_resource = "lom:item/missing"
        missing_texture = self.root / "lom/assets/lom/textures/item/missing.png"
        expected_pixels = tuple(
            (248, 0, 248, 255) if ((x // 8) + (y // 8)) % 2 == 0 else (0, 0, 0, 255)
            for y in range(16) for x in range(16)
        )
        valid_missing_texture = False
        if missing_texture.is_file():
            with Image.open(missing_texture) as image:
                rgba = image.convert("RGBA")
                expected_bytes = bytes(channel for pixel in expected_pixels for channel in pixel)
                valid_missing_texture = rgba.size == (16, 16) and rgba.tobytes() == expected_bytes
        if not valid_missing_texture:
            if self.check:
                self.problem("missing/stale checkerboard: lom/assets/lom/textures/item/missing.png")
            else:
                missing_texture.parent.mkdir(parents=True, exist_ok=True)
                image = Image.new("RGBA", (16, 16))
                image.putdata(expected_pixels)
                image.save(missing_texture)
                self.changes.append(str(missing_texture.relative_to(self.root)))

        # In 26.2 the built-in missing sprite belongs to the blocks atlas,
        # which makes an otherwise item-atlas model illegal.  Bind unresolved
        # faces to an exact item-atlas copy of the classic checkerboard so real
        # model mistakes remain visibly distinct from intentional transparency.
        for pack in PACKS:
            assets = self.root / pack / "assets"
            if not assets.is_dir():
                continue
            for path in sorted(assets.glob("*/models/item/**/*.json")):
                raw = path.read_text(encoding="utf-8")
                data = json.loads(raw)
                current = data.get("textures", {}).get("missing")
                if self.contains_missing_face(data) and current != missing_resource:
                    try:
                        if isinstance(current, str):
                            old_binding = f'"missing": {json.dumps(current)}'
                            raw = raw.replace(old_binding, f'"missing": {json.dumps(missing_resource)}', 1)
                        else:
                            raw = self.add_texture_binding(raw, "missing", missing_resource)
                        self.write_text(path, raw)
                    except ValueError as exc:
                        self.problem(f"cannot bind invisible texture in {path.relative_to(self.root)}: {exc}")

        # Two D20 variants use a seasonal texture in the custom vanilla
        # namespace.  Keep both seasonal overlays and move the sprite identity
        # onto the items atlas.
        for relative in (
            "items/assets/lom/models/item/items/d20/d20_green.json",
            "items/assets/lom/models/item/items/d20/d20_whitegreen.json",
        ):
            path = self.root / relative
            raw = path.read_text(encoding="utf-8")
            self.write_text(path, raw.replace('"vanilla:block/bamboo_block"', '"vanilla:item/block/bamboo_block"'))
        bamboo_base_source = self.root / "seasonal_xmas/assets/vanilla/textures/block/bamboo_block.png"
        bamboo_base_target = self.root / "lom/assets/vanilla/textures/item/block/bamboo_block.png"
        self.copy_exact(bamboo_base_source, bamboo_base_target)
        self.copy_exact(
            Path(str(bamboo_base_source) + ".mcmeta"),
            Path(str(bamboo_base_target) + ".mcmeta"),
            required=False,
        )
        halloween_bamboo_source = self.root / "seasonal_halloween/assets/vanilla/textures/block/bamboo_block.png"
        halloween_bamboo_target = self.root / "seasonal_halloween/assets/vanilla/textures/item/block/bamboo_block.png"
        self.copy_exact(halloween_bamboo_source, halloween_bamboo_target)
        self.copy_exact(
            Path(str(halloween_bamboo_source) + ".mcmeta"),
            Path(str(halloween_bamboo_target) + ".mcmeta"),
            required=False,
        )
        self.remove(self.root / "seasonal_xmas/assets/vanilla/textures/item/block/bamboo_block.png")
        self.remove(self.root / "seasonal_xmas/assets/vanilla/textures/item/block/bamboo_block.png.mcmeta")

        # Item models may not sample the entity atlas.  Preserve the banner
        # pixels under an item-atlas identity for the clipboard model.
        clipboard = self.root / "items/assets/lom/models/item/tools/clipboard_paladin.json"
        raw = clipboard.read_text(encoding="utf-8")
        self.write_text(clipboard, raw.replace('"lom:entity/banner/ankh"', '"lom:item/entity/banner/ankh"'))
        self.copy_exact(
            self.root / "lom/assets/lom/textures/entity/banner/ankh.png",
            self.root / "lom/assets/lom/textures/item/entity/banner/ankh.png",
        )

        # The Goattown crate's door front was the final direct custom-namespace
        # block-atlas texture in an item model.  It was initially masked by an
        # earlier UV bake failure in the same aggregate item definition.
        goattown = self.root / "systems/assets/lom/models/item/items/crates/crate_goattown.json"
        raw = goattown.read_text(encoding="utf-8")
        self.write_text(
            goattown,
            raw.replace('"lom:block/cherry_door_bottom"', '"lom:item/block/cherry_door_bottom"'),
        )
        self.copy_exact(
            self.assets / "minecraft/textures/block/cherry_door_bottom.png",
            self.root / "lom/assets/lom/textures/item/block/cherry_door_bottom.png",
        )

        # This label texture has never existed in the repository.  Retain the
        # crate geometry but make the absent label transparent.
        crate = self.root / "items/assets/lom/models/item/tools/crate_labelled.json"
        raw = crate.read_text(encoding="utf-8")
        data = json.loads(raw)
        if data.get("textures", {}).get("2") != "lom:item/items/invisible":
            raw = raw.replace('"2": "lom:item/tools/crate_labels/chesetest"', '"2": "lom:item/items/invisible"')
            self.write_text(crate, raw)

    def uv_bounds_compatibility(self) -> None:
        # Minecraft 26.2 computes face translucency in the standard 0..16 UV
        # domain and rejects out-of-bounds rectangles.  These are the exact
        # malformed faces isolated by the four-batch direct-model harness.
        fixes = {
            "entities/assets/lom/models/item/entities/vegastables/dice.json": {
                "[15.5, 21.5, 15, 22]": "[6.25, 6.25, 6, 6.5]",
            },
            "systems/assets/lom/models/item/items/crates/crate_goattown.json": {
                "[16.25, 7.125, 7.125, 10.625]": "[16, 7.125, 7.125, 10.625]",
                "[11, -1.375, 8.125, 16]": "[11, 0, 8.125, 16]",
            },
            "systems/assets/lom/models/item/items/crates/crate_grove.json": {
                "[15.25, 0, 0.125, 16.125]": "[15.25, 0, 0.125, 16]",
            },
            "systems/assets/lom/models/item/items/crates/crate_darkvale.json": {
                "[0, 0, 4.625, 16.875]": "[0, 0, 4.625, 16]",
                "[0, 0, 4.125, 16.875]": "[0, 0, 4.125, 16]",
                "[7.25, 0, 11.375, 16.75]": "[7.25, 0, 11.375, 16]",
                "[5.375, 7.375, 8.5, 16.875]": "[5.375, 7.375, 8.5, 16]",
                "[6, 0, 11.375, 16.5]": "[6, 0, 11.375, 16]",
                "[2, -0.875, 6.0625, 16]": "[2, 0, 6.0625, 16]",
                "[0, -0.25, 16, 15.75]": "[0, 0, 16, 15.75]",
            },
            "items/assets/lom/models/item/weapons/regrowth_morning_star.json": {
                "[40, 120, 48, 168]": "[0, 14, 1, 16]",
            },
        }
        for relative, replacements in fixes.items():
            path = self.root / relative
            raw = path.read_text(encoding="utf-8")
            wanted = raw
            for old, new in replacements.items():
                wanted = wanted.replace(old, new)
            self.write_text(path, wanted)

    def dual_use_block_models(self) -> None:
        model_root = self.root / "entities/assets/lom/models"
        texture_root = self.root / "entities/assets/lom/textures"

        candelabra_source = model_root / "item/blocks/candelabra.json"
        candelabra = candelabra_source.read_text(encoding="utf-8")
        candelabra = candelabra.replace("lom:item/block/", "minecraft:block/")
        self.write_text(model_root / "block/dual_use/candelabra.json", candelabra)

        custom_models = {
            "item/entities/trashcan.json": (
                "block/dual_use/trashcan.json",
                "item/entities/trashcan.png",
                "block/dual_use/trashcan.png",
                "lom:item/entities/trashcan",
                "lom:block/dual_use/trashcan",
            ),
            "item/entities/casino_lounges/magic_jukebox.json": (
                "block/dual_use/magic_jukebox.json",
                "item/entities/casino_lounges/10_magic_jukebox_texture.png",
                "block/dual_use/10_magic_jukebox_texture.png",
                "lom:item/entities/casino_lounges/10_magic_jukebox_texture",
                "lom:block/dual_use/10_magic_jukebox_texture",
            ),
        }
        for source_model, (target_model, source_texture, target_texture, old_resource, new_resource) in custom_models.items():
            raw = (model_root / source_model).read_text(encoding="utf-8")
            self.write_text(model_root / target_model, raw.replace(old_resource, new_resource))
            source = texture_root / source_texture
            target = texture_root / target_texture
            self.copy_exact(source, target)
            self.copy_exact(Path(str(source) + ".mcmeta"), Path(str(target) + ".mcmeta"), required=False)

        blockstate_models = {
            "city/assets/minecraft/blockstates/tuff_wall.json": (
                "lom:item/blocks/candelabra", "lom:block/dual_use/candelabra",
            ),
            "city/assets/minecraft/blockstates/tuff_brick_wall.json": (
                "lom:item/entities/trashcan", "lom:block/dual_use/trashcan",
            ),
            "city/assets/minecraft/blockstates/dead_tube_coral_fan.json": (
                "lom:item/entities/casino_lounges/magic_jukebox", "lom:block/dual_use/magic_jukebox",
            ),
            "city/assets/minecraft/blockstates/dead_tube_coral_wall_fan.json": (
                "lom:item/entities/casino_lounges/magic_jukebox", "lom:block/dual_use/magic_jukebox",
            ),
        }
        for relative, (old_model, new_model) in blockstate_models.items():
            path = self.root / relative
            self.write_text(path, path.read_text(encoding="utf-8").replace(old_model, new_model))

    def moons(self) -> None:
        for pack in ("seasonal_halloween", "seasonal_xmas"):
            environment = self.root / pack / "assets/minecraft/textures/environment"
            sheet = environment / "moon_phases.png"
            target = environment / "celestial/moon"
            if sheet.is_file():
                with Image.open(sheet) as image:
                    if image.size != (128, 64):
                        self.problem(f"unexpected moon sheet size in {pack}: {image.size}")
                        continue
                    for index, name in enumerate(MOON_NAMES):
                        x, y = (index % 4) * 32, (index // 4) * 32
                        crop = image.crop((x, y, x + 32, y + 32))
                        destination = target / f"{name}.png"
                        if self.check:
                            self.problem(f"obsolete moon sheet remains: {sheet.relative_to(self.root)}")
                        else:
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            crop.save(destination)
                            self.changes.append(str(destination.relative_to(self.root)))
                if not self.check:
                    sheet.unlink()
                    self.changes.append(str(sheet.relative_to(self.root)))
            for name in MOON_NAMES:
                destination = target / f"{name}.png"
                if not destination.is_file():
                    self.problem(f"missing moon sprite: {destination.relative_to(self.root)}")
                elif Image.open(destination).size != (32, 32):
                    self.problem(f"wrong moon sprite size: {destination.relative_to(self.root)}")

    def entities(self) -> None:
        for pack, moves in ENTITY_MOVES.items():
            root = self.root / pack / "assets/minecraft/textures/entity"
            for old_name, new_name in moves.items():
                old, new = root / old_name, root / new_name
                if old.is_file():
                    if self.check:
                        self.problem(f"obsolete entity texture: {old.relative_to(self.root)}")
                    else:
                        if new.exists() and new.read_bytes() != old.read_bytes():
                            self.problem(f"conflicting entity destination: {new.relative_to(self.root)}")
                            continue
                        new.parent.mkdir(parents=True, exist_ok=True)
                        if not new.exists():
                            shutil.copyfile(old, new)
                        old.unlink()
                        self.changes.extend((str(new.relative_to(self.root)), str(old.relative_to(self.root))))
                if not new.is_file():
                    self.problem(f"missing entity texture: {new.relative_to(self.root)}")

    def gui(self) -> None:
        root = self.root / "lom/assets/minecraft/textures/gui/sprites/container/inventory"
        self.remove(root / "effect_background_large.png")
        self.remove(root / "effect_background_small.png")
        for name in ("effect_background.png", "effect_background_ambient.png"):
            if (root / name).exists():
                self.problem(f"unwanted GUI override: {(root / name).relative_to(self.root)}")

    def validate_json(self) -> None:
        for pack in PACKS:
            for path in (self.root / pack).rglob("*.json"):
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    self.problem(f"invalid JSON {path.relative_to(self.root)}: {exc}")
            metadata = self.root / pack / "pack.mcmeta"
            if metadata.exists():
                try:
                    json.loads(metadata.read_text(encoding="utf-8"))
                except Exception as exc:
                    self.problem(f"invalid metadata {metadata.relative_to(self.root)}: {exc}")

    def run(self) -> int:
        if not (self.assets / "minecraft/textures/block").is_dir():
            self.problem(f"26.2 assets root is invalid: {self.assets}")
        else:
            self.metadata()
            self.item_definitions()
            self.item_atlas()
            self.atlas_compatibility()
            self.uv_bounds_compatibility()
            self.dual_use_block_models()
            self.moons()
            self.entities()
            self.gui()
            self.validate_json()
        for message in self.problems:
            print(f"ERROR: {message}", file=sys.stderr)
        if self.problems:
            print(f"Migration {'check' if self.check else 'apply'} failed with {len(self.problems)} issue(s).", file=sys.stderr)
            return 1
        action = "Check passed" if self.check else f"Migration complete ({len(self.changes)} changed paths)"
        print(action + ".")
        return 0


def default_assets_root() -> Path:
    return Path.home() / "AppData/Roaming/PrismLauncher/libraries/com/mojang/minecraft/26.2/minecraft-26.2-client/assets"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-root", type=Path, default=default_assets_root())
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--check", action="store_true", help="audit without writing")
    args = parser.parse_args()
    return Migration(args.repo_root, args.assets_root, args.check).run()


if __name__ == "__main__":
    raise SystemExit(main())
