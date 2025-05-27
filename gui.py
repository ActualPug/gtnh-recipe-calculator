# gui.py
import ttkbootstrap as tb
import tkinter as tk
from tkinter import messagebox, ttk
from inventory_gui import open_inventory_editor # type: ignore
from logic import load_recipes, save_recipes, split_recipe_types, calculate_raw_materials, format_raw_materials, format_recipe_view, format_raw_materials_with_inventory # type: ignore
from math import ceil

recipes = load_recipes()
multiblocks, singleblocks = split_recipe_types(recipes)
last_viewed_recipe = None

# Group recipes by tag (e.g., 'steam')
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
multi_grouped = group_by_tag(multiblocks)
all_tags = ["Any", "Steam", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPN", "UV", "UHV", "UEV", "UIV", "UMV", "UXV", "MAX"]

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

    for name, tags in sorted(item_to_tags.items()):
        if filtered_by_tag_tags(name, recipe_dict):
            tag_prefix = " ".join(f"[{t}]" for t in sorted(tags))
            names.append(f"{tag_prefix} {name}")

    return names


def refresh_dropdowns():
    single_dropdown['values'] = get_filtered_names(single_grouped)
    multi_dropdown['values'] = get_filtered_names(multi_grouped)

def filtered_by_tag_tags(recipe_name, recipe_dict):
    tags = recipe_dict.get(recipe_name, {}).get("_tags", [])
    return any(tag_filter_selection[tag].get() for tag in tags if tag in tag_filter_selection)

# GUI Setup
root = tb.Window(themename="darkly")
root.geometry("800x900")
root.title("GTNH Recipe Editor")
tag_filter_selection = {tag: tk.BooleanVar(value=True) for tag in all_tags}
selected_tags = {tag: tk.BooleanVar(value=True) for tag in all_tags}

# Configure equal column weight
for i in range(2):
    root.grid_columnconfigure(i, weight=1)

# Widgets
uniform_entry_width = 40
item_entry = tk.Entry(root, width=uniform_entry_width)
components_entry = tk.Entry(root, width=uniform_entry_width)
output_count_entry = tk.Entry(root, width=uniform_entry_width)
recipe_type = tk.StringVar(value="singleblock")

single_var = tk.StringVar()
multi_var = tk.StringVar()
single_dropdown = ttk.Combobox(root, textvariable=single_var, values=get_filtered_names(single_grouped), width=uniform_entry_width)
multi_dropdown = ttk.Combobox(root, textvariable=multi_var, values=get_filtered_names(multi_grouped), width=uniform_entry_width)


single_dropdown.bind("<KeyRelease>", lambda e: filter_dropdown(e, single_dropdown, get_filtered_names(single_grouped), single_var))
multi_dropdown.bind("<KeyRelease>", lambda e: filter_dropdown(e, multi_dropdown, get_filtered_names(multi_grouped), multi_var))

single_dropdown.bind("<<ComboboxSelected>>", lambda e: resolve_dropdown_selection(e, single_dropdown, single_var))
multi_dropdown.bind("<<ComboboxSelected>>", lambda e: resolve_dropdown_selection(e, multi_dropdown, multi_var))

single_dropdown.bind("<Return>", lambda e: resolve_dropdown_selection(e, single_dropdown, single_var))
multi_dropdown.bind("<Return>", lambda e: resolve_dropdown_selection(e, multi_dropdown, multi_var))

output_text = tk.Text(root, height=15, width=75)
output_text.configure(font=("Consolas", 10))  # or ("Courier New", 10)

# Layout
# --- Add Section Header ---
tk.Label(root, text="Add a Recipe", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5))

tk.Label(root, text="Item Name").grid(row=1, column=0, sticky="e", pady=2)
item_entry.grid(row=1, column=1, sticky="w", pady=2)

tk.Label(root, text="Component(s) (e.g. bronze_plate:6, brick:1)").grid(row=2, column=0, sticky="e", pady=2)
components_entry.grid(row=2, column=1, sticky="w", pady=2)

tk.Label(root, text="Output Count").grid(row=3, column=0, sticky="e", pady=2)
output_count_entry.grid(row=3, column=1, sticky="w", pady=2)

tk.Label(root, text="Recipe Type").grid(row=4, column=0, sticky="e", pady=2)
tk.OptionMenu(root, recipe_type, "singleblock", "multiblock").grid(row=4, column=1, sticky="w", pady=2)


# Tag selector for new recipe
tk.Label(root, text="Tags for New Recipe", font=("Arial", 10)).grid(row=5, column=0, sticky="e", pady=2)
new_tag_frame = tk.Frame(root)
new_tag_frame.grid(row=5, column=1, sticky="w")
new_recipe_tags = {tag: tk.BooleanVar(value=False) for tag in all_tags}
columns_per_row = 8  # or whatever fits your screen nicely
for i, tag in enumerate(all_tags):
    row = i // columns_per_row
    col = i % columns_per_row
    cb = tk.Checkbutton(new_tag_frame, text=tag, variable=new_recipe_tags[tag])
    cb.grid(row=row, column=col, pady=2, padx=2)

def set_all_tags(value):
    for var in new_recipe_tags.values():
        var.set(value)
button_frame_multi = tk.Frame(root)
button_frame_multi.grid(row=6, column=0, columnspan=2, pady=2)
tk.Button(button_frame_multi, text="Select All Tags", command=lambda: set_all_tags(True)).grid(row=0, column=0, pady=2, padx=5)
tk.Button(button_frame_multi, text="Clear Tags", command=lambda: set_all_tags(False)).grid(row=0, column=1, pady=2, padx=5)

tk.Button(root, text="Add Recipe", command=lambda: add_recipe()).grid(row=7, column=0, columnspan=2, pady=10)

# --- View Section Header ---
tk.Label(root, text="View a Recipe", font=("Arial", 12, "bold")).grid(row=8, column=0, columnspan=2, pady=(10, 5))

tk.Label(root, text="Filter by Tag", font=("Arial", 10, "bold")).grid(row=9, column=0, columnspan=2)
filter_frame = tk.Frame(root)
filter_frame.grid(row=10, column=0, columnspan=2)
columns_per_row = 8  # or whatever fits your screen nicely
for i, tag in enumerate(all_tags):
    row = i // columns_per_row
    col = i % columns_per_row
    cb = tk.Checkbutton(filter_frame, text=tag, variable=selected_tags[tag], command=refresh_dropdowns)
    cb.grid(row=row, column=col, pady=2, padx=5)

view_tag_button_frame = tk.Frame(root)
view_tag_button_frame.grid(row=11, column=0, columnspan=2, pady=2)
tk.Button(view_tag_button_frame, text="Select All Filter Tags", command=lambda: set_view_filter_tags(True)).grid(row=0, column=0, padx=5)
tk.Button(view_tag_button_frame, text="Clear Filter Tags", command=lambda: set_view_filter_tags(False)).grid(row=0, column=1, padx=5)
tk.Label(root, text="Singleblock Recipes").grid(row=12, column=0, sticky="e", pady=2)
single_dropdown.grid(row=12, column=1, sticky="w", pady=2)
button_frame_single = tk.Frame(root) 
button_frame_single.grid(row=13, column=0, columnspan=2, pady=2)
tk.Button(button_frame_single, text="View", command=lambda: view_selected_recipe(single_var.get().split('] ')[-1])).grid(row=0, column=0, padx=5)
tk.Button(button_frame_single, text="Edit", command=lambda: edit_recipe(single_var.get().split('] ')[-1])).grid(row=0, column=2, padx=5)
tk.Button(button_frame_single, text="Delete", command=lambda: delete_selected_recipe(single_var.get().split('] ')[-1])).grid(row=0, column=1, padx=5)
tk.Button(button_frame_single, text="Materials", command=lambda: view_raw_materials(single_var.get().split('] ')[-1])).grid(row=0, column=3, padx=5)
quantity_var_single = tk.StringVar(value="1")
tk.Label(button_frame_single, text="Quantity to Build").grid(row=0, column=4, sticky="e", padx=5)
quantity_entry = tk.Entry(button_frame_single, textvariable=quantity_var_single, width=5)
quantity_entry.grid(row=0, column=5, sticky="w", padx=5)
show_raw_var_single = tk.BooleanVar(value=True)
tk.Checkbutton(button_frame_single, text="Show Raw Materials", variable=show_raw_var_single).grid(row=0, column=6, padx=5)

tk.Label(root, text="Multiblock Recipes").grid(row=14, column=0, sticky="e", pady=2)
multi_dropdown.grid(row=14, column=1, sticky="w", pady=2)
button_frame_multi = tk.Frame(root)
button_frame_multi.grid(row=15, column=0, columnspan=2, pady=2)
tk.Button(button_frame_multi, text="View", command=lambda: view_selected_recipe(multi_var.get().split('] ')[-1])).grid(row=0, column=0, padx=5)
tk.Button(button_frame_multi, text="Edit", command=lambda: edit_recipe(multi_var.get().split('] ')[-1])).grid(row=0, column=2, padx=5)
tk.Button(button_frame_multi, text="Delete", command=lambda: delete_selected_recipe(multi_var.get().split('] ')[-1])).grid(row=0, column=1, padx=5)
tk.Button(button_frame_multi, text="Materials", command=lambda: view_raw_materials(multi_var.get().split('] ')[-1])).grid(row=0, column=3, padx=5)
quantity_var_multi = tk.StringVar(value="1")
tk.Label(button_frame_multi, text="Quantity to Build").grid(row=0, column=4, sticky="e", padx=5)
quantity_entry = tk.Entry(button_frame_multi, textvariable=quantity_var_multi, width=5)
quantity_entry.grid(row=0, column=5, sticky="w", padx=5)
show_raw_var_multi = tk.BooleanVar(value=True)
tk.Checkbutton(button_frame_multi, text="Show Raw Materials", variable=show_raw_var_multi).grid(row=0, column=6, padx=5)

output_text.grid(row=17, column=0, columnspan=2, pady=5)
output_text.config(state=tk.DISABLED)

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
        quantity = int(quantity_var_single.get() if name in singleblocks else quantity_var_multi.get())
    except ValueError:
        quantity = 1

    output_text.insert(tk.END, f"Component Tree for: {name} (x{quantity})\n\n")

    def recurse(item, qty_needed, ancestors_last=[]):
        entry = recipes.get(item)
        if isinstance(entry, list):
            entry = entry[0]

        have = inventory.get(item, 0)
        remaining = max(0, qty_needed - have)
        inventory[item] = max(0, have - qty_needed)

        # Build the tree prefix
        prefix = ""
        for is_last in ancestors_last[:-1]:
            prefix += "   " if is_last else "│  "
        if ancestors_last:
            prefix += "└─ " if ancestors_last[-1] else "├─ "

        # Add this node line
        line = f"{prefix}{item} x{qty_needed} (have {have}, need {remaining})"
        if remaining == 0:
            line += " ✔"
        output_text.insert(tk.END, line + "\n")

        # Stop if it's raw or unknown
        if not entry or not isinstance(entry, dict) or all(k.startswith("_") for k in entry.keys()):
            return

        # Recurse into inputs
        output_count = entry.get("_output_count", 1)
        crafts_needed = ceil(remaining / output_count)
        inputs = entry.get("_inputs", entry)
        children = [k for k in inputs if not k.startswith("_")]

        for i, sub in enumerate(children):
            is_last = (i == len(children) - 1)
            recurse(sub, inputs[sub] * crafts_needed, ancestors_last + [is_last])

    recurse(name, quantity)
    output_text.config(state=tk.DISABLED)


view_tree_button_frame = tk.Frame(root)
view_tree_button_frame.grid(row=18, column=0, columnspan=2, pady=2)
tk.Button(view_tree_button_frame, text="Manage Inventory", command=lambda: open_inventory_editor(root)).grid(row=0, column=0, padx=5)
tk.Button(view_tree_button_frame, text="View Tree", command=view_component_tree).grid(row=0, column=1, padx=5)


# Function Definitions

def add_recipe():
    item = item_entry.get().strip()
    components_raw = components_entry.get().strip()
    output_count_raw = output_count_entry.get().strip()

    if not item:
        messagebox.showwarning("Input error", "Please fill all fields.")
        return

    try:
        components = {}
        for pair in components_raw.split(","):
            name, qty = pair.strip().split(":")
            components[name.strip()] = int(qty.strip())

        if recipe_type.get() == "multiblock":
            components["_type"] = "multiblock"

        if output_count_raw:
            components["_output_count"] = int(output_count_raw)
        
        selected = [tag for tag, var in new_recipe_tags.items() if var.get()]
        if "Any" not in selected:
            selected.append("Any")
        components["_tags"] = selected

        recipes[item] = components
        save_recipes(recipes)
        update_dropdowns()
        messagebox.showinfo("Success", f"Added/updated recipe for '{item}'!")
        item_entry.delete(0, tk.END)
        components_entry.delete(0, tk.END)
        output_count_entry.delete(0, tk.END)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse: {e}")

def view_selected_recipe(name):
    global last_viewed_recipe
    last_viewed_recipe = name

    output_text.config(state=tk.NORMAL)
    output_text.delete(1.0, tk.END)

    if name in recipes:
        formatted = format_recipe_view(name, recipes[name])
        output_text.insert(tk.END, formatted)
    else:
        output_text.insert(tk.END, f"No recipe found for '{name}'.")

    output_text.config(state=tk.DISABLED)

def delete_selected_recipe(name):
    if name not in recipes:
        messagebox.showerror("Error", f"'{name}' does not exist.")
        return

    confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the recipe '{name}'?")
    if confirm:
        del recipes[name]
        save_recipes(recipes)
        update_dropdowns()
        output_text.config(state=tk.NORMAL)
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"Deleted recipe: {name}")
        output_text.config(state=tk.DISABLED)

def view_raw_materials(name):
    global last_viewed_recipe
    last_viewed_recipe = name

    output_text.config(state=tk.NORMAL)
    output_text.delete(1.0, tk.END)

    if name in recipes:
        from inventory_gui import load_inventory  # type: ignore
        inventory = load_inventory()

        try:
            quantity = int(quantity_var_single.get() if name in singleblocks else quantity_var_multi.get())
        except ValueError:
            quantity = 1

        show_raw = show_raw_var_single.get() if name in singleblocks else show_raw_var_multi.get()

        if show_raw:
            # Raw material breakdown (deepest level only)
            raw_materials = calculate_raw_materials(name, quantity, recipes, inventory.copy())
            formatted = format_raw_materials_with_inventory(raw_materials, inventory)
            output_text.insert(tk.END, formatted)

            if all(max(0, raw_materials[k] - inventory.get(k, 0)) == 0 for k in raw_materials):
                output_text.insert(tk.END, "\n\n✔ All materials available!")

        else:
            # Inventory-aware full component breakdown (deduct top-down)
            original_inventory = inventory
            inventory = inventory.copy()  # this one gets mutated
            component_totals = {}

            def collect_components(item, qty_needed, is_root=False):
                nonlocal inventory
                entry = recipes.get(item)
                if isinstance(entry, list):
                    entry = entry[0]

                have = inventory.get(item, 0)
                remaining = max(0, qty_needed - have)
                inventory[item] = max(0, have - qty_needed)

                if not is_root:
                    component_totals[item] = component_totals.get(item, 0) + qty_needed

                if not entry or not isinstance(entry, dict) or all(k.startswith("_") for k in entry.keys()):
                    return

                output_count = entry.get("_output_count", 1)
                crafts_needed = ceil(remaining / output_count)
                inputs = entry.get("_inputs", entry)

                for sub, count in inputs.items():
                    if not sub.startswith("_"):
                        collect_components(sub, count * crafts_needed)

            collect_components(name, quantity, is_root=True)

            output_text.insert(tk.END, f"All Components Needed to Build {quantity}x {name}:\n\n")

            for comp, needed in sorted(component_totals.items()):
                have = original_inventory.get(comp, 0)
                missing = max(0, needed - have)
                status = f"(have {have}, need {missing})"
                checkmark = " ✔" if missing == 0 else ""
                output_text.insert(tk.END, f"- {comp}: {needed} {status}{checkmark}\n")
            
            if all(max(0, component_totals[k] - original_inventory.get(k, 0)) == 0 for k in component_totals):
                output_text.insert(tk.END, "\n\n✔ All materials available!")

    else:
        output_text.insert(tk.END, f"No recipe found for '{name}'.")

    output_text.config(state=tk.DISABLED)

def update_dropdowns():
    global multiblocks, singleblocks, single_grouped, multi_grouped
    multiblocks, singleblocks = split_recipe_types(recipes)
    single_grouped = group_by_tag(singleblocks)
    multi_grouped = group_by_tag(multiblocks)
    refresh_dropdowns()

def set_view_filter_tags(value):
    for var in selected_tags.values():
        var.set(value)
    refresh_dropdowns()


def edit_recipe(name):
    if name not in recipes:
        messagebox.showerror("Error", f"'{name}' does not exist.")
        return

    recipe = recipes[name]
    item_entry.delete(0, tk.END)
    item_entry.insert(0, name)

    components_entry.delete(0, tk.END)
    component_str = ", ".join(f"{k}:{v}" for k, v in recipe.items() if not k.startswith("_"))
    components_entry.insert(0, component_str)

    output_count_entry.delete(0, tk.END)
    if "_output_count" in recipe:
        output_count_entry.insert(0, str(recipe["_output_count"]))

    for tag, var in new_recipe_tags.items():
        var.set(tag in recipe.get("_tags", []))

    recipe_type.set("multiblock" if recipe.get("_type") == "multiblock" else "singleblock")

    messagebox.showinfo("Edit Mode", f"Now editing '{name}'. Click 'Add Recipe' to save changes.")


def filter_dropdown(event, dropdown, all_values, var):
    typed = var.get().lower().replace(" ", "_")
    filtered = [v for v in all_values if typed in v.lower().replace(" ", "_")]
    dropdown['values'] = filtered if filtered else all_values
    dropdown.filtered_values = filtered if filtered else all_values


def resolve_dropdown_selection(event, dropdown, var):
    value = dropdown.get()
    print(value)
    if hasattr(dropdown, "filtered_values"):
        for v in dropdown.filtered_values:
            if value.lower().replace(" ", "_") == v.lower().replace(" ", "_"):
                var.set(v)
                break


root.mainloop()