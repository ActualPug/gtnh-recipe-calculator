import json
import os
from collections import defaultdict
from math import ceil

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "recipes.json")

def load_recipes():
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

def save_recipes(recipes):
    with open(file_path, "w") as f:
        json.dump(recipes, f, indent=2)

def split_recipe_types(recipes):
    multiblocks = {}
    singleblocks = {}
    for k, v in recipes.items():
        if isinstance(v, dict) and v.get("_type") == "multiblock":
            multiblocks[k] = v
        elif isinstance(v, dict):
            singleblocks[k] = v
    return multiblocks, singleblocks

def format_raw_materials(materials):
    lines = ["Total Raw Materials:"]
    for mat, qty in sorted(materials.items()):
        lines.append(f"- {qty}x {mat}")
    return "\n".join(lines)


def format_raw_materials_with_inventory(materials, inventory):
    lines = ["Total Raw Materials (Adjusted for Inventory):"]
    for mat, required in sorted(materials.items()):
        owned = inventory.get(mat, 0)
        remaining = max(0, required - owned)
        status = f"(have {owned}, need {remaining})" if owned else f"(need {remaining})"
        checkmark = " ✔" if remaining == 0 else ""
        lines.append(f"- {mat}: {required} {status}{checkmark}")
    return "\n".join(lines)


def format_recipe_view(name, recipe):
    lines = [f"Recipe for '{name}':"]
    if "_inputs" in recipe:
        for k, v in recipe["_inputs"].items():
            lines.append(f"- {k}: {v}")
    else:
        for k, v in recipe.items():
            if not k.startswith("_"):
                lines.append(f"- {k}: {v}")
    if "_output_count" in recipe:
        lines.append(f"Output Count: {recipe['_output_count']}")
    if "_tags" in recipe:
        lines.append(f"Tags: {', '.join(recipe['_tags'])}")
    return "\n".join(lines)

def calculate_raw_materials(name, quantity, recipes, inventory=None):
    from math import ceil
    if inventory is None:
        inventory = {}

    raw_needed = {}

    def recurse(item, qty_needed):
        entry = recipes.get(item)
        if isinstance(entry, list):
            entry = entry[0]

        # Spend from inventory if available
        have = inventory.get(item, 0)
        remaining = max(0, qty_needed - have)
        inventory[item] = max(0, have - qty_needed)

        # No recipe means it's a raw material
        if not entry or not isinstance(entry, dict) or all(k.startswith("_") for k in entry.keys()):
            raw_needed[item] = raw_needed.get(item, 0) + qty_needed
            return

        output_count = entry.get("_output_count", 1)
        crafts_needed = ceil(remaining / output_count)
        inputs = entry.get("_inputs", entry)

        for sub, count in inputs.items():
            if not sub.startswith("_"):
                recurse(sub, count * crafts_needed)

    recurse(name, quantity)
    return raw_needed