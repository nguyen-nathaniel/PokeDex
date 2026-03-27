import webbrowser
import requests
import tkinter as tk
from tkinter import messagebox


BULBAPEDIA = "https://bulbapedia.bulbagarden.net/wiki/"
SMOGON = "https://www.smogon.com/dex/sv/pokemon/"
POKEMON_TAG = "_(Pok%C3%A9mon)"
MAX_SUGGESTIONS = 12

all_pokemon_names = []

def check_pokemon_data(pokemon_name):
    try:
        response = requests.get(
            f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}",
            timeout=8
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def open_pokemon_pages(pokemon_name):
    pokemon_name = pokemon_name.lower().replace(" ", "-")

    if check_pokemon_data(pokemon_name):
        webbrowser.open(BULBAPEDIA + pokemon_name + POKEMON_TAG)
        webbrowser.open(SMOGON + pokemon_name)
        return True
    else:
        return False


def fetch_all_pokemon_names():
    try:
        response = requests.get(
            "https://pokeapi.co/api/v2/pokemon?limit=2000",
            timeout=12
        )
        if response.status_code != 200:
            return []

        data = response.json()
        return [item["name"] for item in data.get("results", [])]
    except requests.RequestException:
        return []


def hide_suggestions():
    suggestion_listbox.pack_forget()


def update_suggestions(_event=None):
    typed_text = name_entry.get().strip().lower().replace(" ", "-")
    suggestion_listbox.delete(0, tk.END)

    if not typed_text or not all_pokemon_names:
        hide_suggestions()
        return

    matches = [
        name for name in all_pokemon_names
        if name.startswith(typed_text)
    ][:MAX_SUGGESTIONS]

    if not matches:
        hide_suggestions()
        return

    for name in matches:
        suggestion_listbox.insert(tk.END, name)

    suggestion_listbox.pack(pady=(0, 10))


def choose_selected_suggestion(_event=None):
    selection = suggestion_listbox.curselection()
    if not selection:
        return

    selected_name = suggestion_listbox.get(selection[0])
    name_entry.delete(0, tk.END)
    name_entry.insert(0, selected_name)
    hide_suggestions()
    name_entry.focus_set()
    name_entry.icursor(tk.END)


def move_focus_to_suggestions(_event):
    if suggestion_listbox.size() > 0:
        suggestion_listbox.focus_set()
        suggestion_listbox.selection_clear(0, tk.END)
        suggestion_listbox.selection_set(0)
        suggestion_listbox.activate(0)
    return "break"


def on_search():
    pokemon_name = name_entry.get().strip()
    if not pokemon_name:
        status_var.set("Please enter a Pokemon name.")
        return

    hide_suggestions()

    if open_pokemon_pages(pokemon_name):
        status_var.set(f"Opened Bulbapedia and Smogon for '{pokemon_name}'.")
    else:
        status_var.set(f"Pokemon '{pokemon_name}' was not found.")


def on_help():
    messagebox.showinfo(
        "Help",
        "Type a Pokemon name, then click Search.\n"
        "This opens the Pokemon pages on Bulbapedia and Smogon."
    )


def main():
    global name_entry
    global status_var
    global suggestion_listbox
    global all_pokemon_names

    root = tk.Tk()
    root.title("PokeDex")
    root.geometry("420x320")
    root.resizable(True, True)

    tk.Label(root, text="Enter Pokemon name:").pack(pady=(15, 5))

    name_entry = tk.Entry(root, width=35)
    name_entry.pack(pady=(0, 10))
    name_entry.focus_set()
    name_entry.bind("<KeyRelease>", update_suggestions)
    name_entry.bind("<Down>", move_focus_to_suggestions)

    suggestion_listbox = tk.Listbox(root, width=35, height=8)
    suggestion_listbox.bind("<<ListboxSelect>>", choose_selected_suggestion)
    suggestion_listbox.bind("<Double-Button-1>", choose_selected_suggestion)
    suggestion_listbox.bind("<Return>", choose_selected_suggestion)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    tk.Button(button_frame, text="Search", width=10, command=on_search).pack(
        side=tk.LEFT, padx=5
    )
    tk.Button(button_frame, text="Help", width=10, command=on_help).pack(
        side=tk.LEFT, padx=5
    )
    tk.Button(button_frame, text="Quit", width=10, command=root.destroy).pack(
        side=tk.LEFT, padx=5
    )

    all_pokemon_names = fetch_all_pokemon_names()
    if all_pokemon_names:
        status_var = tk.StringVar(value="Ready.")
    else:
        status_var = tk.StringVar(
            value="Ready, but suggestions are unavailable (network issue)."
        )
    tk.Label(root, textvariable=status_var, fg="blue").pack(pady=(12, 0))

    root.bind("<Return>", lambda _event: on_search())
    root.mainloop()

main()