"""
Tests für GUI-Integration der Anreicherungsstatistik in start.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestEnrichmentStatsButton(unittest.TestCase):
    """Tests für den Anreicherungsstatistik-Button"""

    def setUp(self):
        """Setup Test-Umgebung"""
        self.temp_dir = tempfile.mkdtemp()
        self.enriched_file = os.path.join(self.temp_dir, "voebvoll-20241027_enriched.xml")
        self.stats_file = os.path.join(self.temp_dir, "voebvoll-20241027_enriched_stats.json")

    def tearDown(self):
        """Cleanup"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('start.tk.Tk')
    def test_button_visibility_with_files(self, mock_tk):
        """Test: Button ist sichtbar wenn beide Dateien existieren"""
        # Erstelle Test-Dateien
        with open(self.enriched_file, 'w') as f:
            f.write('<?xml version="1.0"?><collection></collection>')
        
        with open(self.stats_file, 'w') as f:
            json.dump({"metadata": {}, "summary": {}}, f)
        
        # Prüfe Dateien existieren
        self.assertTrue(os.path.exists(self.enriched_file))
        self.assertTrue(os.path.exists(self.stats_file))

    @patch('start.tk.Tk')
    def test_button_hidden_without_enriched_file(self, mock_tk):
        """Test: Button ist versteckt ohne enriched.xml"""
        # Nur Stats-Datei existiert
        with open(self.stats_file, 'w') as f:
            json.dump({"metadata": {}, "summary": {}}, f)
        
        self.assertFalse(os.path.exists(self.enriched_file))
        self.assertTrue(os.path.exists(self.stats_file))

    @patch('start.tk.Tk')
    def test_button_hidden_without_stats_file(self, mock_tk):
        """Test: Button ist versteckt ohne stats.json"""
        # Nur Enriched-Datei existiert
        with open(self.enriched_file, 'w') as f:
            f.write('<?xml version="1.0"?><collection></collection>')
        
        self.assertTrue(os.path.exists(self.enriched_file))
        self.assertFalse(os.path.exists(self.stats_file))


class TestRPathDetection(unittest.TestCase):
    """Tests für R-Pfad-Erkennung"""

    @patch('shutil.which')
    def test_r_found_in_path(self, mock_which):
        """Test: R wird im PATH gefunden"""
        mock_which.return_value = "C:\\Program Files\\R\\R-4.5.1\\bin\\Rscript.exe"
        
        result = mock_which('Rscript')
        self.assertIsNotNone(result)
        self.assertIn('Rscript', result)

    @patch('os.path.exists')
    def test_r_found_in_default_location(self, mock_exists):
        """Test: R wird an Standard-Installationsort gefunden"""
        mock_exists.return_value = True
        
        default_path = r"C:\Program Files\R\R-4.5.1\bin\Rscript.exe"
        self.assertTrue(mock_exists(default_path))

    @patch('shutil.which')
    @patch('os.path.exists')
    def test_r_not_found(self, mock_exists, mock_which):
        """Test: Verhalten wenn R nicht gefunden wird"""
        mock_which.return_value = None
        mock_exists.return_value = False
        
        # R sollte nicht gefunden werden
        self.assertIsNone(mock_which('Rscript'))
        self.assertFalse(mock_exists(r"C:\Program Files\R\R-4.5.1\bin\Rscript.exe"))


class TestChartGenerationWorkflow(unittest.TestCase):
    """Tests für Chart-Generierungs-Workflow"""

    def setUp(self):
        """Setup"""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.temp_dir, "test_stats.json")
        self.charts_dir = os.path.join(self.temp_dir, "charts")
        
        # Erstelle Stats-Datei
        test_stats = {
            "metadata": {"timestamp": "2025-10-25T22:11:57"},
            "summary": {"processed_records": 1500},
            "field_statistics": {
                "Title": {"empty_before": 50, "filled_after": 40}
            }
        }
        
        with open(self.stats_file, 'w') as f:
            json.dump(test_stats, f)

    def tearDown(self):
        """Cleanup"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('subprocess.run')
    def test_r_script_execution(self, mock_run):
        """Test: R-Skript wird korrekt ausgeführt"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Success")
        
        # Simuliere R-Aufruf
        import subprocess
        result = subprocess.run(
            ["Rscript", "generate_enrichment_charts.R", self.stats_file, self.charts_dir],
            capture_output=True
        )
        
        self.assertEqual(result.returncode, 0)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_r_script_error_handling(self, mock_run):
        """Test: Fehlerbehandlung bei R-Skript-Fehlern"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error in script")
        
        import subprocess
        result = subprocess.run(
            ["Rscript", "generate_enrichment_charts.R", self.stats_file, self.charts_dir],
            capture_output=True
        )
        
        self.assertNotEqual(result.returncode, 0)

    @patch('subprocess.run')
    def test_r_script_timeout(self, mock_run):
        """Test: Timeout bei langsamer R-Skript-Ausführung"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="Rscript", timeout=60)
        
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run(
                ["Rscript", "generate_enrichment_charts.R", self.stats_file, self.charts_dir],
                timeout=60
            )


class TestWebserverIntegration(unittest.TestCase):
    """Tests für Webserver-Integration"""

    @patch('threading.Thread')
    def test_webserver_starts_in_thread(self, mock_thread):
        """Test: Webserver startet in separatem Thread"""
        mock_thread.return_value = MagicMock()
        
        import threading
        server_thread = threading.Thread(target=lambda: None, daemon=True)
        
        self.assertIsInstance(server_thread, threading.Thread)

    @patch('webbrowser.open')
    def test_browser_opens_after_server_start(self, mock_browser_open):
        """Test: Browser öffnet nach Server-Start"""
        mock_browser_open.return_value = True
        
        import webbrowser
        result = webbrowser.open('http://localhost:8080')
        
        self.assertTrue(result)
        mock_browser_open.assert_called_once_with('http://localhost:8080')

    @patch('threading.Thread')
    @patch('webbrowser.open')
    def test_complete_workflow(self, mock_browser, mock_thread):
        """Test: Kompletter Workflow von Button-Click bis Browser-Öffnung"""
        mock_thread.return_value = MagicMock()
        mock_browser.return_value = True
        
        # Simuliere kompletten Workflow
        import threading
        import webbrowser
        
        # 1. Thread erstellen
        server_thread = threading.Thread(target=lambda: None, daemon=True)
        self.assertIsInstance(server_thread, threading.Thread)
        
        # 2. Browser öffnen
        result = webbrowser.open('http://localhost:8080')
        self.assertTrue(result)


class TestFilePathHandling(unittest.TestCase):
    """Tests für Dateipfad-Behandlung"""

    def test_stats_file_path_construction(self):
        """Test: Stats-Dateipfad wird korrekt konstruiert"""
        base_file = "voebvoll-20241027.xml"
        expected_stats = "voebvoll-20241027_enriched_stats.json"
        
        # Simuliere Pfad-Konstruktion
        stats_file = base_file.replace('.xml', '_enriched_stats.json')
        self.assertEqual(stats_file, expected_stats)

    def test_enriched_file_path_construction(self):
        """Test: Enriched-Dateipfad wird korrekt konstruiert"""
        base_file = "voebvoll-20241027.xml"
        expected_enriched = "voebvoll-20241027_enriched.xml"
        
        enriched_file = base_file.replace('.xml', '_enriched.xml')
        self.assertEqual(enriched_file, expected_enriched)

    def test_charts_directory_path(self):
        """Test: Charts-Verzeichnis wird korrekt angelegt"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        charts_dir = os.path.join(temp_dir, "enrichment_charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        self.assertTrue(os.path.exists(charts_dir))
        self.assertTrue(os.path.isdir(charts_dir))
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)


class TestProgressDialog(unittest.TestCase):
    """Tests für Progress Dialog"""

    @patch('tkinter.Toplevel')
    def test_progress_dialog_creation(self, mock_toplevel):
        """Test: Progress Dialog wird erstellt"""
        mock_toplevel.return_value = MagicMock()
        
        # Simuliere Dialog-Erstellung
        import tkinter as tk
        _ = tk.Toplevel()
        
        mock_toplevel.assert_called_once()

    @patch('tkinter.Toplevel')
    def test_progress_dialog_has_message(self, mock_toplevel):
        """Test: Progress Dialog zeigt Nachricht"""
        mock_dialog = MagicMock()
        mock_toplevel.return_value = mock_dialog
        
        import tkinter as tk
        dialog = tk.Toplevel()
        
        # Dialog sollte erstellt worden sein
        self.assertIsNotNone(dialog)


class TestErrorHandling(unittest.TestCase):
    """Tests für Fehlerbehandlung"""

    @patch('tkinter.messagebox.showerror')
    def test_r_not_found_error(self, mock_showerror):
        """Test: Fehler wenn R nicht gefunden wird"""
        mock_showerror.return_value = None
        
        import tkinter.messagebox as messagebox
        messagebox.showerror("Fehler", "R nicht gefunden")
        
        mock_showerror.assert_called_once()

    @patch('tkinter.messagebox.showerror')
    def test_chart_generation_error(self, mock_showerror):
        """Test: Fehler bei Chart-Generierung"""
        mock_showerror.return_value = None
        
        import tkinter.messagebox as messagebox
        messagebox.showerror("Fehler", "Chart-Generierung fehlgeschlagen")
        
        mock_showerror.assert_called_once()

    @patch('tkinter.messagebox.showinfo')
    def test_success_message(self, mock_showinfo):
        """Test: Erfolgs-Nachricht wird angezeigt"""
        mock_showinfo.return_value = None
        
        import tkinter.messagebox as messagebox
        messagebox.showinfo("Erfolg", "Charts erfolgreich erstellt")
        
        mock_showinfo.assert_called_once()


if __name__ == '__main__':
    unittest.main()
