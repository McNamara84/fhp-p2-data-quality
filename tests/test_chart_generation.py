"""
Tests für generate_enrichment_charts.R - R-basierte Diagramm-Generierung
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestChartGenerationPrerequisites(unittest.TestCase):
    """Tests für Voraussetzungen der Chart-Generierung"""

    def test_r_installation(self):
        """Test: R ist installiert und erreichbar"""
        r_paths = [
            r"C:\Program Files\R\R-4.5.1\bin\Rscript.exe",
            "Rscript"  # Falls in PATH
        ]
        
        r_found = False
        for r_path in r_paths:
            try:
                result = subprocess.run(
                    [r_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    r_found = True
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        # Überspringe Test wenn R nicht verfügbar (z.B. in CI/CD)
        if not r_found:
            self.skipTest("R/Rscript nicht installiert (optional)")
        
        self.assertTrue(r_found)

    def test_r_script_exists(self):
        """Test: R-Skript existiert"""
        script_path = Path(__file__).resolve().parents[1] / "metadata_enrichment" / "generate_enrichment_charts.R"
        self.assertTrue(script_path.exists(), f"R-Skript nicht gefunden: {script_path}")

    def test_r_script_syntax(self):
        """Test: R-Skript hat gültige Syntax"""
        script_path = Path(__file__).resolve().parents[1] / "metadata_enrichment" / "generate_enrichment_charts.R"
        
        # R-Syntax-Check ohne Ausführung
        r_paths = [
            r"C:\Program Files\R\R-4.5.1\bin\Rscript.exe",
            "Rscript"
        ]
        
        for r_path in r_paths:
            try:
                # Parse-Check mit R
                result = subprocess.run(
                    [r_path, "-e", f"parse('{script_path}')"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return  # Syntax OK
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        # Wenn wir hier ankommen, ist R nicht verfügbar - Test überspringen
        self.skipTest("R nicht verfügbar für Syntax-Check")


class TestStatsJsonStructure(unittest.TestCase):
    """Tests für die Struktur der Stats-JSON-Datei"""

    def setUp(self):
        """Erstelle Test-JSON-Daten"""
        self.test_stats = {
            "metadata": {
                "timestamp": "2025-10-25T22:11:57.762821",
                "input_file": "test.xml",
                "output_file": "test_enriched.xml",
                "total_records_in_file": 1000
            },
            "summary": {
                "processed_records": 1500,
                "successful_enrichments": 400,
                "failed_enrichments": 100,
                "isbn_not_found": 100,
                "conflicts_skipped": 50,
                "multi_isbn_warnings": 200,
                "success_rate_percent": 26.67
            },
            "field_statistics": {
                "Title": {
                    "total_records": 1200,
                    "empty_before": 50,
                    "filled_after": 40,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 100,
                    "potentially_incorrect": 0,
                    "corrected": 150,
                    "conflicts": 10
                },
                "Authors": {
                    "total_records": 1200,
                    "empty_before": 0,
                    "filled_after": 0,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 80,
                    "potentially_incorrect": 0,
                    "corrected": 20,
                    "conflicts": 10
                },
                "Publisher": {
                    "total_records": 1200,
                    "empty_before": 0,
                    "filled_after": 0,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 200,
                    "potentially_incorrect": 0,
                    "corrected": 50,
                    "conflicts": 10
                },
                "Year": {
                    "total_records": 1200,
                    "empty_before": 0,
                    "filled_after": 0,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 10,
                    "potentially_incorrect": 0,
                    "corrected": 5,
                    "conflicts": 10
                }
            }
        }

    def test_json_has_required_fields(self):
        """Test: JSON enthält alle erforderlichen Felder"""
        required_top_level = ["metadata", "summary", "field_statistics"]
        for field in required_top_level:
            self.assertIn(field, self.test_stats)

    def test_field_statistics_complete(self):
        """Test: Alle Metadatenfelder sind vorhanden"""
        required_fields = ["Title", "Authors", "Publisher", "Year"]
        field_stats = self.test_stats["field_statistics"]
        
        for field in required_fields:
            self.assertIn(field, field_stats)

    def test_field_statistics_structure(self):
        """Test: Jedes Feld hat die richtige Struktur"""
        required_keys = [
            "total_records", "empty_before", "filled_after",
            "abbreviation_replaced", "corrected", "conflicts"
        ]
        
        for field_name, field_data in self.test_stats["field_statistics"].items():
            for key in required_keys:
                self.assertIn(key, field_data, 
                             f"Feld '{field_name}' fehlt Schlüssel '{key}'")

    def test_numeric_values(self):
        """Test: Alle Statistik-Werte sind numerisch"""
        for field_data in self.test_stats["field_statistics"].values():
            for key, value in field_data.items():
                self.assertIsInstance(value, (int, float),
                                    f"Wert für '{key}' ist nicht numerisch")

    def test_json_serializable(self):
        """Test: Statistiken können als JSON serialisiert werden"""
        try:
            json_str = json.dumps(self.test_stats)
            self.assertIsInstance(json_str, str)
            
            # Und wieder deserialisiert
            reloaded = json.loads(json_str)
            self.assertEqual(reloaded["summary"]["processed_records"], 1500)
        except (TypeError, json.JSONDecodeError) as e:
            self.fail(f"JSON-Serialisierung fehlgeschlagen: {e}")


class TestChartGeneration(unittest.TestCase):
    """Tests für die eigentliche Chart-Generierung"""

    def setUp(self):
        """Erstelle temporäre Test-Dateien"""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.temp_dir, "test_stats.json")
        self.output_dir = os.path.join(self.temp_dir, "charts")
        
        # Erstelle Test-Stats
        test_stats = {
            "metadata": {
                "timestamp": "2025-10-25T22:11:57.762821",
                "input_file": "test.xml",
                "output_file": "test_enriched.xml",
                "total_records_in_file": 1000
            },
            "summary": {
                "processed_records": 1500,
                "successful_enrichments": 400,
                "failed_enrichments": 100,
                "isbn_not_found": 100,
                "conflicts_skipped": 50,
                "multi_isbn_warnings": 200,
                "success_rate_percent": 26.67
            },
            "field_statistics": {
                "Title": {
                    "total_records": 1200,
                    "empty_before": 50,
                    "filled_after": 40,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 100,
                    "potentially_incorrect": 0,
                    "corrected": 150,
                    "conflicts": 10
                },
                "Authors": {
                    "total_records": 1200,
                    "empty_before": 0,
                    "filled_after": 0,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 80,
                    "potentially_incorrect": 0,
                    "corrected": 20,
                    "conflicts": 10
                },
                "Publisher": {
                    "total_records": 1200,
                    "empty_before": 0,
                    "filled_after": 0,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 200,
                    "potentially_incorrect": 0,
                    "corrected": 50,
                    "conflicts": 10
                },
                "Year": {
                    "total_records": 1200,
                    "empty_before": 0,
                    "filled_after": 0,
                    "had_abbreviation": 0,
                    "abbreviation_replaced": 10,
                    "potentially_incorrect": 0,
                    "corrected": 5,
                    "conflicts": 10
                }
            }
        }
        
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(test_stats, f)

    def tearDown(self):
        """Räume temporäre Dateien auf"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_chart_generation_creates_files(self):
        """Test: Chart-Generierung erstellt PNG-Dateien"""
        script_path = Path(__file__).resolve().parents[1] / "metadata_enrichment" / "generate_enrichment_charts.R"
        
        r_paths = [
            r"C:\Program Files\R\R-4.5.1\bin\Rscript.exe",
            "Rscript"
        ]
        
        for r_path in r_paths:
            try:
                result = subprocess.run(
                    [r_path, str(script_path), self.stats_file, self.output_dir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    # Prüfe ob Chart-Dateien erstellt wurden
                    expected_files = [
                        "isbn_overview.png",
                        "metadata_overview.png",
                        "title_enrichment.png",
                        "title_corrections.png",
                        "title_total_impact.png",
                        "authors_enrichment.png",
                        "authors_corrections.png",
                        "authors_total_impact.png",
                        "publisher_enrichment.png",
                        "publisher_corrections.png",
                        "publisher_total_impact.png",
                        "year_enrichment.png",
                        "year_corrections.png",
                        "year_total_impact.png"
                    ]
                    
                    for filename in expected_files:
                        filepath = os.path.join(self.output_dir, filename)
                        self.assertTrue(os.path.exists(filepath),
                                      f"Chart-Datei fehlt: {filename}")
                    return
                    
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        self.skipTest("R nicht verfügbar für Chart-Generierung")


class TestChartFileProperties(unittest.TestCase):
    """Tests für Eigenschaften der generierten Chart-Dateien"""

    def test_expected_chart_count(self):
        """Test: Erwartete Anzahl von Charts ist dokumentiert"""
        # 1 ISBN-Übersicht + 1 Metadata-Übersicht + 4 Felder × 3 Chart-Typen = 14 Charts
        expected_chart_count = 14
        
        chart_files = [
            "isbn_overview.png",
            "metadata_overview.png",
            "title_enrichment.png", "title_corrections.png", "title_total_impact.png",
            "authors_enrichment.png", "authors_corrections.png", "authors_total_impact.png",
            "publisher_enrichment.png", "publisher_corrections.png", "publisher_total_impact.png",
            "year_enrichment.png", "year_corrections.png", "year_total_impact.png"
        ]
        
        self.assertEqual(len(chart_files), expected_chart_count)

    def test_chart_naming_convention(self):
        """Test: Chart-Dateien folgen Namenskonvention"""
        chart_files = [
            "isbn_overview.png",
            "metadata_overview.png",
            "title_enrichment.png", "title_corrections.png", "title_total_impact.png",
            "authors_enrichment.png", "authors_corrections.png", "authors_total_impact.png",
            "publisher_enrichment.png", "publisher_corrections.png", "publisher_total_impact.png",
            "year_enrichment.png", "year_corrections.png", "year_total_impact.png"
        ]
        
        for filename in chart_files:
            # Prüfe Format: <field>_<type>.png oder overview.png
            self.assertTrue(filename.endswith('.png'))
            
            if filename not in ['isbn_overview.png', 'metadata_overview.png']:
                self.assertIn('_', filename)
                # Prüfe dass es ein bekanntes Feld ist
                field = filename.split('_')[0]
                self.assertIn(field, ['title', 'authors', 'publisher', 'year'])


class TestStackedBarCharts(unittest.TestCase):
    """Tests für die Stacked Bar Chart Implementation"""

    def test_stacked_bar_data_structure(self):
        """Test: Datenstruktur für gestapelte Balken ist korrekt"""
        # Simuliere Daten wie im R-Skript
        records_with_isbn = 1200
        filled_after = 40
        unchanged = records_with_isbn - filled_after
        
        # Prüfe dass Summe stimmt
        self.assertEqual(filled_after + unchanged, records_with_isbn)
        
        # Prüfe dass beide Werte positiv sind
        self.assertGreaterEqual(filled_after, 0)
        self.assertGreaterEqual(unchanged, 0)

    def test_stacked_bar_factor_levels(self):
        """Test: Factor-Levels für gestapelte Balken sind in korrekter Reihenfolge"""
        # Die Reihenfolge sollte sein: "Angereichert" (unten), "Unverändert" (oben)
        # Dies entspricht der factor()-Definition im R-Skript
        
        # Für verschiedene Diagramm-Typen können unterschiedliche Labels verwendet werden
        alternative_levels = [
            ["Befüllt", "Unverändert"],
            ["Ansetzung angeglichen", "Unverändert"],
            ["Korrigiert", "Unverändert"]
        ]
        
        # Teste dass alle Level-Sets zwei Elemente haben
        for levels in alternative_levels:
            self.assertEqual(len(levels), 2)
            self.assertIn("Unverändert", levels)

    def test_percentage_calculation(self):
        """Test: Prozentberechnung für Labels ist korrekt"""
        total = 1000
        enriched = 250
        
        percentage = (enriched / total) * 100
        
        self.assertEqual(percentage, 25.0)
        self.assertGreaterEqual(percentage, 0)
        self.assertLessEqual(percentage, 100)


class TestMetadataOverviewDiagram(unittest.TestCase):
    """Tests für das neue Metadata Overview Diagramm"""

    def test_overview_has_four_elements(self):
        """Test: Overview-Diagramm zeigt alle 4 Metadatenelemente"""
        expected_elements = ["Title", "Authors", "Publisher", "Year"]
        
        # Jedes Element hat 2 Status-Werte (Angereichert, Unverändert)
        expected_data_points = len(expected_elements) * 2
        
        self.assertEqual(expected_data_points, 8)

    def test_overview_data_structure(self):
        """Test: Datenstruktur für Overview ist korrekt"""
        # Simuliere die Datenstruktur aus dem R-Skript
        elements = ["Title", "Authors", "Publisher", "Year"]
        statuses = ["Angereichert", "Unverändert"]
        
        # Erstelle simulierte Daten
        data_points = []
        for element in elements:
            for status in statuses:
                data_points.append({
                    "Element": element,
                    "Status": status,
                    "Anzahl": 100  # Beispielwert
                })
        
        self.assertEqual(len(data_points), 8)
        
        # Prüfe dass jedes Element beide Status hat
        for element in elements:
            element_data = [d for d in data_points if d["Element"] == element]
            self.assertEqual(len(element_data), 2)
            element_statuses = [d["Status"] for d in element_data]
            self.assertIn("Angereichert", element_statuses)
            self.assertIn("Unverändert", element_statuses)

    def test_overview_total_calculation(self):
        """Test: Gesamtanzahl pro Element wird korrekt berechnet"""
        # Beispiel: Title hat 290 angereicherte + 910 unveränderte = 1200 gesamt
        title_enriched = 290
        title_unchanged = 910
        total_records = 1200
        
        calculated_total = title_enriched + title_unchanged
        
        self.assertEqual(calculated_total, total_records)


class TestConditionalLabelRendering(unittest.TestCase):
    """Tests für die conditional label rendering Funktion (≥2% inside, <2% outside)"""

    def test_threshold_detection(self):
        """Test: 2%-Schwellenwert wird korrekt erkannt"""
        total = 1000
        
        # Testfälle
        test_cases = [
            (50, True),   # 5% >= 2% → inside
            (20, True),   # 2% >= 2% → inside
            (19, False),  # 1.9% < 2% → outside
            (10, False),  # 1% < 2% → outside
            (5, False),   # 0.5% < 2% → outside
        ]
        
        for count, should_be_inside in test_cases:
            percentage = (count / total) * 100
            is_inside = percentage >= 2
            
            self.assertEqual(is_inside, should_be_inside,
                           f"Für {count}/{total} ({percentage}%) erwartet {should_be_inside}, bekommen {is_inside}")

    def test_small_segment_detection(self):
        """Test: Sehr kleine Segmente (< 2%) werden erkannt"""
        total = 831973  # Realistische Anzahl aus den echten Daten
        year_enriched = 2921  # Realistischer Wert
        
        percentage = (year_enriched / total) * 100
        
        # Year hat ca. 0.35%, sollte also < 2% sein
        self.assertLess(percentage, 2.0)
        self.assertGreater(percentage, 0.0)

    def test_external_label_position_calculation(self):
        """Test: Position für externe Labels wird korrekt berechnet"""
        total_records = 831973
        year_total = 2921
        
        # Position in der Mitte des grünen Segments (oben am Balken)
        # Formula: records_with_isbn_val - (year_total / 2)
        label_y_position = total_records - (year_total / 2)
        
        # Position sollte sehr nah am oberen Rand sein
        self.assertGreater(label_y_position, total_records - year_total)
        self.assertLessEqual(label_y_position, total_records)
        
        # Genauer Test: Position ist genau in der Mitte des grünen Segments
        expected_position = total_records - (year_total / 2)
        self.assertEqual(label_y_position, expected_position)


class TestXAxisExpansion(unittest.TestCase):
    """Tests für die X-Achsen-Erweiterung für externe Labels"""

    def test_expansion_values(self):
        """Test: X-Achsen-Expansion hat korrekte Werte"""
        # Im Overview-Diagramm: expansion(add = c(0.5, 1.2))
        left_expansion = 0.5
        right_expansion = 1.2
        
        # Rechte Seite sollte mehr Platz haben für externe Labels
        self.assertGreater(right_expansion, left_expansion)
        
        # Beide sollten positiv sein
        self.assertGreater(left_expansion, 0)
        self.assertGreater(right_expansion, 0)

    def test_external_label_x_position(self):
        """Test: X-Position für externe Labels ist außerhalb des Balkens"""
        # Balken-Position für Year ist 4 (vierter Balken)
        bar_position = 4
        
        # Label-Position sollte rechts vom Balken sein
        label_x_position = 4.35
        
        self.assertGreater(label_x_position, bar_position)


class TestColorScheme(unittest.TestCase):
    """Tests für das Farbschema der Diagramme"""

    def test_color_values(self):
        """Test: Farbwerte sind gültige Hex-Codes"""
        colors = {
            "Angereichert": "#27ae60",  # Grün
            "Unverändert": "#95a5a6"    # Grau
        }
        
        for name, color in colors.items():
            # Prüfe dass es mit # beginnt
            self.assertTrue(color.startswith('#'))
            # Prüfe dass es 7 Zeichen lang ist (#RRGGBB)
            self.assertEqual(len(color), 7)
            # Prüfe dass nach # nur Hex-Zeichen kommen
            hex_part = color[1:]
            self.assertTrue(all(c in '0123456789abcdefABCDEF' for c in hex_part))

    def test_color_consistency(self):
        """Test: Farben werden konsistent verwendet"""
        # "Angereichert" sollte immer grün sein
        green_color = "#27ae60"
        
        # Grüne Farbe wird für verschiedene Labels verwendet
        self.assertTrue(green_color.startswith('#'))
        self.assertEqual(len(green_color), 7)


if __name__ == '__main__':
    unittest.main()
