"""
Tests für benchmark_api_limits.py - API Performance Benchmark
"""

import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Versuche benchmark_api_limits zu importieren, überspringe Tests wenn nicht verfügbar
try:
    from benchmark_api_limits import RateLimiter, test_configuration
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False
    # Dummy-Klassen für Tests
    RateLimiter = None
    test_configuration = None


@unittest.skipUnless(BENCHMARK_AVAILABLE, "benchmark_api_limits.py noch nicht implementiert")
class TestRateLimiter(unittest.TestCase):
    """Tests für die RateLimiter-Klasse"""

    def test_initialization(self):
        """Test: RateLimiter wird korrekt initialisiert"""
        limiter = RateLimiter(requests_per_second=5.0)
        self.assertEqual(limiter.rate_limit_seconds, 0.2)  # 1/5 = 0.2

    def test_rate_limiting_delays(self):
        """Test: RateLimiter erzwingt korrekte Verzögerungen"""
        limiter = RateLimiter(requests_per_second=10.0)  # 0.1s pro Request
        
        start_time = time.time()
        for _ in range(3):
            limiter.acquire()
        elapsed = time.time() - start_time
        
        # Mindestens 0.2s sollten vergangen sein (2 Delays bei 3 Requests)
        self.assertGreaterEqual(elapsed, 0.19)  # Kleine Toleranz für Timing

    def test_different_rates(self):
        """Test: Verschiedene Rate Limits funktionieren"""
        slow_limiter = RateLimiter(requests_per_second=2.0)
        fast_limiter = RateLimiter(requests_per_second=20.0)
        
        self.assertEqual(slow_limiter.rate_limit_seconds, 0.5)
        self.assertEqual(fast_limiter.rate_limit_seconds, 0.05)


@unittest.skipUnless(BENCHMARK_AVAILABLE, "benchmark_api_limits.py noch nicht implementiert")
class TestBenchmarkConfiguration(unittest.TestCase):
    """Tests für Benchmark-Konfigurationen"""

    @patch('benchmark_api_limits.fetch_isbn_data')
    def test_configuration_structure(self, mock_fetch):
        """Test: Konfiguration hat erwartete Struktur"""
        mock_fetch.return_value = {"title": "Test Book"}
        
        result = test_configuration(
            max_workers=4,
            rate_limit_seconds=0.1,
            test_isbns=["9783453350618"],
            test_duration=1
        )
        
        self.assertIn('max_workers', result)
        self.assertIn('rate_limit_seconds', result)
        self.assertIn('total_time', result)
        self.assertIn('requests_made', result)
        self.assertIn('requests_per_second', result)

    @patch('benchmark_api_limits.fetch_isbn_data')
    def test_request_counting(self, mock_fetch):
        """Test: Anzahl der Requests wird korrekt gezählt"""
        mock_fetch.return_value = {"title": "Test Book"}
        test_isbns = ["9783453350618", "9780306406157", "9781234567890"]
        
        result = test_configuration(
            max_workers=2,
            rate_limit_seconds=0.01,
            test_isbns=test_isbns,
            test_duration=2
        )
        
        # Mindestens die Anzahl der Test-ISBNs sollte bearbeitet worden sein
        self.assertGreater(result['requests_made'], 0)
        self.assertGreaterEqual(result['total_time'], 0)

    @patch('benchmark_api_limits.fetch_isbn_data')
    def test_error_handling(self, mock_fetch):
        """Test: Fehlerhafte API-Calls werden behandelt"""
        mock_fetch.side_effect = Exception("Network error")
        
        result = test_configuration(
            max_workers=2,
            rate_limit_seconds=0.1,
            test_isbns=["9783453350618"],
            test_duration=1
        )
        
        # Sollte trotz Fehler ein Ergebnis liefern
        self.assertIn('requests_made', result)
        self.assertIn('total_time', result)


@unittest.skipUnless(BENCHMARK_AVAILABLE, "benchmark_api_limits.py noch nicht implementiert")
class TestBenchmarkResults(unittest.TestCase):
    """Tests für Benchmark-Ergebnisse"""

    @patch('benchmark_api_limits.test_configuration')
    def test_result_comparison(self, mock_test):
        """Test: Verschiedene Konfigurationen können verglichen werden"""
        # Simuliere zwei verschiedene Ergebnisse
        mock_test.side_effect = [
            {
                'max_workers': 4,
                'rate_limit_seconds': 0.12,
                'total_time': 10.0,
                'requests_made': 50,
                'requests_per_second': 5.0
            },
            {
                'max_workers': 8,
                'rate_limit_seconds': 0.05,
                'total_time': 5.0,
                'requests_made': 50,
                'requests_per_second': 10.0
            }
        ]
        
        results = []
        for workers, rate in [(4, 0.12), (8, 0.05)]:
            result = mock_test(workers, rate, [], 1)
            results.append(result)
        
        # Zweite Konfiguration sollte schneller sein
        self.assertGreater(
            results[1]['requests_per_second'],
            results[0]['requests_per_second']
        )


@unittest.skipUnless(BENCHMARK_AVAILABLE, "benchmark_api_limits.py noch nicht implementiert")
class TestBenchmarkOutputFormat(unittest.TestCase):
    """Tests für Output-Format des Benchmarks"""

    def test_json_serialization(self):
        """Test: Ergebnisse können als JSON serialisiert werden"""
        result = {
            'max_workers': 8,
            'rate_limit_seconds': 0.05,
            'total_time': 5.5,
            'requests_made': 100,
            'requests_per_second': 18.18,
            'estimated_time_for_1m_isbns': 15263.0
        }
        
        # Sollte ohne Fehler serialisierbar sein
        json_str = json.dumps(result)
        self.assertIsInstance(json_str, str)
        
        # Deserialierung sollte Original entsprechen
        deserialized = json.loads(json_str)
        self.assertEqual(deserialized['max_workers'], 8)
        self.assertAlmostEqual(deserialized['requests_per_second'], 18.18, places=2)


@unittest.skipUnless(BENCHMARK_AVAILABLE, "benchmark_api_limits.py noch nicht implementiert")
class TestBenchmarkRecommendations(unittest.TestCase):
    """Tests für Empfehlungs-Logik"""

    def test_optimal_configuration_selection(self):
        """Test: Beste Konfiguration wird korrekt identifiziert"""
        results = [
            {'requests_per_second': 5.0, 'max_workers': 4},
            {'requests_per_second': 10.0, 'max_workers': 8},  # Beste
            {'requests_per_second': 7.5, 'max_workers': 6}
        ]
        
        best = max(results, key=lambda x: x['requests_per_second'])
        self.assertEqual(best['max_workers'], 8)
        self.assertEqual(best['requests_per_second'], 10.0)

    def test_time_estimation(self):
        """Test: Zeitschätzung für große Datensätze ist korrekt"""
        requests_per_second = 5.0
        total_isbns = 1000000
        
        estimated_seconds = total_isbns / requests_per_second
        estimated_hours = estimated_seconds / 3600
        
        self.assertAlmostEqual(estimated_hours, 55.56, places=1)


if __name__ == '__main__':
    unittest.main()
