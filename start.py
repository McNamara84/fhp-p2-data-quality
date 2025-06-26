import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox


def run_script(script_name: str) -> None:
    """Run a Python script located in the same directory as this file."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        messagebox.showerror("Fehler", f"Skript nicht gefunden: {script_name}")
        return

    try:
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as exc:
        messagebox.showerror(
            "Fehler", f"Beim Ausführen von {script_name} ist ein Fehler aufgetreten:\n{exc}"
        )


def main() -> None:
    root = tk.Tk()
    root.title("FHP Daten-Qualität Skripte")
    root.resizable(False, False)

    frm = tk.Frame(root, padx=20, pady=20)
    frm.pack()

    tk.Button(
        frm,
        text="Nach Besitz splitten",
        width=30,
        command=lambda: run_script("datensaetze_nach_besitz.py"),
    ).pack(pady=5)

    tk.Button(
        frm,
        text="Nach Quelle splitten",
        width=30,
        command=lambda: run_script("datensaetze_nach_quelle.py"),
    ).pack(pady=5)

    tk.Button(
        frm,
        text="Metadatenelemente auflisten",
        width=30,
        command=lambda: run_script("show_elements.py"),
    ).pack(pady=5)

    tk.Button(
        frm,
        text="Metadatenelemente (Menge) analysieren",
        width=30,
        command=lambda: run_script("show_elements_quantity.py"),
    ).pack(pady=5)

    tk.Button(
        frm,
        text="Beenden",
        width=30,
        command=root.destroy,
    ).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main()