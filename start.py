import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk


def run_script(
    root: tk.Tk,
    progress_label: ttk.Label,
    progress: ttk.Progressbar,
    script_name: str,
) -> None:

    progress_label.config(text=f"{script_name} wird ausgeführt...")
    progress_label.pack(pady=(15, 5))
    progress.pack(pady=(0, 15))
    progress.start(10)

    def on_finish() -> None:
        progress.stop()
        progress_label.pack_forget()
        progress.pack_forget()

    def execute_script() -> None:
        script_path = os.path.join(os.path.dirname(__file__), script_name)
        if not os.path.exists(script_path):
            root.after(0, lambda: messagebox.showerror("Fehler", f"Skript nicht gefunden: {script_name}"))
            root.after(0, on_finish)
            return

        try:
            subprocess.run([sys.executable, script_path], check=True)
        except subprocess.CalledProcessError as exc:
            error_msg = (
                f"Beim Ausführen von {script_name} ist ein Fehler aufgetreten:\n{exc}"
            )
            root.after(0, lambda msg=error_msg: messagebox.showerror("Fehler", msg))
        finally:
            root.after(0, on_finish)

    threading.Thread(target=execute_script, daemon=True).start()
def main() -> None:
    root = tk.Tk()
    root.title("P2 - Datenqualitätsanalyse")
    root.resizable(False, False)

    frm = tk.Frame(root, padx=20, pady=20)
    frm.pack()

    progress_label = ttk.Label(frm)
    progress_bar = ttk.Progressbar(frm, mode="indeterminate", length=300)

    buttons = [
        ("Nach Besitz splitten", "datensaetze_nach_besitz.py"),
        ("Nach Quelle splitten", "datensaetze_nach_quelle.py"),
        ("Metadatenelemente auflisten", "show_elements.py"),
        ("Metadatenelemente (Menge) analysieren", "show_elements_quantity.py"),
        ("Primärschlüssel prüfen", "check_primary_key_unique.py"),
        ("ISBN prüfen", "check_isbn.py"),
        ("Leader prüfen", "check_leader_element.py"),
        ("Datum prüfen", "check_008_datum.py"),
    ]

    for label, script in buttons:
        ttk.Button(
            frm,
            text=label,
            width=30,
            command=lambda s=script: run_script(root, progress_label, progress_bar, s),
        ).pack(pady=5)

    ttk.Button(
        frm,
        text="Beenden",
        width=30,
        command=root.destroy,
    ).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main()