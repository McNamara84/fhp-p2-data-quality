"""
Test Suite für Anreicherungsstatistik-Features

Diese Test-Suite führt alle Tests für die neuen Features im Branch
feature/enrichment-statistics aus.

Features:
- API Performance Benchmark (benchmark_api_limits.py)
- R-basierte Chart-Generierung (generate_enrichment_charts.R)
- Webserver für Statistik-Dashboard (enrichment_stats_server.py)
- GUI-Integration in start.py
"""

import sys
import unittest
from pathlib import Path

# Füge Parent-Verzeichnis zum Path hinzu
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_tests(loader, tests, pattern):
    """Lädt alle Test-Module"""
    suite = unittest.TestSuite()
    
    # Lade alle neuen Test-Module
    test_modules = [
        'test_benchmark_api_limits',
        'test_chart_generation',
        'test_enrichment_stats_server',
        'test_gui_stats_integration'
    ]
    
    for module_name in test_modules:
        try:
            module = loader.loadTestsFromName(f'tests.{module_name}')
            suite.addTests(module)
        except ImportError as e:
            print(f"⚠ Warnung: Konnte Modul {module_name} nicht laden: {e}")
    
    return suite


def run_enrichment_stats_tests(verbosity=2):
    """
    Führt alle Tests für Anreicherungsstatistik aus
    
    Args:
        verbosity: Test-Ausgabe-Level (0=quiet, 1=normal, 2=verbose)
        
    Returns:
        TestResult Objekt
    """
    loader = unittest.TestLoader()
    suite = load_tests(loader, None, None)
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


def print_test_summary(result):
    """
    Gibt eine Zusammenfassung der Test-Ergebnisse aus
    
    Args:
        result: TestResult Objekt
    """
    print("\n" + "=" * 70)
    print("TEST ZUSAMMENFASSUNG - Anreicherungsstatistik")
    print("=" * 70)
    print(f"Tests durchgeführt: {result.testsRun}")
    print(f"✓ Erfolgreich:      {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"✗ Fehlgeschlagen:   {len(result.failures)}")
    print(f"⚠ Fehler:           {len(result.errors)}")
    print(f"⊘ Übersprungen:     {len(result.skipped)}")
    print("=" * 70)
    
    if result.wasSuccessful():
        print("✓ ALLE TESTS BESTANDEN!")
    else:
        print("✗ EINIGE TESTS SIND FEHLGESCHLAGEN")
        
        if result.failures:
            print("\nFehlgeschlagene Tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\nTests mit Fehlern:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    print("=" * 70 + "\n")


class EnrichmentStatsTestCategories:
    """
    Kategorisierung der Tests nach Funktionsbereichen
    """
    
    @staticmethod
    def get_benchmark_tests():
        """Tests für API Benchmark"""
        loader = unittest.TestLoader()
        return loader.loadTestsFromName('tests.test_benchmark_api_limits')
    
    @staticmethod
    def get_chart_tests():
        """Tests für Chart-Generierung"""
        loader = unittest.TestLoader()
        return loader.loadTestsFromName('tests.test_chart_generation')
    
    @staticmethod
    def get_server_tests():
        """Tests für Webserver"""
        loader = unittest.TestLoader()
        return loader.loadTestsFromName('tests.test_enrichment_stats_server')
    
    @staticmethod
    def get_gui_tests():
        """Tests für GUI-Integration"""
        loader = unittest.TestLoader()
        return loader.loadTestsFromName('tests.test_gui_stats_integration')


def run_specific_category(category_name, verbosity=2):
    """
    Führt Tests einer bestimmten Kategorie aus
    
    Args:
        category_name: Name der Kategorie ('benchmark', 'chart', 'server', 'gui')
        verbosity: Test-Ausgabe-Level
        
    Returns:
        TestResult Objekt
    """
    categories = {
        'benchmark': EnrichmentStatsTestCategories.get_benchmark_tests,
        'chart': EnrichmentStatsTestCategories.get_chart_tests,
        'server': EnrichmentStatsTestCategories.get_server_tests,
        'gui': EnrichmentStatsTestCategories.get_gui_tests
    }
    
    if category_name not in categories:
        raise ValueError(f"Unbekannte Kategorie: {category_name}. "
                        f"Verfügbar: {', '.join(categories.keys())}")
    
    suite = categories[category_name]()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test Suite für Anreicherungsstatistik-Features'
    )
    parser.add_argument(
        '--category',
        choices=['all', 'benchmark', 'chart', 'server', 'gui'],
        default='all',
        help='Test-Kategorie auswählen (default: all)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=2,
        help='Erhöht Test-Ausgabe-Level'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("ANREICHERUNGSSTATISTIK - TEST SUITE")
    print("=" * 70)
    print("Branch: feature/enrichment-statistics")
    print(f"Kategorie: {args.category}")
    print(f"Verbosity: {args.verbose}")
    print("=" * 70 + "\n")
    
    if args.category == 'all':
        result = run_enrichment_stats_tests(verbosity=args.verbose)
    else:
        result = run_specific_category(args.category, verbosity=args.verbose)
    
    print_test_summary(result)
    
    # Exit-Code basierend auf Test-Erfolg
    sys.exit(0 if result.wasSuccessful() else 1)
