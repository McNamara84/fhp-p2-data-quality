import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from enrichment_dialog import EnrichmentProgressDialog
from statistics_dialog import show_statistics


def run_enrichment(root: tk.Tk) -> None:
    """Startet die Metadaten-Anreicherung mit GUI-Dialog."""
    
    # Datei-Auswahl
    xml_path = filedialog.askopenfilename(
        parent=root,
        title="XML-Datei für Anreicherung auswählen",
        filetypes=[("XML-Dateien", "*.xml"), ("Alle Dateien", "*.*")],
        initialdir=os.path.dirname(__file__)
    )
    
    if not xml_path:
        return
    
    # Prüfen, ob Datei existiert
    if not os.path.exists(xml_path):
        messagebox.showerror("Fehler", f"Datei nicht gefunden: {xml_path}", parent=root)
        return
    
    # Anzahl Records ermitteln
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root_elem = tree.getroot()
        
        # ISBNs zählen
        isbn_count = 0
        for record in root_elem.findall("record"):
            for datafield in record.findall("datafield"):
                if datafield.get("tag") == "020":
                    for subfield in datafield.findall("subfield"):
                        if subfield.get("code") == "a" and subfield.text and subfield.text.strip():
                            isbn_count += 1
                            break  # Nur eine ISBN pro Record
                    if isbn_count > 0:
                        break
        
        if isbn_count == 0:
            messagebox.showwarning(
                "Keine ISBNs gefunden",
                "Die ausgewählte Datei enthält keine ISBNs (Feld 020$a).",
                parent=root
            )
            return
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Analysieren der Datei:\n{e}", parent=root)
        return
    
    # Progress-Dialog erstellen
    cancelled = False
    
    def check_cancelled():
        return cancelled
    
    def on_cancel():
        nonlocal cancelled
        cancelled = True
    
    progress_dialog = EnrichmentProgressDialog(root, isbn_count, on_cancel=on_cancel)
    
    def run_enrichment_thread():
        result = None
        try:
            # Importiere enrich_metadata lokal, um Circular Import zu vermeiden
            import enrich_metadata
            
            # Callback für Progress-Updates
            def progress_callback(processed, successful, failed, retry_1, retry_2, retry_3, isbn_not_found, conflicts_skipped):
                if not cancelled:  # Nur Updates senden, wenn nicht abgebrochen
                    try:
                        root.after(0, lambda p=processed, s=successful, f=failed, r1=retry_1, r2=retry_2, r3=retry_3, i=isbn_not_found, c=conflicts_skipped: 
                            progress_dialog.update_progress(p, s, f, r1, r2, r3, i, c))
                    except (tk.TclError, AttributeError):
                        pass
            
            # Enrichment durchführen
            result = enrich_metadata.main(xml_path, progress_callback=progress_callback, check_cancelled=check_cancelled)
            
            if result:
                if result.get('cancelled'):
                    def show_cancel():
                        try:
                            progress_dialog.mark_complete(
                                success=False,
                                message="Die Anreicherung wurde abgebrochen."
                            )
                        except (tk.TclError, AttributeError):
                            pass
                    root.after(0, show_cancel)
                else:
                    # Erfolgreich - Datei speichern
                    output_path = xml_path.replace(".xml", "_enriched.xml")
                    if result.get('tree'):
                        result['tree'].write(output_path, encoding='utf-8', xml_declaration=True)
                    
                    # JSON-Statistiken exportieren
                    json_path = None
                    try:
                        json_path = enrich_metadata.export_stats_to_json(result, xml_path, output_path)
                    except Exception as e:
                        print(f"Warnung: JSON-Export fehlgeschlagen: {e}")
                    
                    def show_success():
                        try:
                            # Progress-Dialog schließen
                            progress_dialog.dialog.destroy()
                            
                            # Statistik-Dialog anzeigen
                            show_statistics(root, result)
                            
                            # Abschließende Bestätigung mit JSON-Info
                            success_msg = f"Angereicherte Datei gespeichert:\n{output_path}"
                            if json_path:
                                success_msg += f"\n\nStatistiken exportiert:\n{json_path}"
                            
                            messagebox.showinfo(
                                "Erfolg",
                                success_msg,
                                parent=root
                            )
                        except (tk.TclError, AttributeError) as e:
                            print(f"Fehler beim Anzeigen der Statistiken: {e}")
                    root.after(0, show_success)
            else:
                def show_error():
                    try:
                        progress_dialog.mark_complete(
                            success=False,
                            message="Ein Fehler ist aufgetreten. Bitte prüfen Sie die Log-Datei."
                        )
                    except (tk.TclError, AttributeError):
                        pass
                root.after(0, show_error)
        except Exception as e:
            error_msg = f"Fehler bei der Anreicherung:\n{str(e)}"
            def show_exception():
                try:
                    if progress_dialog.dialog.winfo_exists():
                        messagebox.showerror("Fehler", error_msg, parent=progress_dialog.dialog)
                    progress_dialog.mark_complete(success=False, message=error_msg)
                except (tk.TclError, AttributeError):
                    pass
            root.after(0, show_exception)
    
    # Thread starten
    thread = threading.Thread(target=run_enrichment_thread, daemon=True)
    thread.start()


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
        ("Doppelte ISBN/ISSN prüfen", "check_duplicate_identifiers.py"),
    ]

    for label, script in buttons:
        ttk.Button(
            frm,
            text=label,
            width=30,
            command=lambda s=script: run_script(root, progress_label, progress_bar, s),
        ).pack(pady=5)
    
    # Spezial-Button für Metadaten-Anreicherung mit eigenem Dialog
    ttk.Button(
        frm,
        text="Metadaten anreichern",
        width=30,
        command=lambda: run_enrichment(root),
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
