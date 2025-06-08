"""
GTNH Recipe Calculator Logic
---------
This module handles core recipe logic for GTNH Recipe Editor.

Features:
- Reading and writing recipes
- Splitting and selecting recipes based on type or tech level
- Calculating required raw materials for crafting
- Formatting recipes and requirements for display

Author: ActualPug on github: https://github.com/ActualPug
"""

# === Imports ===

import json
import os
from math import ceil

# === Paths ===

# Absolute path to recipes.json (located in the same directory as this script)
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "recipes.json")

# === File I/O Utilities

# Load recipes from the JSON file if it exists, otherwise return an empty dictionary.
def load_recipes():
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

# Save the given recipes dictionary to the JSON file with indentation.
def save_recipes(recipes):
    with open(file_path, "w") as f:
        json.dump(recipes, f, indent=2)

# === Recipe Classification & Selection ===

# Split the recipe dictionary into two groups:
# - multiblocks: recipes explicitly marked with '_type': 'multiblock'
# - singleblocks: all other valid recipes
def split_recipe_types(recipes):
    multiblocks = {}
    singleblocks = {}
    for k, v in recipes.items():
        first_entry = v[0] if isinstance(v, list) else v
        if isinstance(first_entry, dict) and first_entry.get("_type") == "multiblock":
            multiblocks[k] = v
        elif isinstance(first_entry, dict):
            singleblocks[k] = v
    return multiblocks, singleblocks

# Return the best matching recipe variant for the given tech level.
# If multiple variants exist, prioritize the one with the highest applicable tag ≤ current tech level.
# Returns a tuple: (best_recipe_dict, matched_tag)
def get_best_recipe(name, recipes, tech_level):
    if name not in recipes:
        return None, None

    entry = recipes[name]
    if isinstance(entry, dict):
        return entry, "Any"

    tag_order = ["Any", "Steam", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPN", "UV", "UHV", "UEV", "UIV", "UMV", "UXV", "MAX"]
    max_index = tag_order.index(tech_level)

    best = None
    best_score = -1
    best_tag = None

    for r in entry:
        tags = r.get("_tags", [])
        recipe_max_idx = -1
        recipe_tag = None

        for tag in tags:
            if tag in tag_order:
                idx = tag_order.index(tag)
                if idx > recipe_max_idx:
                    recipe_max_idx = idx
                    recipe_tag = tag

        if recipe_max_idx <= max_index and recipe_max_idx > best_score:
            best = r
            best_score = recipe_max_idx
            best_tag = recipe_tag

    return best, best_tag

# === Recipe Formatting Utilities ===

# Format a list of raw materials into a plain text summary (no inventory considered).
def format_raw_materials(materials):
    lines = ["Total Raw Materials:"]
    for mat, qty in sorted(materials.items()):
        lines.append(f"- {qty}x {mat}")
    return "\n".join(lines)

# Format a list of raw materials adjusted against current inventory.
# Displays how much is needed, how much is owned, and whether the requirement is satisfied.
def format_raw_materials_with_inventory(materials, inventory, liquid_items=None):
    if liquid_items is None:
        liquid_items = []
    lines = ["Total Raw Materials (Adjusted for Inventory):"]
    for mat, required in sorted(materials.items()):
        owned = inventory.get(mat, 0)
        remaining = max(0, required - owned)
        status = f"(have {owned}, need {remaining})" if owned else f"(need {remaining})"
        checkmark = " ✔" if remaining == 0 else ""
        label = f"{required}L" if mat in liquid_items else str(required)
        lines.append(f"- {mat}: {label} {status}{checkmark}")
    return "\n".join(lines)

# Display the recipe in a human-readable format.
# Handles both flat and structured input formats.
def format_recipe_view(name, recipe):
    lines = [f"Recipe for '{name}':"]
    liquids = recipe.get("_liquids", [])
    
    if "_inputs" in recipe:
        for k, v in recipe["_inputs"].items():
            if not k.startswith("_"):
                label = f"{v}L" if k in liquids else str(v)
                lines.append(f"- {k}: {label}")
    else:
        for k, v in recipe.items():
            if not k.startswith("_"):
                label = f"{v}L" if k in liquids else str(v)
                lines.append(f"- {k}: {label}")
    
    if "_outputs" in recipe:
        lines.append("Outputs:")
        for out_item, qty in recipe["_outputs"].items():
            lines.append(f"- {out_item}: {qty}")

    if "_tags" in recipe:
        lines.append(f"Tags: {', '.join(recipe['_tags'])}")

    if "_machine" in recipe:
        lines.append(f"Machine: {recipe['_machine']}")

    return "\n".join(lines)

# === Computation/Crafting Logic ===

# Recursively compute the total base-level (raw) materials required to craft the given item.
# - Deducts from inventory when available
# - Handles nested input chains (i.e., components of components)
# - Stops recursion at items with no recipe (raw inputs)
# Returns: dict of item_name → total quantity needed
def calculate_raw_materials(name, quantity, recipes, inventory=None):
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

        # If no recipe exists for this item, treat it as a raw resource
        if not entry or not isinstance(entry, dict) or all(k.startswith("_") for k in entry.keys()):
            raw_needed[item] = raw_needed.get(item, 0) + qty_needed
            return

        outputs = entry.get("_outputs", {})
        output_count = outputs.get(item, 1)

        # Determine how many crafts are needed to fulfill the remaining quantity
        crafts_needed = ceil(remaining / output_count)
        inputs = entry.get("_inputs", entry)

        for sub, count in inputs.items():
            if not sub.startswith("_"):
                recurse(sub, count * crafts_needed)

    recurse(name, quantity)
    return raw_needed