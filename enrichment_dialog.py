"""
GUI-Dialog für die Metadaten-Anreicherung mit Echtzeit-Statistiken.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import time
from dataclasses import dataclass


@dataclass
class EnrichmentStats:
    """Statistiken für den Enrichment-Prozess."""
    total_records: int = 0
    processed_records: int = 0
    successful_enrichments: int = 0
    failed_enrichments: int = 0
    rate_limit_retries: int = 0
    isbn_not_found: int = 0
    conflicts_skipped: int = 0
    start_time: float = 0.0
    
    def get_success_rate(self) -> float:
        """Berechnet die Erfolgsrate in Prozent."""
        if self.processed_records == 0:
            return 0.0
        return (self.successful_enrichments / self.processed_records) * 100
    
    def get_elapsed_time(self) -> float:
        """Berechnet die verstrichene Zeit in Sekunden."""
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time
    
    def get_estimated_remaining_time(self) -> float:
        """Schätzt die verbleibende Zeit basierend auf dem bisherigen Fortschritt."""
        elapsed = self.get_elapsed_time()
        if self.processed_records == 0 or elapsed == 0:
            return 0.0
        
        records_per_second = self.processed_records / elapsed
        remaining_records = self.total_records - self.processed_records
        
        if records_per_second == 0:
            return 0.0
        
        return remaining_records / records_per_second


class EnrichmentProgressDialog:
    """Dialog-Fenster für die Anzeige des Enrichment-Fortschritts."""
    
    def __init__(self, parent: tk.Tk, total_records: int, on_cancel: Optional[Callable] = None):
        """
        Initialisiert den Progress-Dialog.
        
        Args:
            parent: Eltern-Fenster
            total_records: Gesamtanzahl der zu verarbeitenden Records
            on_cancel: Callback-Funktion beim Abbruch
        """
        self.parent = parent
        self.on_cancel = on_cancel
        self.cancelled = False
        
        # Statistiken initialisieren
        self.stats = EnrichmentStats(
            total_records=total_records,
            start_time=time.time()
        )
        
        # Dialog-Fenster erstellen
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Metadaten werden angereichert...")
        self.dialog.geometry("600x450")
        self.dialog.resizable(False, False)
        
        # Dialog modal machen
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Beim Schließen des Fensters Abbruch auslösen
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Erstellt alle GUI-Widgets."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titel
        title_label = ttk.Label(
            main_frame,
            text="📚 Metadaten-Anreicherung",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Progress Bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            length=560
        )
        self.progress_bar.pack()
        
        self.progress_label = ttk.Label(
            progress_frame,
            text="0 / 0 Records (0.0%)",
            font=("Segoe UI", 10)
        )
        self.progress_label.pack(pady=(5, 0))
        
        # Statistiken-Frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistiken", padding="10")
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Grid für Statistiken
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.BOTH, expand=True)
        
        # Linke Spalte
        left_frame = ttk.Frame(stats_grid)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.success_label = self._create_stat_row(left_frame, "✅ Erfolgreiche Anreicherungen:", "0")
        self.error_label = self._create_stat_row(left_frame, "❌ Fehler:", "0")
        self.retry_label = self._create_stat_row(left_frame, "⏳ Rate-Limit Retries:", "0")
        
        # Rechte Spalte
        right_frame = ttk.Frame(stats_grid)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self.not_found_label = self._create_stat_row(right_frame, "🔍 ISBN nicht gefunden:", "0")
        self.conflict_label = self._create_stat_row(right_frame, "⚠️ Konflikte übersprungen:", "0")
        self.rate_label = self._create_stat_row(right_frame, "📊 Erfolgsrate:", "0.0%")
        
        # Zeit-Informationen
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.time_label = ttk.Label(
            time_frame,
            text="Verstrichene Zeit: 00:00:00 | Geschätzte Restzeit: --:--:--",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.time_label.pack()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self._on_cancel_clicked,
            state="normal"
        )
        self.cancel_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.close_button = ttk.Button(
            button_frame,
            text="Schließen",
            command=self._on_close_clicked,
            state="disabled"
        )
        self.close_button.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        
    def _create_stat_row(self, parent: ttk.Frame, label: str, value: str) -> ttk.Label:
        """Erstellt eine Zeile mit Label und Wert und gibt das Value-Label zurück."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=3)
        
        label_widget = ttk.Label(row_frame, text=label, font=("Segoe UI", 9))
        label_widget.pack(side=tk.LEFT)
        
        value_widget = ttk.Label(row_frame, text=value, font=("Segoe UI", 9, "bold"))
        value_widget.pack(side=tk.RIGHT)
        
        return value_widget
    
    def _format_time(self, seconds: float) -> str:
        """Formatiert Sekunden zu HH:MM:SS."""
        if seconds < 0:
            return "--:--:--"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def update_progress(self, processed: int, successful: int, failed: int, 
                       rate_limit_retries: int, isbn_not_found: int, conflicts_skipped: int):
        """
        Aktualisiert den Fortschritt und die Statistiken.
        
        Args:
            processed: Anzahl verarbeiteter Records
            successful: Anzahl erfolgreicher Anreicherungen
            failed: Anzahl fehlgeschlagener Anreicherungen
            rate_limit_retries: Anzahl Rate-Limit Retries
            isbn_not_found: Anzahl nicht gefundener ISBNs
            conflicts_skipped: Anzahl übersprungener Konflikte
        """
        # Prüfen, ob Dialog noch existiert
        try:
            if not self.dialog.winfo_exists():
                return
        except (tk.TclError, AttributeError):
            return
        
        # Statistiken aktualisieren
        self.stats.processed_records = processed
        self.stats.successful_enrichments = successful
        self.stats.failed_enrichments = failed
        self.stats.rate_limit_retries = rate_limit_retries
        self.stats.isbn_not_found = isbn_not_found
        self.stats.conflicts_skipped = conflicts_skipped
        
        # Progress Bar aktualisieren
        if self.stats.total_records > 0:
            progress_percentage = (processed / self.stats.total_records) * 100
            self.progress_bar["value"] = progress_percentage
            
            self.progress_label.config(
                text=f"{processed} / {self.stats.total_records} Records ({progress_percentage:.1f}%)"
            )
        
        # Statistik-Labels aktualisieren
        if self.success_label and self.success_label.winfo_exists():
            self.success_label.config(text=str(successful))
        if self.error_label and self.error_label.winfo_exists():
            self.error_label.config(text=str(failed))
        if self.retry_label and self.retry_label.winfo_exists():
            self.retry_label.config(text=str(rate_limit_retries))
        if self.not_found_label and self.not_found_label.winfo_exists():
            self.not_found_label.config(text=str(isbn_not_found))
        if self.conflict_label and self.conflict_label.winfo_exists():
            self.conflict_label.config(text=str(conflicts_skipped))
        if self.rate_label and self.rate_label.winfo_exists():
            self.rate_label.config(text=f"{self.stats.get_success_rate():.1f}%")
        
        # Zeit-Informationen aktualisieren
        elapsed = self.stats.get_elapsed_time()
        remaining = self.stats.get_estimated_remaining_time()
        
        if self.time_label and self.time_label.winfo_exists():
            self.time_label.config(
                text=f"Verstrichene Zeit: {self._format_time(elapsed)} | "
                     f"Geschätzte Restzeit: {self._format_time(remaining)}"
            )
        
        # GUI aktualisieren
        try:
            self.dialog.update_idletasks()
        except (tk.TclError, AttributeError):
            pass
    
    def mark_complete(self, success: bool = True, message: str = ""):
        """
        Markiert den Prozess als abgeschlossen.
        
        Args:
            success: Ob der Prozess erfolgreich war
            message: Optional eine Nachricht anzuzeigen
        """
        try:
            if not self.dialog.winfo_exists():
                return
            
            self.cancel_button.config(state="disabled")
            self.close_button.config(state="normal")
            
            if success:
                self.dialog.title("✅ Anreicherung abgeschlossen")
                if message:
                    messagebox.showinfo("Erfolg", message, parent=self.dialog)
            else:
                self.dialog.title("❌ Anreicherung abgebrochen")
                if message:
                    messagebox.showwarning("Abgebrochen", message, parent=self.dialog)
        except (tk.TclError, AttributeError):
            pass
    
    def _on_cancel_clicked(self):
        """Wird aufgerufen, wenn der Abbrechen-Button geklickt wird."""
        try:
            if not self.dialog.winfo_exists():
                return
            
            if messagebox.askyesno(
                "Abbrechen",
                "Möchten Sie die Anreicherung wirklich abbrechen?\n\n"
                "Bereits verarbeitete Datensätze bleiben erhalten.",
                parent=self.dialog
            ):
                self.cancelled = True
                self.cancel_button.config(state="disabled", text="Wird abgebrochen...")
                
                if self.on_cancel:
                    self.on_cancel()
        except (tk.TclError, AttributeError):
            pass
    
    def _on_close_clicked(self):
        """Wird aufgerufen, wenn der Schließen-Button geklickt wird."""
        self.dialog.destroy()
    
    def _on_window_close(self):
        """Wird aufgerufen, wenn das Fenster geschlossen werden soll."""
        try:
            if not self.dialog.winfo_exists():
                return
            
            if self.close_button["state"] == "normal":
                self.dialog.destroy()
            else:
                self._on_cancel_clicked()
        except (tk.TclError, AttributeError):
            pass
    
    def is_cancelled(self) -> bool:
        """Gibt zurück, ob der Prozess abgebrochen wurde."""
        return self.cancelled
