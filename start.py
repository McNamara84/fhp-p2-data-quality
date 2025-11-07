import os
import sys
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from metadata_enrichment.enrichment_dialog import EnrichmentProgressDialog
from metadata_enrichment.statistics_dialog import show_statistics


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
    
    # Anzahl ISBNs ermitteln (nur für kleine Dateien, sonst schätzen)
    isbn_count = None  # None = unbekannt (wird während Pass 1 ermittelt)
    
    try:
        file_size_mb = os.path.getsize(xml_path) / (1024 * 1024)
        
        # Nur für kleine Dateien (<100MB) vorab zählen
        if file_size_mb < 100:
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
                                break  # Nur erste ISBN pro Record
                        break  # Nur erstes datafield 020
            
            if isbn_count == 0:
                messagebox.showwarning(
                    "Keine ISBNs gefunden",
                    "Die ausgewählte Datei enthält keine ISBNs (Feld 020$a).",
                    parent=root
                )
                return
        else:
            # Für große Dateien: Unbekannte Anzahl (wird in Pass 1 ermittelt)
            print(f"Große Datei ({file_size_mb:.0f} MB) - ISBN-Anzahl wird während Verarbeitung ermittelt")
            isbn_count = None
            
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
            def progress_callback(processed, successful, failed, retry_1, retry_2, retry_3, isbn_not_found, conflicts_skipped, total=None):
                if not cancelled:  # Nur Updates senden, wenn nicht abgebrochen
                    try:
                        root.after(0, lambda p=processed, s=successful, f=failed, r1=retry_1, r2=retry_2, r3=retry_3, i=isbn_not_found, c=conflicts_skipped, t=total: 
                            progress_dialog.update_progress(p, s, f, r1, r2, r3, i, c, total=t))
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
                    # Erfolgreich
                    output_path = xml_path.replace(".xml", "_enriched.xml")
                    
                    # Datei speichern (je nach return-Format)
                    if result.get('output_path'):
                        # Iteratives Parsing: Datei wurde bereits geschrieben
                        output_path = result.get('output_path')
                    elif result.get('tree'):
                        # Altes Format: Tree zurückgegeben (Backward-Kompatibilität)
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


def show_enrichment_statistics(root: tk.Tk) -> None:
    """Startet einen Webserver und öffnet die Anreicherungsstatistik im Browser."""
    
    # Prüfe ob Statistik-Dateien existieren
    stats_file = os.path.join(os.path.dirname(__file__), "voebvoll-20241027_enriched_stats.json")
    
    if not os.path.exists(stats_file):
        messagebox.showerror(
            "Fehler",
            "Statistik-Datei nicht gefunden.\nBitte führen Sie zuerst die Metadaten-Anreicherung durch.",
            parent=root
        )
        return
    
    # Erstelle Output-Verzeichnis für Diagramme
    output_dir = os.path.join(os.path.dirname(__file__), "enrichment_charts")
    os.makedirs(output_dir, exist_ok=True)
    
    # R-Script Pfad
    r_script = os.path.join(os.path.dirname(__file__), "generate_enrichment_charts.R")
    
    # Prüfe ob R installiert ist und finde Rscript.exe
    rscript_paths = [
        "Rscript",  # Im PATH
        r"C:\Program Files\R\R-4.5.1\bin\Rscript.exe",  # Standard Windows Installation
        r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe",
        r"C:\Program Files\R\R-4.3.1\bin\Rscript.exe",
    ]
    
    rscript_cmd = None
    for path in rscript_paths:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                rscript_cmd = path
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not rscript_cmd:
        messagebox.showerror(
            "R nicht gefunden",
            "R ist nicht installiert oder nicht im PATH.\n\n"
            "Bitte installieren Sie R 4.5.1 oder höher:\n"
            "https://cran.r-project.org/",
            parent=root
        )
        return
    
    # Generiere Diagramme im Hintergrund
    def generate_charts():
        try:
            # Führe R-Script aus
            result = subprocess.run(
                [rscript_cmd, r_script, stats_file, output_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                error_msg = f"R-Script Fehler:\n{result.stderr}"
                root.after(0, lambda: messagebox.showerror("Fehler", error_msg, parent=root))
                return False
            
            print(result.stdout)  # R-Script Ausgabe
            return True
            
        except subprocess.TimeoutExpired:
            root.after(0, lambda: messagebox.showerror(
                "Fehler",
                "R-Script Timeout: Diagramm-Generierung dauert zu lange.",
                parent=root
            ))
            return False
        except Exception as e:
            error_msg = f"Fehler beim Generieren der Diagramme:\n{e}"
            root.after(0, lambda msg=error_msg: messagebox.showerror(
                "Fehler",
                msg,
                parent=root
            ))
            return False
    
    # Status-Dialog
    status_dialog = tk.Toplevel(root)
    status_dialog.title("Generiere Diagramme...")
    status_dialog.geometry("400x150")
    status_dialog.transient(root)
    status_dialog.grab_set()
    
    status_label = ttk.Label(
        status_dialog,
        text="Generiere Diagramme mit R...\nBitte warten...",
        font=('Arial', 11)
    )
    status_label.pack(pady=30)
    
    status_progress = ttk.Progressbar(status_dialog, mode="indeterminate", length=300)
    status_progress.pack(pady=10)
    status_progress.start(10)
    
    # Diagramme in separatem Thread generieren
    def run_chart_generation():
        success = generate_charts()
        
        # Schließe Status-Dialog
        root.after(0, status_dialog.destroy)
        
        if not success:
            return
        
        # Starte Webserver
        try:
            from enrichment_stats_server import start_stats_server
        except ImportError:
            root.after(0, lambda: messagebox.showerror(
                "Fehler",
                "Webserver-Modul nicht gefunden.\nBitte prüfen Sie die Installation.",
                parent=root
            ))
            return
        
        # Starte Webserver in separatem Thread
        try:
            port = 8080
            server_thread = threading.Thread(
                target=start_stats_server,
                args=(stats_file, output_dir, port),
                daemon=True
            )
            server_thread.start()
            
            # Öffne Browser nach kurzer Verzögerung
            def open_browser():
                import time
                time.sleep(0.5)  # Warte bis Server bereit ist
                webbrowser.open(f"http://localhost:{port}")
            
            browser_thread = threading.Thread(target=open_browser, daemon=True)
            browser_thread.start()
            
            root.after(0, lambda: messagebox.showinfo(
                "Webserver gestartet",
                f"Die Anreicherungsstatistik wurde im Browser geöffnet.\n\n"
                f"URL: http://localhost:{port}\n\n"
                f"Der Webserver läuft im Hintergrund und wird beim Beenden der Anwendung automatisch geschlossen.",
                parent=root
            ))
            
        except Exception as e:
            error_msg = f"Fehler beim Starten des Webservers:\n{e}"
            root.after(0, lambda msg=error_msg: messagebox.showerror(
                "Fehler",
                msg,
                parent=root
            ))
    
    chart_thread = threading.Thread(target=run_chart_generation, daemon=True)
    chart_thread.start()


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
        ("Nach Besitz splitten", "data_processing/split_by_possession.py"),
        ("Nach Quelle splitten", "data_processing/split_by_source.py"),
        ("Metadatenelemente auflisten", "data_analysis/analyze_elements_list.py"),
        ("Metadatenelemente (Menge) analysieren", "data_analysis/analyze_elements_quantity.py"),
        ("Primärschlüssel prüfen", "data_quality/check_primary_key.py"),
        ("ISBN prüfen", "data_quality/check_isbn.py"),
        ("Leader prüfen", "data_quality/check_leader.py"),
        ("Datum prüfen", "data_quality/check_date_field.py"),
        ("Doppelte ISBN/ISSN prüfen", "data_quality/check_duplicate_identifiers.py"),
        ("ISIL-Codes validieren", "data_quality/validate_isil_codes.py"),
        ("Besitznachweise zählen", "data_analysis/analyze_possession_counts.py"),
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
    
    # Button "Anreicherungsstatistik" nur anzeigen, wenn angereicherte Dateien existieren
    enriched_xml = os.path.join(os.path.dirname(__file__), "voebvoll-20241027_enriched.xml")
    enriched_stats = os.path.join(os.path.dirname(__file__), "voebvoll-20241027_enriched_stats.json")
    
    if os.path.exists(enriched_xml) and os.path.exists(enriched_stats):
        ttk.Button(
            frm,
            text="Anreicherungsstatistik",
            width=30,
            command=lambda: show_enrichment_statistics(root),
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
