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
        
        canvas = tk.Canvas(canvas_frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Canvas-Window mit expliziter Breite erstellen
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=860)
        
        def on_frame_configure(event):
            # Scrollregion aktualisieren
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_canvas_configure(event):
            # Breite des scrollable_frame an Canvas-Breite anpassen
            canvas.itemconfig(canvas_window, width=event.width)
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mausrad-Scrolling aktivieren
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Unbind beim Schließen des Dialogs
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), self.dialog.destroy()))
        
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
        card_frame = ttk.LabelFrame(parent, text=display_name, padding="15")
        card_frame.pack(fill=tk.X, pady=(0, 15))
        
        total_records = field_data.get('total_records', 0)
        
        # Obere Zeile: Gesamt-Info
        summary_frame = ttk.Frame(card_frame)
        summary_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            summary_frame,
            text=f"Gesamt-Records mit diesem Feld: {total_records}",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        
        # --- Sektion 1: Leere Felder ---
        self._create_comparison_section(
            card_frame,
            "📄 Leere Felder",
            field_data.get('empty_before', 0),
            field_data.get('filled_after', 0),
            total_records,
            "Waren leer",
            "Wurden befüllt",
            "Verbleiben leer"
        )
        
        # --- Sektion 2: Abkürzungen ---
        self._create_comparison_section(
            card_frame,
            "📝 Abkürzungen",
            field_data.get('had_abbreviation', 0),
            field_data.get('abbreviation_replaced', 0),
            total_records,
            "Enthielten Abkürzung",
            "Wurden ausgeschrieben",
            "Verbleiben abgekürzt"
        )
        
        # --- Sektion 3: Fehlerhafte Einträge ---
        if field_key == 'Year':  # Nur für Jahr relevant
            self._create_comparison_section(
                card_frame,
                "🔧 Fehlerhafte Einträge",
                field_data.get('potentially_incorrect', 0),
                field_data.get('corrected', 0),
                total_records,
                "Potenziell fehlerhaft",
                "Wurden korrigiert",
                "Verbleiben fehlerhaft"
            )
        
        # --- Sektion 4: Konflikte ---
        conflicts = field_data.get('conflicts', 0)
        if conflicts > 0:
            conflict_frame = ttk.Frame(card_frame)
            conflict_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Label(
                conflict_frame,
                text=f"⚠️ Konflikte: {conflicts}",
                font=("Segoe UI", 9),
                foreground="red"
            ).pack(anchor="w")
            
            ttk.Label(
                conflict_frame,
                text="(Datensätze mit zu großen Abweichungen zwischen Quelle und API)",
                font=("Segoe UI", 8),
                foreground="gray"
            ).pack(anchor="w", padx=(20, 0))
    
    def _create_comparison_section(self, parent: ttk.Frame, title: str, 
                                   before_count: int, improved_count: int, total: int,
                                   before_label: str, improved_label: str, remaining_label: str):
        """Erstellt eine Vorher-Nachher-Vergleichs-Sektion."""
        section_frame = ttk.LabelFrame(parent, text=title, padding="10")
        section_frame.pack(fill=tk.X, pady=(0, 10))
        
        remaining_count = before_count - improved_count
        
        # Zwei-Spalten-Layout
        columns_frame = ttk.Frame(section_frame)
        columns_frame.pack(fill=tk.X)
        
        # Linke Spalte: Vorher-Zustand
        left_col = ttk.Frame(columns_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Label(
            left_col,
            text="Vorher:",
            font=("Segoe UI", 9, "bold"),
            foreground="#d32f2f"  # Rot
        ).pack(anchor="w", pady=(0, 5))
        
        self._create_stat_bar(
            left_col,
            before_label,
            before_count,
            total,
            "#ef5350"  # Helles Rot
        )
        
        # Rechte Spalte: Nachher-Zustand
        right_col = ttk.Frame(columns_frame)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        ttk.Label(
            right_col,
            text="Nachher:",
            font=("Segoe UI", 9, "bold"),
            foreground="#388e3c"  # Grün
        ).pack(anchor="w", pady=(0, 5))
        
        self._create_stat_bar(
            right_col,
            improved_label,
            improved_count,
            total,
            "#66bb6a"  # Helles Grün
        )
        
        self._create_stat_bar(
            right_col,
            remaining_label,
            remaining_count,
            total,
            "#ffb74d"  # Orange
        )
        
        # Verbesserungsrate berechnen und anzeigen
        if before_count > 0:
            improvement_rate = (improved_count / before_count) * 100
            
            rate_frame = ttk.Frame(section_frame)
            rate_frame.pack(fill=tk.X, pady=(10, 0))
            
            rate_color = "#388e3c" if improvement_rate >= 70 else "#ff9800" if improvement_rate >= 40 else "#d32f2f"
            
            ttk.Label(
                rate_frame,
                text=f"✓ Verbesserungsrate: {improvement_rate:.1f}% ({improved_count} von {before_count})",
                font=("Segoe UI", 9, "bold"),
                foreground=rate_color
            ).pack(anchor="w")
    
    def _create_stat_bar(self, parent: ttk.Frame, label: str, value: int, total: int, color: str):
        """Erstellt einen Statistik-Balken mit Label."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=2)
        
        # Label + Wert
        label_frame = ttk.Frame(row_frame)
        label_frame.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Label(
            label_frame,
            text=label,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            label_frame,
            text=f"{value}",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.RIGHT)
        
        # Balken
        bar_container = tk.Frame(row_frame, height=18, bg="lightgray", relief=tk.SUNKEN, bd=1)
        bar_container.pack(fill=tk.X)
        
        if total > 0 and value > 0:
            bar_width = value / total
            bar = tk.Frame(bar_container, bg=color, height=18)
            bar.place(x=0, y=0, relwidth=bar_width, relheight=1.0)
            
            # Prozent-Label
            if bar_width > 0.15:  # Nur wenn genug Platz
                percent = (value / total * 100)
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
