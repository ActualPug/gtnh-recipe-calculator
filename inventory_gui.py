import json
import os
import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, ttk
from logic import split_recipe_types
from math import ceil

# Inventory file location
inventory_file = os.path.join(os.path.dirname(__file__), "inventory.json")

def load_inventory():
    if os.path.exists(inventory_file):
        with open(inventory_file, "r") as f:
            return json.load(f)
    return {}

def save_inventory(inventory):
    with open(inventory_file, "w") as f:
        json.dump(inventory, f, indent=2)

# GUI logic for inventory editing
def open_inventory_editor(root):
    inventory = load_inventory()

    inv_window = tb.Toplevel(root)
    inv_window.title("Inventory Editor")

    tk.Label(inv_window, text="Item Name").grid(row=0, column=0, padx=5, pady=5)
    tk.Label(inv_window, text="Quantity").grid(row=0, column=1, padx=5, pady=5)

    item_var = tk.StringVar()
    qty_var = tk.StringVar()

    with open(os.path.join(os.path.dirname(__file__), "recipes.json"), "r") as rf:
        recipes = json.load(rf)

    recipe_items = set(recipes.keys())
    raw_materials = set()

    for r in recipes.values():
        inputs = r.get("_inputs", r)
        for k in inputs:
            if not k.startswith("_") and k not in recipe_items:
                raw_materials.add(k)
    
    for raw in raw_materials:
        recipes[raw] = {
            "_tags": ["Raw", "Any"]
        }


    multiblocks, singleblocks = split_recipe_types(recipes)

    def group_by_tag(recipe_dict):
        grouped = {}
        for name, data in recipe_dict.items():
            tags = data.get("_tags", ["Any"])
            for tag in tags:
                if tag not in grouped:
                    grouped[tag] = []
                grouped[tag].append(name)
        return grouped
    
    single_grouped = group_by_tag(singleblocks)
    all_tags = ["Any", "Raw", "Steam", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPN", "UV", "UHV", "UEV", "UIV", "UMV", "UXV", "MAX"]
    selected_tags = {tag: tk.BooleanVar(value=True) for tag in all_tags}

    def filtered_by_tag_tags(recipe_name, recipe_dict):
        tags = recipe_dict.get(recipe_name, {}).get("_tags", [])
        return any(selected_tags[tag].get() for tag in tags if tag in selected_tags)

    def get_filtered_names(grouped):
        names = []
        seen = set()
        recipe_dict = {**singleblocks, **multiblocks}

        item_to_tags = {}
        for tag, items in grouped.items():
            if selected_tags[tag].get():
                for name in items:
                    if name not in item_to_tags:
                        item_to_tags[name] = []
                    item_to_tags[name].append(tag)

        # Handle recipe items
        for name, tags in sorted(item_to_tags.items()):
            if name in seen:
                continue
            if filtered_by_tag_tags(name, recipe_dict):
                recipe_tags = recipe_dict.get(name, {}).get("_tags", [])
                tag_prefix = " ".join(f"[{t}]" for t in sorted(recipe_tags))
                names.append(f"{tag_prefix} {name}")
                seen.add(name)

        # Handle raw materials
        for r in sorted(raw_materials):
            if r in seen:
                continue
            if filtered_by_tag_tags(r, recipes):
                tags = recipes.get(r, {}).get("_tags", [])
                tag_prefix = " ".join(f"[{t}]" for t in sorted(tags))
                names.append(f"{tag_prefix} {r}")
                seen.add(r)

        return names


    def filter_dropdown(event, dropdown, all_values, var):
        typed = var.get().lower().replace(" ", "_").replace("[Raw] ", "")
        filtered = [v for v in all_values if typed in v.lower().replace(" ", "_").replace("[Raw] ", "")]
        dropdown['values'] = filtered if filtered else all_values
        dropdown.filtered_values = filtered if filtered else all_values

    def resolve_dropdown_selection(event, dropdown, var):
        value = dropdown.get()
        if hasattr(dropdown, "filtered_values"):
            for v in dropdown.filtered_values:
                if value.lower().replace(" ", "_").replace("[Raw] ", "") == v.lower().replace(" ", "_").replace("[Raw] ", ""):
                    var.set(v)
                    break

    def update_inventory():
        item = item_var.get().strip()
        # Remove all [Tag] prefixes
        while item.startswith("["):
            closing = item.find("]")
            if closing == -1:
                break
            item = item[closing + 1:].strip()

        try:
            qty = int(qty_var.get().strip())
            if item in recipe_items or item in raw_materials:
                if qty == 0:
                    inventory.pop(item, None)
                else:
                    inventory[item] = qty
                save_inventory(inventory)
                refresh_display()
                messagebox.showinfo("Saved", f"{item} set to {qty}")
                item_var.set("")
                qty_var.set("")
            else:
                messagebox.showerror("Invalid Item", f"{item} is not a recognized recipe.")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer quantity.")

    def refresh_display():
        inventory_display.config(state=tk.NORMAL)
        inventory_display.delete(1.0, tk.END)
        for k, v in sorted(inventory.items()):
            inventory_display.insert(tk.END, f"{k}: {v}\n")
        inventory_display.config(state=tk.DISABLED)

    def clear_inventory():
        if messagebox.askyesno("Confirm", "Are you sure you want to clear your entire inventory?"):
            inventory.clear()
            save_inventory(inventory)
            refresh_display()
            messagebox.showinfo("Cleared", "Inventory cleared.")
    
    def refresh_dropdown():
        item_dropdown['values'] = get_filtered_names(single_grouped)
    
    def add_to_inventory():
        item = item_var.get().strip()
        # Remove all [Tag] prefixes
        while item.startswith("["):
            closing = item.find("]")
            if closing == -1:
                break
            item = item[closing + 1:].strip()

        try:
            qty = int(qty_var.get().strip())
            if qty <= 0:
                messagebox.showerror("Error", "Please enter a positive quantity to add.")
                return

            if item in recipe_items or item in raw_materials:
                inventory[item] = inventory.get(item, 0) + qty
                save_inventory(inventory)
                refresh_display()
                messagebox.showinfo("Added", f"{qty} added to '{item}' (new total: {inventory[item]})")
                item_var.set("")
                qty_var.set("")
            else:
                messagebox.showerror("Invalid Item", f"{item} is not a recognized recipe.")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer quantity.")
    
    def subtract_from_inventory():
        item = item_var.get().strip()
        # Remove all [Tag] prefixes
        while item.startswith("["):
            closing = item.find("]")
            if closing == -1:
                break
            item = item[closing + 1:].strip()

        try:
            qty = int(qty_var.get().strip())
            if qty <= 0:
                messagebox.showerror("Error", "Please enter a positive quantity to subtract.")
                return

            if item not in inventory:
                messagebox.showerror("Error", f"{item} is not in your inventory.")
                return

            inventory[item] -= qty
            if inventory[item] <= 0:
                del inventory[item]

            save_inventory(inventory)
            refresh_display()
            messagebox.showinfo("Subtracted", f"{qty} subtracted from '{item}'")
            item_var.set("")
            qty_var.set("")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid integer quantity.")

    def craft_item():
        nonlocal inventory
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

        recipe = recipes[item]
        if isinstance(recipe, list):
            recipe = recipe[0]

        output_count = recipe.get("_output_count", 1)
        crafts_needed = ceil(qty / output_count)

        # Determine components
        inputs = recipe.get("_inputs", recipe)
        required = {}
        for k, v in inputs.items():
            if not k.startswith("_"):
                required[k] = v * crafts_needed

        # Check inventory
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


        inventory[item] = inventory.get(item, 0) + qty

        save_inventory(inventory)
        refresh_display()
        messagebox.showinfo("Crafted", f"{item} x{qty} crafted successfully!")

    # Dropdown setup
    item_dropdown = ttk.Combobox(inv_window, textvariable=item_var, values=get_filtered_names(single_grouped) + [f"[Raw] {r}" for r in sorted(raw_materials)], width=30)
    item_dropdown.grid(row=1, column=0, padx=5, pady=5)

    # Always resolve based on visible text (not index)
    item_dropdown.bind("<KeyRelease>", lambda e: filter_dropdown(e, item_dropdown, get_filtered_names(single_grouped), item_var))
    item_dropdown.bind("<<ComboboxSelected>>", lambda e: resolve_dropdown_selection(e, item_dropdown, item_var))
    item_dropdown.bind("<Return>", lambda e: resolve_dropdown_selection(e, item_dropdown, item_var))

    qty_entry = tk.Entry(inv_window, textvariable=qty_var, width=10)
    qty_entry.grid(row=1, column=1, padx=5, pady=5)

    button_frame_inv = tk.Frame(inv_window)
    button_frame_inv.grid(row=2, column=0, columnspan=2, pady=5)
    tk.Button(button_frame_inv, text="Add", command=add_to_inventory).grid(row=0, column=0, padx=5)
    tk.Button(button_frame_inv, text="Subtract", command=subtract_from_inventory).grid(row=0, column=1, padx=5)
    tk.Button(button_frame_inv, text="Update", command=update_inventory).grid(row=0, column=2, padx=5)
    tk.Button(button_frame_inv, text="Craft", command=craft_item).grid(row=0, column=3, padx=5)
    tk.Button(button_frame_inv, text="Clear Inventory", command=clear_inventory).grid(row=0, column=4, padx=5)

    inventory_display = tk.Text(inv_window, height=10, width=50, state=tk.DISABLED)
    inventory_display.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

    tk.Label(inv_window, text="Filter by Tag").grid(row=4, column=0, columnspan=2)
    filter_frame = tk.Frame(inv_window)
    filter_frame.grid(row=5, column=0, columnspan=2)

    def set_all_tags(value):
        for var in selected_tags.values():
            var.set(value)
        refresh_dropdown()

    tag_button_frame = tk.Frame(inv_window)
    tag_button_frame.grid(row=6, column=0, columnspan=2)
    tk.Button(tag_button_frame, text="Select All Tags", command=lambda: set_all_tags(True)).grid(row=0, column=0, pady=2, padx=5)
    tk.Button(tag_button_frame, text="Clear Tags", command=lambda: set_all_tags(False)).grid(row=0, column=1, pady=2, padx=5)

    columns_per_row = 6  # or whatever fits your screen nicely
    for i, tag in enumerate(all_tags):
        row = i // columns_per_row
        col = i % columns_per_row
        cb = tk.Checkbutton(filter_frame, text=tag, variable=selected_tags[tag], command=refresh_dropdown)
        cb.grid(row=row, column=col, pady=2, padx=2)

    refresh_dropdown()
    refresh_display()