"""
GTNH Recipe Calculator GUI
-----------------------
A Tkinter interface for viewing, editing, and calculating material requirements for GregTech: New Horizons crafting recipes.

Features:
- Add/Edit/Delete recipes with tech-level tagging
- View materials required with raw/recursive breakdown
- Filter recipes by tech tag
- Inventory-aware material estimation

Author: ActualPug on github: https://github.com/ActualPug
"""

# === Standard library ===
from math import ceil

# === Third-party ===
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb

# === Internal modules ===
from inventory_gui import open_inventory_editor  # type: ignore
from logic import (
    load_recipes, save_recipes, split_recipe_types,
    calculate_raw_materials, format_raw_materials,
    format_recipe_view, format_raw_materials_with_inventory,
    get_best_recipe
)  # type: ignore

# === Constants ===
ALL_TAGS = ["Any", "Steam", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPN", "UV", "UHV", "UEV", "UIV", "UMV", "UXV", "MAX"]
ENTRY_WIDTH = 40

# === Recipe loading and categorization ===
recipes = load_recipes()
multiblocks, singleblocks = split_recipe_types(recipes)
last_viewed_recipe = None

# === Utility Functions ===
# These functions support recipe filtering, dropdown management, and tag-based view logic.

# Group all recipe names under their associated tech level tags (e.g. "LV", "EV").
# Each tag will map to a list of item names that can be crafted at that tier.
def group_by_tag(recipe_dict):
    grouped = {}
    for name, data in recipe_dict.items():
        entry = data[0] if isinstance(data, list) else data
        tags = entry.get("_tags", ["Any"])
        for tag in tags:
            grouped.setdefault(tag, []).append(name)
    return grouped

# Return a list of recipe names (formatted as "[TAG] name") that match the currently selected tech levels.
# Only includes items whose "best" variant (based on current tech) also matches a selected tag.
def get_filtered_names(grouped):
    names = []
    recipe_dict = {**singleblocks, **multiblocks}

    item_to_tags = {}
    for tag, items in grouped.items():
        if selected_tags[tag].get():
            for name in items:
                if name not in item_to_tags:
                    item_to_tags[name] = []
                item_to_tags[name].append(tag)

    for name in sorted(item_to_tags.keys()):
        # Chooses the recipe variant that best matches the current tech level or returns default.
        best_entry, matching_tag = get_best_recipe(name, recipe_dict, current_tech_level.get())
        if not best_entry:
            continue
        # Skip items whose best_tag isn't selected in the checkboxes
        if not selected_tags.get(matching_tag, tk.BooleanVar()).get():
            continue
        tag_prefix = f"[{matching_tag}]" if matching_tag else ""
        names.append(f"{tag_prefix} {name}")

    return names

# Determine whether the given recipe has at least one tag that is currently selected in the filter UI.
# Used to decide visibility of a recipe entry based on tag checkboxes.
def filtered_by_tag_tags(recipe_name, recipe_dict):
    entry = recipe_dict.get(recipe_name)
    if isinstance(entry, list):
        entry = entry[0]
    elif not isinstance(entry, dict):
        return False
    tags = entry.get("_tags", [])
    return any(tag_filter_selection.get(tag, tk.BooleanVar()).get() for tag in tags)

# Refreshes all recipe data, re-categorizes recipes, and updates the dropdown lists to reflect current filters.
# Typically called after a recipe is added, edited, or deleted.
def update_dropdowns():
    global multiblocks, singleblocks, single_grouped, multi_grouped
    # Separates recipes into multiblocks and singleblocks based on _type metadata.
    multiblocks, singleblocks = split_recipe_types(recipes)
    single_grouped = group_by_tag(singleblocks)
    multi_grouped = group_by_tag(multiblocks)
    refresh_dropdowns()

# Bulk-toggle all tag filters ON or OFF, then refresh the dropdowns.
# Used by "Select All Filter Tags" and "Clear Filter Tags" buttons.
def set_view_filter_tags(value):
    for var in selected_tags.values():
        var.set(value)
    refresh_dropdowns()

# Dynamically filter dropdown values based on what the user types.
# Replaces spaces with underscores and performs a case-insensitive match.
def filter_dropdown(event, dropdown, all_values, var):
    typed = var.get().lower().replace(" ", "_")
    filtered = [v for v in all_values if typed in v.lower().replace(" ", "_")]
    dropdown['values'] = filtered if filtered else all_values
    dropdown.filtered_values = filtered if filtered else all_values

# Set the dropdown variable to the matching filtered value (if one exists).
# Triggered when the user selects an item or presses Enter in the dropdown.
def resolve_dropdown_selection(event, dropdown, var):
    value = dropdown.get()
    if hasattr(dropdown, "filtered_values"):
        for v in dropdown.filtered_values:
            if value.lower().replace(" ", "_") == v.lower().replace(" ", "_"):
                var.set(v)
                break

# Apply the current tag filters and update both singleblock and multiblock dropdown options.
def refresh_dropdowns():
    single_dropdown['values'] = get_filtered_names(single_grouped)
    multi_dropdown['values'] = get_filtered_names(multi_grouped)

# === Recipe Logic ===

# --- Add Recipe ---
# Parses user input from form fields, constructs a recipe dictionary, and inserts or updates it in the recipe database.
def add_recipe():
    item = item_entry.get().strip()
    components_raw = components_entry.get().strip()
    outputs_raw = outputs_entry.get().strip()

    if not item:
        messagebox.showwarning("Input error", "Please fill all fields.")
        return

    try:
        components = {}
        # Parse component input (e.g. "bronze_plate:6")
        for pair in components_raw.split(","):
            name, qty = pair.strip().split(":")
            qty_str = qty.strip()
            if qty_str.endswith("L"):
                qty_value = int(qty_str[:-1])
            else:
                qty_value = int(qty_str)
            components[name.strip()] = qty_value

        if recipe_type.get() == "multiblock":
            components["_type"] = "multiblock"

        outputs_raw = outputs_entry.get().strip()
        if outputs_raw:
            output_dict = {}
            # Parse output quantities from user input and add to components
            for pair in outputs_raw.split(","):
                name, qty = pair.strip().split(":")
                output_dict[name.strip()] = int(qty.strip())
            components["_outputs"] = output_dict
        else:
            messagebox.showerror("Missing Output", "You must specify at least one output.")
            return
        
        components["_tags"] = ["Any", recipe_tech_level.get()] if recipe_tech_level.get() != "Any" else ["Any"]

        selected_tag = recipe_tech_level.get()
        components["_tags"] = ["Any", selected_tag] if selected_tag != "Any" else ["Any"]

        machine = machine_entry.get().strip()
        if machine:
            components["_machine"] = machine

        # Insert or update recipe entry in the dictionary
        # If multiple variants exist, match and replace one with the same outputs and inputs
        if item not in recipes:
            recipes[item] = [components]
        elif isinstance(recipes[item], list):
            # Replace recipe with same primary tag
            replaced = False
            for i, existing in enumerate(recipes[item]):
                # Match by output structure, not just tags
                def strip_metadata(d):
                    return {k: v for k, v in d.items() if not k.startswith("_")}

                if (
                    existing.get("_outputs") == components.get("_outputs") and
                    strip_metadata(existing) == strip_metadata(components)
                ):
                    # Update the tech level tags
                    components["_tags"] = ["Any", selected_tag] if selected_tag != "Any" else ["Any"]
                    recipes[item][i] = components
                    replaced = True
                    break
            if not replaced:
                recipes[item].append(components)
        else:
            # Convert old format and replace
            old = recipes[item]
            old_tags = old.get("_tags", [])
            if selected_tag in old_tags:
                recipes[item] = [components]
            else:
                recipes[item] = [old, components]

        # Persist updated recipe data and refresh UI
        save_recipes(recipes)
        update_dropdowns()
        messagebox.showinfo("Success", f"Added/updated recipe for '{item}'!")
        item_entry.delete(0, tk.END)
        components_entry.delete(0, tk.END)
        outputs_entry.delete(0, tk.END)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse: {e}")

# --- Edit Recipe ---
# Loads an existing recipe into the form fields to allow editing.
def edit_recipe(name):
    if name not in recipes:
        messagebox.showerror("Error", f"'{name}' does not exist.")
        return

    # Selects the best matching recipe variant for current tech level
    recipe, tag = get_best_recipe(name, recipes, current_tech_level.get())
    if not recipe:
        messagebox.showerror("Error", f"No valid recipe for '{name}' at current tech level.")
        return

    # Populate GUI form fields with the recipe data
    item_entry.delete(0, tk.END)
    item_entry.insert(0, name)

    components_entry.delete(0, tk.END)
    component_str = ", ".join(f"{k}:{v}" for k, v in recipe.items() if not k.startswith("_"))
    components_entry.insert(0, component_str)
    machine_entry.insert(0, recipe.get("_machine", ""))

    outputs_entry.delete(0, tk.END)
    if "_outputs" in recipe:
        output_str = ", ".join(f"{k}:{v}" for k, v in recipe["_outputs"].items())
        outputs_entry.insert(0, output_str)


    recipe_tech_level.set(tag if tag else "Any")
    recipe_type.set("multiblock" if recipe.get("_type") == "multiblock" else "singleblock")

    messagebox.showinfo("Edit Mode", f"Now editing '{name}'. Click 'Add Recipe' to save changes.")

# --- Delete Recipe ---
# Deletes a specific variant of a recipe based on selected tech tag.
def delete_selected_recipe():
    selection = single_var.get()
    if not selection:
        messagebox.showwarning("No Selection", "Please select a recipe to delete.")
        return

    # Extract tag and item name from "[Tag] item_name"
    if selection.startswith("[") and "]" in selection:
        selected_tag = selection[1:].split("]")[0]
        name = selection.split("] ", 1)[-1].strip()
    else:
        selected_tag = "Any"
        name = selection.strip()

    if name not in recipes:
        messagebox.showerror("Error", f"No recipe found for '{name}'.")
        return

    # Confirm with user
    confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the '{name}' recipe for tech level '{selected_tag}'?")
    if not confirm:
        return

    entry = recipes[name]

    if isinstance(entry, list):
        # Remove only the variant matching the selected tag
        recipes[name] = [r for r in entry if selected_tag not in r.get("_tags", [])]

        # If no variants remain, delete the whole item
        if not recipes[name]:
            del recipes[name]
    else:
        # Single-recipe case
        if selected_tag in entry.get("_tags", []):
            del recipes[name]

    save_recipes(recipes)
    update_dropdowns()
    messagebox.showinfo("Deleted", f"Successfully deleted '{name}' recipe for tech level '{selected_tag}'.")

# --- View Selected Recipe ---
# Displays the formatted recipe text in the output text area.
def view_selected_recipe(name):
    global last_viewed_recipe
    last_viewed_recipe = name

    output_text.config(state=tk.NORMAL)
    output_text.delete(1.0, tk.END)

    if name in recipes:
        # Chooses the recipe variant that best matches the current tech level or returns default.
        best_recipe, _ = get_best_recipe(name, recipes, current_tech_level.get())
        formatted = format_recipe_view(name, best_recipe)
        output_text.insert(tk.END, formatted)
    else:
        output_text.insert(tk.END, f"No recipe found for '{name}'.")

    output_text.config(state=tk.DISABLED)

# --- View Raw Materials ---
# Displays the materials needed for a recipe either as raw items or full dependency tree, depending on the user's "Show Raw Materials" selection.
def view_raw_materials(name):
    global last_viewed_recipe
    last_viewed_recipe = name

    output_text.config(state=tk.NORMAL)
    output_text.delete(1.0, tk.END)

    if name in recipes:
        from inventory_gui import load_inventory  # type: ignore
        inventory = load_inventory()

        try:
            raw_quantity = quantity_var_single.get() if name in singleblocks else quantity_var_multi.get()
            if raw_quantity.strip().endswith("L"):
                quantity = int(raw_quantity.strip()[:-1])
            else:
                quantity = int(raw_quantity.strip())
        except ValueError:
            quantity = 1

        show_raw = show_raw_var_single.get() if name in singleblocks else show_raw_var_multi.get()

        if show_raw:
            # Raw material breakdown (deepest level only)
            raw_materials = calculate_raw_materials(name, quantity, recipes, inventory.copy())
            entry = recipes.get(name)
            if isinstance(entry, list):
                entry = entry[0]
            elif not isinstance(entry, dict):
                entry = {}

            formatted = format_raw_materials_with_inventory(raw_materials, inventory)

            output_text.insert(tk.END, formatted)

            if all(max(0, raw_materials[k] - inventory.get(k, 0)) == 0 for k in raw_materials):
                output_text.insert(tk.END, "\n\n✔ All materials available!")

        else:
            # Inventory-aware full component breakdown (deduct top-down)
            original_inventory = inventory
            inventory = inventory.copy()  # this one gets mutated
            component_totals = {}

            # Recursively traverse recipe tree to gather total required materials, accounting for what is already in inventory
            def collect_components(item, qty_needed):
                nonlocal inventory
                entry = recipes.get(item)
                # Base case: fully satisfied or no recipe available
                if isinstance(entry, list):
                    entry = entry[0]

                # Check how much we already have
                have = inventory.get(item, 0)
                remaining = max(0, qty_needed - have)
                inventory[item] = max(0, have - qty_needed)

                # Always record the total needed (regardless of how much inventory satisfies it)
                component_totals[item] = component_totals.get(item, 0) + qty_needed

                # ✅ If fully satisfied by inventory, no need to recurse
                if remaining == 0:
                    return

                # Raw material or no recipe — stop here
                if not entry or not isinstance(entry, dict) or all(k.startswith("_") for k in entry.keys()):
                    return

                # Crafting logic
                outputs = entry.get("_outputs", {})
                output_count = outputs.get(item, 1)
                crafts_needed = ceil(remaining / output_count)

                inputs = entry.get("_inputs", entry)

                # Recursive case: calculate how many crafts are needed and descend into inputs
                for sub, count in inputs.items():
                    if not sub.startswith("_"):
                        collect_components(sub, count * crafts_needed)

            collect_components(name, quantity)

            # Format and display each required material along with machine info 
            output_text.insert(tk.END, f"All Components Needed to Build {quantity}x {name}:\n\n")

            for comp, needed in sorted(component_totals.items()):
                have = original_inventory.get(comp, 0)
                missing = max(0, needed - have)

                # Check if this component is a liquid in its own recipe
                comp_recipe = recipes.get(comp, {})
                if isinstance(comp_recipe, list):
                    comp_recipe = comp_recipe[0]

                status = f"(have {have}, need {missing})"
                checkmark = " ✔" if missing == 0 else ""
                # Check for machine used to make this component
                machine = ""
                comp_recipe = recipes.get(comp, {})
                if isinstance(comp_recipe, list):
                    comp_recipe = comp_recipe[0]
                if isinstance(comp_recipe, dict):
                    machine = comp_recipe.get("_machine", "")

                machine_str = f" [{machine}]" if machine else ""
                output_text.insert(tk.END, f"- {comp}: {needed} {status}{checkmark}{machine_str}\n")


            if all(max(0, component_totals[k] - original_inventory.get(k, 0)) == 0 for k in component_totals):
                output_text.insert(tk.END, "\n\n✔ All materials available!")

    else:
        output_text.insert(tk.END, f"No recipe found for '{name}'.")

    output_text.config(state=tk.DISABLED)

# --- View Component Tree ---
# Displays a formatted tree view of all components needed to craft a specific recipe.
def view_component_tree():
    output_text.config(state=tk.NORMAL)
    output_text.delete(1.0, tk.END)

    global last_viewed_recipe

    if not last_viewed_recipe or last_viewed_recipe not in recipes:
        output_text.insert(tk.END, "No recipe recently viewed.")
        output_text.config(state=tk.DISABLED)
        return

    name = last_viewed_recipe

    from inventory_gui import load_inventory
    inventory = load_inventory()

    try:
        raw_quantity = quantity_var_single.get() if name in singleblocks else quantity_var_multi.get()
        if raw_quantity.strip().endswith("L"):
            quantity = int(raw_quantity.strip()[:-1])
        else:
            quantity = int(raw_quantity.strip())
    except ValueError:
        quantity = 1


    output_text.insert(tk.END, f"Component Tree for: {name} (x{quantity})\n\n")


    def recurse(item, qty_needed, ancestors_last=[]):
        # Chooses the recipe variant that best matches the current tech level or returns default.
        entry, _ = get_best_recipe(item, recipes, current_tech_level.get())
        if isinstance(entry, list):
            entry = entry[0]

        have = inventory.get(item, 0)
        remaining = max(0, qty_needed - have)
        inventory[item] = max(0, have - qty_needed)

        # Build tree visual structure based on ancestry depth and branch position
        prefix = ""
        for is_last in ancestors_last[:-1]:
            prefix += "   " if is_last else "│  "
        if ancestors_last:
            prefix += "└─ " if ancestors_last[-1] else "├─ "

        item_recipe = recipes.get(item, {})
        if isinstance(item_recipe, list):
            item_recipe = item_recipe[0]

        line = f"{prefix}{item} x{qty_needed} (have {have}, need {remaining})"
        if remaining == 0:
            line += " ✔"
        output_text.insert(tk.END, line + "\n")


        # Stop if it's raw or unknown
        if not entry or not isinstance(entry, dict) or all(k.startswith("_") for k in entry.keys()):
            return

        # Recurse through all input components
        outputs = entry.get("_outputs", {})
        output_count = outputs.get(item, 1)
        crafts_needed = ceil(remaining / output_count)
        # Warn if output quantity can't be determined (likely a malformed recipe)
        if item not in outputs:
            output_text.insert(tk.END, f"⚠ Warning: '{item}' not found in _outputs of its recipe.\n\n")
            return


        inputs = entry.get("_inputs", entry)
        children = [k for k in inputs if not k.startswith("_")]

        for i, sub in enumerate(children):
            is_last = (i == len(children) - 1)
            recurse(sub, inputs[sub] * crafts_needed, ancestors_last + [is_last])

    recurse(name, quantity)
    output_text.config(state=tk.DISABLED)

# === GUI Initialization ===

# Create the main window and set up basic layout configuration
root = tb.Window(themename="darkly")
root.geometry("510x850")
root.title("GTNH Recipe Editor")

# Configure equal column weight
for i in range(2):
    root.grid_columnconfigure(i, weight=1)

# Global state variables
tag_filter_selection = {tag: tk.BooleanVar(value=True) for tag in ALL_TAGS}
selected_tags = {tag: tk.BooleanVar(value=True) for tag in ALL_TAGS}
current_tech_level = tk.StringVar(value="MAX")

# --- Group Recipes ---
single_grouped = group_by_tag(singleblocks)
multi_grouped = group_by_tag(multiblocks)

# === Input Widgets ===

# Define all entry fields, dropdowns, and state variables used in the form
item_entry = tk.Entry(root, width=ENTRY_WIDTH)

components_entry = tk.Entry(root, width=ENTRY_WIDTH)

outputs_entry = tk.Entry(root, width=ENTRY_WIDTH)

machine_entry = tk.Entry(root, width=ENTRY_WIDTH)

recipe_type = tk.StringVar(value="singleblock")

recipe_tech_level = tk.StringVar(value="Any")

filter_frame = tk.Frame(root)
columns_per_row = 8  # or whatever fits your screen nicely

view_tag_button_frame = tk.Frame(root)

single_var = tk.StringVar()
single_dropdown = ttk.Combobox(root, textvariable=single_var, values=get_filtered_names(single_grouped), width=ENTRY_WIDTH)

# Frame for single-recipe controls (view/edit/delete/materials)
button_frame_single = tk.Frame(root) 
quantity_var_single = tk.StringVar(value="1")
quantity_entry_single = tk.Entry(button_frame_single, textvariable=quantity_var_single, width=5)
show_raw_var_single = tk.BooleanVar(value=True)

multi_var = tk.StringVar()
multi_dropdown = ttk.Combobox(root, textvariable=multi_var, values=get_filtered_names(multi_grouped), width=ENTRY_WIDTH)

# Frame for multi-recipe controls (view/edit/delete/materials)
button_frame_multi = tk.Frame(root)
quantity_var_multi = tk.StringVar(value="1")
quantity_entry_multi = tk.Entry(button_frame_multi, textvariable=quantity_var_multi, width=5)
show_raw_var_multi = tk.BooleanVar(value=True)

output_text = tk.Text(root, height=15, width=75)
output_text.configure(font=("Consolas", 10))  # or ("Courier New", 10)
output_text.config(state=tk.DISABLED)

view_tree_button_frame = tk.Frame(root)

tech_level_frame = tk.Frame(root)

# === Widget Layout ===

# -- Add Recipe Section --
# Inputs for defining a new crafting recipe
tk.Label(root, text="Add a Recipe", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5))

tk.Label(root, text="Item Name").grid(row=1, column=0, sticky="e", pady=2)
item_entry.grid(row=1, column=1, sticky="w", pady=2)

tk.Label(root, text="Component(s) (e.g. bronze_plate:6, brick:1)").grid(row=2, column=0, sticky="e", pady=2)
components_entry.grid(row=2, column=1, sticky="w", pady=2)

tk.Label(root, text="Outputs (e.g. sulfur_dust:1, arsenic_dust:1)").grid(row=3, column=0, sticky="e", pady=2)
outputs_entry.grid(row=3, column=1, sticky="w", pady=2)

tk.Label(root, text="Where to Craft (e.g. crafting_table, compressor)").grid(row=4, column=0, sticky="e", pady=2)
machine_entry.grid(row=4, column=1, sticky="w", pady=2)  # wherever appropriate

tk.Label(root, text="Recipe Type").grid(row=5, column=0, sticky="e", pady=2)
tk.OptionMenu(root, recipe_type, "singleblock", "multiblock").grid(row=5, column=1, sticky="w", pady=2)

tk.Label(root, text="Recipe Tech Level", font=("Arial", 10)).grid(row=6, column=0, sticky="e", pady=2)
tk.OptionMenu(root, recipe_tech_level, *ALL_TAGS).grid(row=6, column=1, sticky="w", pady=2)

tk.Button(root, text="Add Recipe", command=lambda: add_recipe()).grid(row=7, column=0, columnspan=2, pady=10)

# -- View Controls --
# Buttons for viewing, editing, and calculating materials
tk.Label(root, text="View a Recipe", font=("Arial", 12, "bold")).grid(row=8, column=0, columnspan=2, pady=(10, 5))

tk.Label(root, text="Filter by Tag", font=("Arial", 10, "bold")).grid(row=9, column=0, columnspan=2)

filter_frame.grid(row=10, column=0, columnspan=2)
for i, tag in enumerate(ALL_TAGS):
    row = i // columns_per_row
    col = i % columns_per_row
    cb = tk.Checkbutton(filter_frame, text=tag, variable=selected_tags[tag], command=refresh_dropdowns)
    cb.grid(row=row, column=col, pady=2, padx=5)

view_tag_button_frame.grid(row=11, column=0, columnspan=2, pady=2)
tk.Button(view_tag_button_frame, text="Select All Filter Tags", command=lambda: set_view_filter_tags(True)).grid(row=0, column=0, padx=5)
tk.Button(view_tag_button_frame, text="Clear Filter Tags", command=lambda: set_view_filter_tags(False)).grid(row=0, column=1, padx=5)

tk.Label(root, text="Singleblock Recipes").grid(row=12, column=0, sticky="e", pady=2)
single_dropdown.grid(row=12, column=1, sticky="w", pady=2)

# Extract the recipe name from the dropdown (format: [TAG] name)
# single_var.get().split('] ')[-1]
button_frame_single.grid(row=13, column=0, columnspan=2, pady=2)
tk.Button(button_frame_single, text="View", command=lambda: view_selected_recipe(single_var.get().split('] ')[-1])).grid(row=0, column=0, padx=5)
tk.Button(button_frame_single, text="Edit", command=lambda: edit_recipe(single_var.get().split('] ')[-1])).grid(row=0, column=2, padx=5)
tk.Button(button_frame_single, text="Delete", command=lambda: delete_selected_recipe()).grid(row=0, column=1, padx=5)
tk.Button(button_frame_single, text="Materials", command=lambda: view_raw_materials(single_var.get().split('] ')[-1])).grid(row=0, column=3, padx=5)
tk.Label(button_frame_single, text="Quantity to Build").grid(row=0, column=4, sticky="e", padx=5)
quantity_entry_single.grid(row=0, column=5, sticky="w", padx=5)
tk.Checkbutton(button_frame_single, text="Show Raw Materials", variable=show_raw_var_single).grid(row=0, column=6, padx=5)

tk.Label(root, text="Multiblock Recipes").grid(row=14, column=0, sticky="e", pady=2)
multi_dropdown.grid(row=14, column=1, sticky="w", pady=2)

button_frame_multi.grid(row=15, column=0, columnspan=2, pady=2)
tk.Button(button_frame_multi, text="View", command=lambda: view_selected_recipe(multi_var.get().split('] ')[-1])).grid(row=0, column=0, padx=5)
tk.Button(button_frame_multi, text="Edit", command=lambda: edit_recipe(multi_var.get().split('] ')[-1])).grid(row=0, column=2, padx=5)
tk.Button(button_frame_multi, text="Delete", command=lambda: delete_selected_recipe()).grid(row=0, column=1, padx=5)
tk.Button(button_frame_multi, text="Materials", command=lambda: view_raw_materials(multi_var.get().split('] ')[-1])).grid(row=0, column=3, padx=5)
tk.Label(button_frame_multi, text="Quantity to Build").grid(row=0, column=4, sticky="e", padx=5)
quantity_entry_multi.grid(row=0, column=5, sticky="w", padx=5)
tk.Checkbutton(button_frame_multi, text="Show Raw Materials", variable=show_raw_var_multi).grid(row=0, column=6, padx=5)

output_text.grid(row=17, column=0, columnspan=2, pady=5)

view_tree_button_frame.grid(row=18, column=0, columnspan=2, pady=2)
tk.Button(view_tree_button_frame, text="Manage Inventory", command=lambda: open_inventory_editor(root)).grid(row=0, column=0, padx=5)
tk.Button(view_tree_button_frame, text="View Tree", command=view_component_tree).grid(row=0, column=1, padx=5)

tech_level_frame.grid(row=19, column=0, columnspan=2, pady=2)
tk.Label(tech_level_frame, text="Your Tech Level").grid(row=0, column=0, sticky="e", padx=5)
tk.OptionMenu(tech_level_frame, current_tech_level, *ALL_TAGS).grid(row=0, column=1, sticky="w", padx=5)

# === Widget Bindings ===

# Filter dropdown suggestions as the user types
single_dropdown.bind("<KeyRelease>", lambda e: filter_dropdown(e, single_dropdown, get_filtered_names(single_grouped), single_var))
multi_dropdown.bind("<KeyRelease>", lambda e: filter_dropdown(e, multi_dropdown, get_filtered_names(multi_grouped), multi_var))

# Set dropdown value when user selects from the list or presses enter
single_dropdown.bind("<<ComboboxSelected>>", lambda e: resolve_dropdown_selection(e, single_dropdown, single_var))
multi_dropdown.bind("<<ComboboxSelected>>", lambda e: resolve_dropdown_selection(e, multi_dropdown, multi_var))

single_dropdown.bind("<Return>", lambda e: resolve_dropdown_selection(e, single_dropdown, single_var))
multi_dropdown.bind("<Return>", lambda e: resolve_dropdown_selection(e, multi_dropdown, multi_var))

# === Mainloop ===
root.mainloop()