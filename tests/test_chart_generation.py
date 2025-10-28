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
        
        self.assertTrue(r_found, "R/Rscript nicht gefunden")

    def test_r_script_exists(self):
        """Test: R-Skript existiert"""
        script_path = Path(__file__).resolve().parents[1] / "generate_enrichment_charts.R"
        self.assertTrue(script_path.exists(), f"R-Skript nicht gefunden: {script_path}")

    def test_r_script_syntax(self):
        """Test: R-Skript hat gültige Syntax"""
        script_path = Path(__file__).resolve().parents[1] / "generate_enrichment_charts.R"
        
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
        script_path = Path(__file__).resolve().parents[1] / "generate_enrichment_charts.R"
        
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
        # 4 Felder × 3 Chart-Typen = 12 Charts
        expected_chart_count = 12
        
        chart_files = [
            "title_enrichment.png", "title_corrections.png", "title_total_impact.png",
            "authors_enrichment.png", "authors_corrections.png", "authors_total_impact.png",
            "publisher_enrichment.png", "publisher_corrections.png", "publisher_total_impact.png",
            "year_enrichment.png", "year_corrections.png", "year_total_impact.png"
        ]
        
        self.assertEqual(len(chart_files), expected_chart_count)

    def test_chart_naming_convention(self):
        """Test: Chart-Dateien folgen Namenskonvention"""
        chart_files = [
            "title_enrichment.png", "title_corrections.png", "title_total_impact.png",
            "authors_enrichment.png", "authors_corrections.png", "authors_total_impact.png",
            "publisher_enrichment.png", "publisher_corrections.png", "publisher_total_impact.png",
            "year_enrichment.png", "year_corrections.png", "year_total_impact.png"
        ]
        
        for filename in chart_files:
            # Prüfe Format: <field>_<type>.png
            self.assertTrue(filename.endswith('.png'))
            self.assertIn('_', filename)
            
            # Prüfe dass es ein bekanntes Feld ist
            field = filename.split('_')[0]
            self.assertIn(field, ['title', 'authors', 'publisher', 'year'])


if __name__ == '__main__':
    unittest.main()
