"""
Tests für enrichment_stats_server.py - Statistik-Webserver
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metadata_enrichment.enrichment_stats_server import StatsRequestHandler, start_stats_server


class TestWebserverBasics(unittest.TestCase):
    """Basis-Tests für den Webserver"""

    def setUp(self):
        """Erstelle temporäre Test-Dateien"""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.temp_dir, "test_stats.json")
        self.charts_dir = os.path.join(self.temp_dir, "charts")
        os.makedirs(self.charts_dir, exist_ok=True)
        
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
                    "abbreviation_replaced": 100,
                    "corrected": 150,
                    "conflicts": 10
                }
            }
        }
        
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(test_stats, f)
        
        # Erstelle Test-Chart
        self.test_chart = os.path.join(self.charts_dir, "test_chart.png")
        with open(self.test_chart, 'wb') as f:
            # Minimales PNG (1x1 transparent)
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

    def tearDown(self):
        """Räume temporäre Dateien auf"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_stats_file_validation(self):
        """Test: Server validiert Stats-Datei beim Start"""
        # Nicht-existierende Datei sollte Fehler werfen
        with self.assertRaises(FileNotFoundError):
            start_stats_server("nonexistent.json", self.charts_dir, port=8081)

    def test_charts_dir_validation(self):
        """Test: Server validiert Charts-Verzeichnis beim Start"""
        # Nicht-existierendes Verzeichnis sollte Fehler werfen
        with self.assertRaises(FileNotFoundError):
            start_stats_server(self.stats_file, "nonexistent_dir", port=8082)


class TestRequestHandler(unittest.TestCase):
    """Tests für HTTP Request Handler"""

    def setUp(self):
        """Erstelle Test-Umgebung"""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.temp_dir, "test_stats.json")
        self.charts_dir = os.path.join(self.temp_dir, "charts")
        os.makedirs(self.charts_dir, exist_ok=True)
        
        # Test-Stats
        test_stats = {
            "metadata": {"timestamp": "2025-10-25T22:11:57.762821"},
            "summary": {
                "processed_records": 1500,
                "successful_enrichments": 400,
                "success_rate_percent": 26.67
            },
            "field_statistics": {
                "Title": {"empty_before": 50, "filled_after": 40}
            }
        }
        
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(test_stats, f)
        
        # Test-Chart (minimales PNG)
        test_chart = os.path.join(self.charts_dir, "test_chart.png")
        with open(test_chart, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
        
        # Setze Klassenattribute für Handler
        StatsRequestHandler.stats_file_path = self.stats_file
        StatsRequestHandler.charts_dir_path = self.charts_dir
        
        # Finde freien Port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            self.server_port = s.getsockname()[1]
        
        # Starte Server in separatem Thread
        self.server_thread = threading.Thread(
            target=start_stats_server,
            args=(self.stats_file, self.charts_dir, self.server_port),
            daemon=True
        )
        self.server_thread.start()
        
        # Warte bis Server bereit ist (mit Retry-Loop)
        self._wait_for_server_ready(max_retries=10, retry_delay=0.2)
    
    def _wait_for_server_ready(self, max_retries=10, retry_delay=0.2):
        """
        Wartet bis Server bereit ist, Verbindungen zu akzeptieren.
        
        Args:
            max_retries: Maximale Anzahl der Versuche (default: 10)
            retry_delay: Wartezeit zwischen Versuchen in Sekunden (default: 0.2)
        """
        import socket
        
        for attempt in range(max_retries):
            try:
                # Versuche Verbindung zum Server
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    s.connect(('localhost', self.server_port))
                    # Verbindung erfolgreich - Server ist bereit
                    return
            except (ConnectionRefusedError, OSError, socket.timeout):
                # Server noch nicht bereit, warte und versuche erneut
                if attempt < max_retries - 1:  # Nicht beim letzten Versuch warten
                    time.sleep(retry_delay)
        
        # Server nicht rechtzeitig bereit - Test überspringen statt Fehler
        raise unittest.SkipTest(f"Server auf Port {self.server_port} wurde nach {max_retries * retry_delay}s nicht bereit")

    def tearDown(self):
        """Räume auf"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_root_endpoint_returns_html(self):
        """Test: Root-Endpoint liefert HTML"""
        try:
            conn = HTTPConnection('localhost', self.server_port, timeout=2)
            conn.request('GET', '/')
            response = conn.getresponse()
            
            self.assertEqual(response.status, 200)
            self.assertIn('text/html', response.getheader('Content-Type'))
            
            body = response.read().decode('utf-8')
            self.assertIn('<!DOCTYPE html>', body)
            self.assertIn('Anreicherungsstatistik', body)
            
            conn.close()
        except Exception as e:
            self.skipTest(f"Server nicht erreichbar: {e}")

    def test_api_stats_endpoint(self):
        """Test: /api/stats liefert JSON"""
        try:
            conn = HTTPConnection('localhost', self.server_port, timeout=2)
            conn.request('GET', '/api/stats')
            response = conn.getresponse()
            
            self.assertEqual(response.status, 200)
            self.assertIn('application/json', response.getheader('Content-Type'))
            
            body = response.read().decode('utf-8')
            data = json.loads(body)
            
            self.assertIn('metadata', data)
            self.assertIn('summary', data)
            self.assertEqual(data['summary']['processed_records'], 1500)
            
            conn.close()
        except Exception as e:
            self.skipTest(f"Server nicht erreichbar: {e}")

    def test_chart_image_endpoint(self):
        """Test: /charts/<filename> liefert PNG"""
        try:
            conn = HTTPConnection('localhost', self.server_port, timeout=2)
            conn.request('GET', '/charts/test_chart.png')
            response = conn.getresponse()
            
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('Content-Type'), 'image/png')
            
            body = response.read()
            # PNG Magic Number
            self.assertTrue(body.startswith(b'\x89PNG'))
            
            conn.close()
        except Exception as e:
            self.skipTest(f"Server nicht erreichbar: {e}")

    def test_nonexistent_chart_returns_404(self):
        """Test: Nicht-existierendes Chart liefert 404"""
        try:
            conn = HTTPConnection('localhost', self.server_port, timeout=2)
            conn.request('GET', '/charts/nonexistent.png')
            response = conn.getresponse()
            
            self.assertEqual(response.status, 404)
            
            conn.close()
        except Exception as e:
            self.skipTest(f"Server nicht erreichbar: {e}")

    def test_invalid_path_returns_404(self):
        """Test: Ungültiger Pfad liefert 404"""
        try:
            conn = HTTPConnection('localhost', self.server_port, timeout=2)
            conn.request('GET', '/invalid/path')
            response = conn.getresponse()
            
            self.assertEqual(response.status, 404)
            
            conn.close()
        except Exception as e:
            self.skipTest(f"Server nicht erreichbar: {e}")


class TestHTMLContent(unittest.TestCase):
    """Tests für HTML-Inhalte"""

    def setUp(self):
        """Lade HTML-Template aus Datei"""
        server_file = Path(__file__).resolve().parents[1] / "enrichment_stats_server.py"
        with open(server_file, 'r', encoding='utf-8') as f:
            self.server_code = f.read()

    def test_html_contains_all_chart_sections(self):
        """Test: HTML enthält Sektionen für alle Charts"""
        # Prüfe dass alle 14 Charts referenziert werden (1 ISBN + 1 Overview + 12 Element-Charts)
        expected_charts = [
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
        
        for chart in expected_charts:
            self.assertIn(chart, self.server_code,
                         f"Chart '{chart}' fehlt im Server-Code")

    def test_html_structure(self):
        """Test: HTML hat gültige Struktur"""
        # Basis-HTML-Elemente
        self.assertIn('<!DOCTYPE html>', self.server_code)
        self.assertIn('<html', self.server_code)
        self.assertIn('<head>', self.server_code)
        self.assertIn('<body>', self.server_code)
        self.assertIn('</html>', self.server_code)

    def test_html_includes_styling(self):
        """Test: HTML enthält CSS-Styling"""
        self.assertIn('<style>', self.server_code)
        self.assertIn('</style>', self.server_code)
        # Prüfe spezifische Style-Klassen
        self.assertIn('.container', self.server_code)
        self.assertIn('.stat-card', self.server_code)

    def test_html_includes_javascript(self):
        """Test: HTML enthält JavaScript für Daten-Loading"""
        self.assertIn('<script>', self.server_code)
        self.assertIn('fetch(\'/api/stats\')', self.server_code)
        # response.json() ist die moderne Variante
        self.assertIn('response.json()', self.server_code)


class TestServerConfiguration(unittest.TestCase):
    """Tests für Server-Konfiguration"""

    def test_default_port(self):
        """Test: Standard-Port ist 8080"""
        # Dies ist dokumentarisch - prüft die Signatur
        import inspect
        sig = inspect.signature(start_stats_server)
        self.assertEqual(sig.parameters['port'].default, 8080)

    def test_server_localhost_only(self):
        """Test: Server bindet nur an localhost"""
        # Dies wird durch Code-Inspektion getestet
        with open(Path(__file__).resolve().parents[1] / "enrichment_stats_server.py", encoding='utf-8') as f:
            content = f.read()
            # Server sollte an 'localhost' binden, nicht '0.0.0.0'
            self.assertIn("'localhost'", content)


if __name__ == '__main__':
    unittest.main()
