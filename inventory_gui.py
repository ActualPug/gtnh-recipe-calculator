"""
GTNH Recipe Calculator Inventory GUI
---------------------
This module provides a Toplevel Tkinter window that allows the user to:
- View and manage their in-game inventory
- Add, subtract, and update item quantities
- Craft items if all materials are present
- Filter available items by tech level tags

Author: ActualPug on github: https://github.com/ActualPug
"""

# === Imports ===
# Standard libraries for file handling, math, and GUI
# 'logic' module provides recipe classification logic shared with main GUI
import json
import os
import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, ttk
from math import ceil
from logic import split_recipe_types

# === Paths and Global Constants ===
# Path to the inventory JSON file (stored alongside this script)
# Ordered list of all tech level tags used for filtering and labeling
inventory_file = os.path.join(os.path.dirname(__file__), "inventory.json")
ALL_TAGS = ["Any", "Steam", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPN", "UV", "UHV", "UEV", "UIV", "UMV", "UXV", "MAX"]

# === Inventory File Utilities ===

# Load the inventory from disk, if the file exists.
# Returns a dictionary of item_name → quantity.
def load_inventory():
    if os.path.exists(inventory_file):
        with open(inventory_file, "r") as f:
            return json.load(f)
    return {}

# Save the given inventory dictionary to disk in JSON format.
def save_inventory(inventory):
    with open(inventory_file, "w") as f:
        json.dump(inventory, f, indent=2)

# === Dropdown Filtering Utilities ===

# Filter the dropdown options in real-time based on the user's typed input.
# Normalizes strings by replacing spaces and removing '[Raw]' labels for matching.
def filter_dropdown(event, dropdown, all_values, var):
    typed = var.get().lower().replace(" ", "_").replace("[Raw] ", "")
    filtered = [v for v in all_values if typed in v.lower().replace(" ", "_").replace("[Raw] ", "")]
    dropdown['values'] = filtered if filtered else all_values
    dropdown.filtered_values = filtered if filtered else all_values
    dropdown['values'] = filtered

# Finalize a dropdown selection by matching typed input with available filtered values.
# Ensures consistent formatting regardless of user case or spacing.
def resolve_dropdown_selection(event, dropdown, var):
    value = dropdown.get()
    if hasattr(dropdown, "filtered_values"):
        for v in dropdown.filtered_values:
            if value.lower().replace(" ", "_").replace("[Raw] ", "") == v.lower().replace(" ", "_").replace("[Raw] ", ""):
                var.set(v)
                break

# Group all recipe names under their corresponding tags (e.g., 'LV', 'HV').
# Returns a dictionary: tag → list of item names.
def group_by_tag(recipe_dict):
    grouped = {}
    for name, data in recipe_dict.items():
        entry = data[0] if isinstance(data, list) else data
        tags = entry.get("_tags", ["Any"])
        for tag in tags:
            if tag not in grouped:
                grouped[tag] = []
            grouped[tag].append(name)
    return grouped

# Generate a list of item names labeled with their most relevant tag, filtered by currently selected tags (e.g., [LV] Steel Plate).
# If multiple tags exist for a recipe, the highest-priority tag that matches the filter is used.
def get_filtered_names(recipe_dict, selected_tags):
    selected = [tag for tag, var in selected_tags.items() if var.get()]
    labeled_names = {}
    # Ordered tech level priority (higher index = more advanced)
    tag_priority = ["Any", "Raw", "Steam", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPN", "UV", "UHV", "UEV", "UIV", "UMV", "UXV", "MAX"]

    for name in sorted(recipe_dict):
        entries = recipe_dict[name]
        if not isinstance(entries, list):
            entries = [entries]

        best_tag = None
        best_index = -1

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tags = entry.get("_tags", [])
            for tag in tags:
                if tag in selected and tag_priority.index(tag) > best_index:
                    best_tag = tag
                    best_index = tag_priority.index(tag)

        if best_tag:
            labeled_names[name] = f"[{best_tag}] {name}"

    return list(labeled_names.values())

# === Inventory Editor Window ===

# Launches a new GUI window to manage, modify, and simulate inventory actions for GTNH recipes.
def open_inventory_editor(root):
    # === Recipe loading and categorization ===

    # Load all recipes and split them into multiblock and singleblock categories.
    with open(os.path.join(os.path.dirname(__file__), "recipes.json"), "r") as rf:
        recipes = json.load(rf)
    multiblocks, singleblocks = split_recipe_types(recipes)

    # === Tag Variables and Filter Setup ===

    # Helper to toggle all tag checkboxes for item filtering.
    def set_all_tags(value):
        for var in selected_tags.values():
            var.set(value)
        refresh_dropdown()
    
    # === Core Inventory Actions ===
    # These methods handle modifying the user's inventory: add, update, subtract, clear, and simulate crafting.

    # Set an item's quantity directly. Removes the item from inventory if qty is zero.
    # Rejects unknown items and non-integer input.
    def update_inventory():
        item = item_var.get().strip()
        # Remove all [Tag] prefixes
        while item.startswith("["):
            closing = item.find("]")
            if closing == -1:
                break
            item = item[closing + 1:].strip()

        try:
            qty_raw = qty_var.get().strip()
            if qty_raw.endswith("L"):
                qty = int(qty_raw[:-1])
            else:
                qty = int(qty_raw)
            
            if item in recipe_items or item in raw_materials:
                if qty == 0:
                    inventory.pop(item, None)
                else:
                    inventory[item] = qty
                save_inventory(inventory)
                refresh_display()
                refresh_dropdown()
                messagebox.showinfo("Saved", f"{item} set to {qty}")
                item_var.set("")
                qty_var.set("")
            else:
                messagebox.showerror("Invalid Item", f"{item} is not a recognized recipe.")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer quantity.")
    
    # Adds the specified quantity to an existing inventory item.
    # Rejects zero/negative amounts or unrecognized items.
    def add_to_inventory():
        item = item_var.get().strip()
        # Remove all [Tag] prefixes
        while item.startswith("["):
            closing = item.find("]")
            if closing == -1:
                break
            item = item[closing + 1:].strip()

        try:
            qty_raw = qty_var.get().strip()
            if qty_raw.endswith("L"):
                qty = int(qty_raw[:-1])
            else:
                qty = int(qty_raw)

            if qty <= 0:
                messagebox.showerror("Error", "Please enter a positive quantity to add.")
                return

            if item in recipe_items or item in raw_materials:
                inventory[item] = inventory.get(item, 0) + qty
                save_inventory(inventory)
                refresh_display()
                refresh_dropdown()
                messagebox.showinfo("Added", f"{qty} added to '{item}' (new total: {inventory[item]})")
                item_var.set("")
                qty_var.set("")
            else:
                messagebox.showerror("Invalid Item", f"{item} is not a recognized recipe.")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer quantity.")
    
    # Subtracts a specified quantity from an item in the inventory.
    # Deletes the item entirely if quantity drops to zero or below.
    def subtract_from_inventory():
        item = item_var.get().strip()
        # Remove all [Tag] prefixes
        while item.startswith("["):
            closing = item.find("]")
            if closing == -1:
                break
            item = item[closing + 1:].strip()
        
        try:
            qty_raw = qty_var.get().strip()
            if qty_raw.endswith("L"):
                qty = int(qty_raw[:-1])
            else:
                qty = int(qty_raw)

            if qty <= 0:
                messagebox.showerror("Error", "Please enter a positive quantity to subtract.")
                return

            if item not in inventory:
                messagebox.showerror("Error", f"{item} is not in your inventory.")
                return

            # Subtract, and remove if zero or less
            new_qty = inventory[item] - qty
            if new_qty <= 0:
                del inventory[item]
            else:
                inventory[item] = new_qty

            save_inventory(inventory)
            refresh_display()
            refresh_dropdown()
            messagebox.showinfo("Subtracted", f"{qty} subtracted from '{item}' (new total: {inventory.get(item, 0)})")
            item_var.set("")
            qty_var.set("")

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer quantity.")

    # Clears the entire inventory after user confirmation.
    def clear_inventory():
        if messagebox.askyesno("Confirm", "Are you sure you want to clear your entire inventory?"):
            inventory.clear()
            save_inventory(inventory)
            refresh_display()
            messagebox.showinfo("Cleared", "Inventory cleared.")
    
    # Refresh the inventory display box to reflect the current state.
    def refresh_display():
        inventory_display.config(state=tk.NORMAL)
        inventory_display.delete(1.0, tk.END)
        for k, v in sorted(inventory.items()):
            # Check if the item is a liquid
            item_recipe = recipes.get(k, {})
            if isinstance(item_recipe, list):
                item_recipe = item_recipe[0]
            inventory_display.insert(tk.END, f"{k}: {v}\n")
        inventory_display.config(state=tk.DISABLED)

    # Rebuild the item dropdown list based on selected tags.
    # Ensures that raw materials (not craftable) are included only if not already labeled.
    def refresh_dropdown():
        flat_recipes = {**singleblocks, **{raw: recipes[raw] for raw in raw_materials}}
        filtered = get_filtered_names(flat_recipes, selected_tags)

        existing_names = set(name.split("] ", 1)[-1] for name in filtered if "] " in name)
        raw_only = [f"[Raw] {r}" for r in sorted(raw_materials) if r not in existing_names]
        item_dropdown['values'] = filtered + raw_only
        item_var.set("")
        item_dropdown.set("")

    # Attempt to craft the selected item in the specified quantity.
    # Checks if inventory has enough components, deducts them, and adds outputs.
    # If insufficient materials exist, shows an error instead.
    def craft_item():
        nonlocal inventory
        # Helper: remove [Tag] prefix from dropdown labels
        def strip_tags(labeled_item):
            while labeled_item.startswith("["):
                closing = labeled_item.find("]")
                if closing == -1:
                    break
                labeled_item = labeled_item[closing + 1:].strip()
            return labeled_item

        item = strip_tags(item_var.get().strip())
        try:
            qty = int(qty_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer quantity.")
            return

        if item.endswith(" (raw)"):
            item = item.replace(" (raw)", "")

        if item not in recipes:
            messagebox.showerror("Error", f"No recipe found for '{item}'")
            return

        selected_tag = None
        label = item_var.get()
        if label.startswith("["):
            selected_tag = label[1:label.find("]")]
        item = strip_tags(label)

        # --- Find correct recipe variant based on user-selected tech level tag ---

        # Choose the correct recipe
        recipe_variants = recipes[item]
        if not isinstance(recipe_variants, list):
            recipe_variants = [recipe_variants]

        # Pick the matching tech-level recipe
        recipe = None
        for variant in recipe_variants:
            tags = variant.get("_tags", [])
            if selected_tag in tags:
                recipe = variant
                break

        if recipe is None:
            messagebox.showerror("Error", f"No matching recipe for {item} with tag [{selected_tag}]")
            return

        outputs = recipe.get("_outputs", {})
        if item not in outputs:
            messagebox.showerror("Error", f"'{item}' is not a valid output for its recipe.")
            return

        output_count = outputs[item]
        crafts_needed = ceil(qty / output_count)

        # Determine components
        inputs = recipe.get("_inputs", recipe)
        required = {}
        for k, v in inputs.items():
            if not k.startswith("_"):
                required[k] = v * crafts_needed

        # Check if user has enough of each input material
        missing = [f"{k} (need {required[k]}, have {inventory.get(k, 0)})"
                for k in required if inventory.get(k, 0) < required[k]]

        if missing:
            messagebox.showerror("Not enough materials", "Missing:\n" + "\n".join(missing))
            return

        # Deduct from inventory
        for k, v in required.items():
            inventory[k] -= v
            if inventory[k] <= 0:
                del inventory[k]

        # Add all outputs
        for out_item, out_qty in outputs.items():
            total_output = out_qty * crafts_needed
            inventory[out_item] = inventory.get(out_item, 0) + total_output

        save_inventory(inventory)
        refresh_display()
        refresh_dropdown()
        messagebox.showinfo("Crafted", f"{item} x{qty} crafted successfully!\n\nAlso produced:\n" +
                            "\n".join(f"{k}: {v * crafts_needed}" for k, v in outputs.items() if k != item))

    # === GUI Initialization ===
    # Set up the inventory editor window, load inventory data, and initialize GUI state variables.

    # Load existing inventory from disk and create a new window.
    inventory = load_inventory()
    inv_window = tb.Toplevel(root)
    inv_window.title("Inventory Editor")

    # Make columns equally flexible for responsive layout.
    for i in range(2):
        root.grid_columnconfigure(i, weight=1)

    # Set up all the necessary state: tag filters, entry fields, and recipe data tracking.
    selected_tags = {tag: tk.BooleanVar(value=True) for tag in ALL_TAGS}
    item_var = tk.StringVar()
    qty_var = tk.StringVar()
    recipe_items = set(recipes.keys())
    raw_materials = set()

    # Determine which items are raw materials (used in recipes but not produced by any recipe).
    # These will be added as "[Raw]" entries in the dropdown.
    for r in recipes.values():
        entry = r[0] if isinstance(r, list) else r
        inputs = entry.get("_inputs", entry)

        for k in inputs:
            if not k.startswith("_") and k not in recipe_items:
                raw_materials.add(k)
    
    for raw in raw_materials:
        recipes[raw] = {
            "_tags": ["Raw", "Any"]
        }

    # Group recipes by tag for later filtering and dropdown population.
    single_grouped = group_by_tag(singleblocks)

    # === Input Widgets ===
    # Define all widgets for item entry, quantity entry, inventory output, tag filters, and control buttons.

    # Combine recipes and raw materials into one dropdown list.
    # Avoid duplicates by checking which raw items are already labeled by a recipe.
    flat_recipes = {**singleblocks, **{raw: recipes[raw] for raw in raw_materials}}
    filtered = get_filtered_names(flat_recipes, selected_tags)
    existing_names = set(name.split("] ", 1)[-1] for name in filtered if "] " in name)
    raw_only = [f"[Raw] {r}" for r in sorted(raw_materials) if r not in existing_names]
    full_item_list = filtered + raw_only
    item_dropdown = ttk.Combobox(inv_window, textvariable=item_var, values=full_item_list, width=30)
    qty_entry = tk.Entry(inv_window, textvariable=qty_var, width=10)

    button_frame_inv = tk.Frame(inv_window)

    inventory_display = tk.Text(inv_window, height=10, width=50, state=tk.DISABLED)

    filter_frame = tk.Frame(inv_window)

    tag_button_frame = tk.Frame(inv_window)

    columns_per_row = 6  # or whatever fits your screen nicely

    # === Widget Layout ===
    # Arrange widgets in the window using grid layout.
    tk.Label(inv_window, text="Item Name").grid(row=0, column=0, padx=5, pady=5)
    tk.Label(inv_window, text="Quantity").grid(row=0, column=1, padx=5, pady=5)

    item_dropdown.grid(row=1, column=0, padx=5, pady=5)
    qty_entry.grid(row=1, column=1, padx=5, pady=5)

    button_frame_inv.grid(row=2, column=0, columnspan=2, pady=5)
    tk.Button(button_frame_inv, text="Add", command=add_to_inventory).grid(row=0, column=0, padx=5)
    tk.Button(button_frame_inv, text="Subtract", command=subtract_from_inventory).grid(row=0, column=1, padx=5)
    tk.Button(button_frame_inv, text="Update", command=update_inventory).grid(row=0, column=2, padx=5)
    tk.Button(button_frame_inv, text="Craft", command=craft_item).grid(row=0, column=3, padx=5)
    tk.Button(button_frame_inv, text="Clear Inventory", command=clear_inventory).grid(row=0, column=4, padx=5)

    inventory_display.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

    tk.Label(inv_window, text="Filter by Tag").grid(row=4, column=0, columnspan=2)
    
    filter_frame.grid(row=5, column=0, columnspan=2)

    tag_button_frame.grid(row=6, column=0, columnspan=2)
    tk.Button(tag_button_frame, text="Select All Tags", command=lambda: set_all_tags(True)).grid(row=0, column=0, pady=2, padx=5)
    tk.Button(tag_button_frame, text="Clear Tags", command=lambda: set_all_tags(False)).grid(row=0, column=1, pady=2, padx=5)

    for i, tag in enumerate(ALL_TAGS):
        row = i // columns_per_row
        col = i % columns_per_row
        cb = tk.Checkbutton(filter_frame, text=tag, variable=selected_tags[tag], command=refresh_dropdown)
        cb.grid(row=row, column=col, pady=2, padx=2)

    # === Widget Bindings ===
    # Bind keyboard and selection events to the item dropdown to enable dynamic filtering and selection.
    item_dropdown.bind("<KeyRelease>", lambda e: filter_dropdown(e, item_dropdown, full_item_list, item_var))

    item_dropdown.bind("<<ComboboxSelected>>", lambda e: resolve_dropdown_selection(e, item_dropdown, item_var))
    item_dropdown.bind("<Return>", lambda e: resolve_dropdown_selection(e, item_dropdown, item_var))

    # === Refresh GUI ===
    # Trigger initial population of the dropdown and inventory display.
    refresh_dropdown()
    refresh_display()