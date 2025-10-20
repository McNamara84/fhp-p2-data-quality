"""
Statistik-Dialog für detaillierte Vorher-Nachher-Analyse der Metadaten-Anreicherung.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any


class StatisticsDialog:
    """Dialog-Fenster für detaillierte Anreicherungs-Statistiken mit Vorher-Nachher-Vergleich."""
    
    def __init__(self, parent: tk.Tk, stats: Dict[str, Any]):
        """
        Initialisiert den Statistik-Dialog.
        
        Args:
            parent: Eltern-Fenster
            stats: Dictionary mit allen Statistiken inkl. field_stats
        """
        self.parent = parent
        self.stats = stats
        self.field_stats = stats.get('field_stats', {})
        
        # Dialog-Fenster erstellen
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("📊 Detaillierte Anreicherungs-Statistiken")
        self.dialog.geometry("900x700")
        self.dialog.resizable(True, True)
        
        # Dialog modal machen
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Erstellt alle GUI-Widgets."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titel
        title_label = ttk.Label(
            main_frame,
            text="📊 Anreicherungs-Statistiken",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Scrollbare Canvas für alle Inhalte
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg="white")
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Gesamt-Übersicht
        self._create_overview_section(scrollable_frame)
        
        # Field-by-Field Statistiken
        self._create_field_statistics(scrollable_frame)
        
        # Schließen-Button
        close_button = ttk.Button(
            main_frame,
            text="Schließen",
            command=self.dialog.destroy,
            width=20
        )
        close_button.pack(pady=(10, 0))
        
    def _create_overview_section(self, parent: ttk.Frame):
        """Erstellt die Gesamt-Übersicht-Sektion."""
        overview_frame = ttk.LabelFrame(parent, text="Gesamt-Übersicht", padding="15")
        overview_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        stats_grid = ttk.Frame(overview_frame)
        stats_grid.pack(fill=tk.X)
        
        # Linke Spalte
        left_col = ttk.Frame(stats_grid)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        self._add_stat_row(left_col, "Verarbeitete Records:", str(self.stats.get('processed_records', 0)))
        self._add_stat_row(left_col, "Erfolgreiche Anreicherungen:", str(self.stats.get('successful_enrichments', 0)))
        self._add_stat_row(left_col, "Fehler:", str(self.stats.get('failed_enrichments', 0)))
        
        # Rechte Spalte
        right_col = ttk.Frame(stats_grid)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))
        
        self._add_stat_row(right_col, "ISBN nicht gefunden:", str(self.stats.get('isbn_not_found', 0)))
        self._add_stat_row(right_col, "Konflikte übersprungen:", str(self.stats.get('conflicts_skipped', 0)))
        
        # Erfolgsrate prominent anzeigen
        processed = self.stats.get('processed_records', 0)
        successful = self.stats.get('successful_enrichments', 0)
        success_rate = (successful / processed * 100) if processed > 0 else 0
        
        success_frame = ttk.Frame(overview_frame)
        success_frame.pack(fill=tk.X, pady=(15, 0))
        
        success_label = ttk.Label(
            success_frame,
            text=f"Erfolgsrate: {success_rate:.1f}%",
            font=("Segoe UI", 14, "bold"),
            foreground="green" if success_rate >= 70 else "orange" if success_rate >= 40 else "red"
        )
        success_label.pack()
        
    def _create_field_statistics(self, parent: ttk.Frame):
        """Erstellt die detaillierten Feld-Statistiken mit Vorher-Nachher-Vergleich."""
        fields_frame = ttk.LabelFrame(parent, text="Detaillierte Feld-Statistiken", padding="15")
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Für jedes Feld eine Karte erstellen
        field_display_names = {
            'Title': '📖 Titel (245$a)',
            'Authors': '👤 Autoren (100$a)',
            'Publisher': '🏢 Verlag (260$b)',
            'Year': '📅 Jahr (260$c)'
        }
        
        for field_key, display_name in field_display_names.items():
            if field_key in self.field_stats:
                self._create_field_card(fields_frame, field_key, display_name, self.field_stats[field_key])
    
    def _create_field_card(self, parent: ttk.Frame, field_key: str, display_name: str, field_data: Dict[str, int]):
        """Erstellt eine Karte für ein einzelnes Feld mit Vorher-Nachher-Visualisierung."""
        card_frame = ttk.LabelFrame(parent, text=display_name, padding="10")
        card_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Obere Zeile: Gesamt-Änderungen
        total_changes = (
            field_data.get('filled_after', 0) +
            field_data.get('abbreviation_replaced', 0) +
            field_data.get('corrected', 0)
        )
        
        summary_label = ttk.Label(
            card_frame,
            text=f"Gesamt-Änderungen: {total_changes}",
            font=("Segoe UI", 11, "bold")
        )
        summary_label.pack(anchor="w", pady=(0, 10))
        
        # Grid für die einzelnen Metriken
        metrics_frame = ttk.Frame(card_frame)
        metrics_frame.pack(fill=tk.X)
        
        # Spalten-Header
        header_frame = ttk.Frame(metrics_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="Änderungs-Typ", font=("Segoe UI", 9, "bold"), width=25).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Anzahl", font=("Segoe UI", 9, "bold"), width=10).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Visualisierung", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Einzelne Metriken
        self._add_metric_row(metrics_frame, "✅ Leere Felder befüllt", field_data.get('filled_after', 0), total_changes, "green")
        self._add_metric_row(metrics_frame, "📝 Abkürzungen ersetzt", field_data.get('abbreviation_replaced', 0), total_changes, "blue")
        self._add_metric_row(metrics_frame, "🔧 Fehler korrigiert", field_data.get('corrected', 0), total_changes, "orange")
        self._add_metric_row(metrics_frame, "⚠️ Konflikte", field_data.get('conflicts', 0), total_changes, "red")
        
    def _add_metric_row(self, parent: ttk.Frame, label: str, value: int, total: int, color: str):
        """Fügt eine Metrik-Zeile mit Balkendiagramm hinzu."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=3)
        
        # Label
        label_widget = ttk.Label(row_frame, text=label, width=25)
        label_widget.pack(side=tk.LEFT)
        
        # Wert
        value_label = ttk.Label(row_frame, text=str(value), width=10, font=("Segoe UI", 9, "bold"))
        value_label.pack(side=tk.LEFT)
        
        # Balken-Container
        bar_container = tk.Frame(row_frame, height=20, bg="lightgray", relief=tk.SUNKEN)
        bar_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Balken (proportional)
        if total > 0:
            bar_width = (value / total) if total > 0 else 0
            bar = tk.Frame(bar_container, bg=color, height=20)
            bar.place(x=0, y=0, relwidth=bar_width, relheight=1.0)
            
            # Prozent-Label im Balken (wenn Platz ist)
            if bar_width > 0.1:
                percent = (value / total * 100) if total > 0 else 0
                percent_label = tk.Label(
                    bar,
                    text=f"{percent:.1f}%",
                    bg=color,
                    fg="white",
                    font=("Segoe UI", 8, "bold")
                )
                percent_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def _add_stat_row(self, parent: ttk.Frame, label: str, value: str):
        """Fügt eine einfache Statistik-Zeile hinzu."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=3)
        
        label_widget = ttk.Label(row_frame, text=label, font=("Segoe UI", 10))
        label_widget.pack(side=tk.LEFT)
        
        value_widget = ttk.Label(row_frame, text=value, font=("Segoe UI", 10, "bold"))
        value_widget.pack(side=tk.RIGHT)


def show_statistics(parent: tk.Tk, stats: Dict[str, Any]):
    """
    Zeigt den Statistik-Dialog an.
    
    Args:
        parent: Eltern-Fenster
        stats: Dictionary mit allen Statistiken
    """
    dialog = StatisticsDialog(parent, stats)
    parent.wait_window(dialog.dialog)
