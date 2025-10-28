#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Webserver für die Anreicherungsstatistik-Anzeige.

Startet einen lokalen HTTP-Server und stellt eine interaktive Webseite
mit den Anreicherungsstatistiken bereit.
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class StatsRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler für Statistik-Anzeige."""
    
    stats_file_path = None  # Wird von start_stats_server gesetzt
    charts_dir_path = None  # Verzeichnis mit Diagrammen
    
    def log_message(self, format, *args):
        """Überschreibe Logging um Console-Spam zu vermeiden."""
        pass  # Stille Ausgabe
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            # Hauptseite
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_html_page().encode('utf-8'))
            
        elif parsed_path.path == '/api/stats':
            # JSON-Daten API
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            try:
                with open(self.stats_file_path, 'r', encoding='utf-8') as f:
                    stats_data = f.read()
                self.wfile.write(stats_data.encode('utf-8'))
            except Exception as e:
                error_data = json.dumps({"error": str(e)})
                self.wfile.write(error_data.encode('utf-8'))
        
        elif parsed_path.path.startswith('/charts/'):
            # Diagramm-Bilder ausliefern
            chart_name = parsed_path.path[8:]  # Entferne '/charts/'
            chart_path = os.path.join(self.charts_dir_path, chart_name)
            
            if os.path.exists(chart_path) and chart_path.endswith('.png'):
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                
                with open(chart_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Chart not found')
        
        else:
            # 404
            self.send_response(404)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>404 Not Found</h1></body></html>')
    
    def get_html_page(self):
        """Generiert die HTML-Seite für die Statistik-Anzeige."""
        return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anreicherungsstatistik - MARC21 Metadaten</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .loading {
            text-align: center;
            padding: 60px;
            font-size: 1.2em;
            color: #666;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card h3 {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        table thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        table th,
        table td {
            padding: 15px;
            text-align: left;
        }
        
        table tbody tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        table tbody tr:hover {
            background: #e9ecef;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.5s ease;
        }
        
        footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Anreicherungsstatistik</h1>
            <p>MARC21 Metadaten-Anreicherung mit ISBN-Daten</p>
        </header>
        
        <div class="content">
            <div id="loading" class="loading">
                <p>Lade Statistiken...</p>
            </div>
            
            <div id="stats-content" style="display: none;">
                <!-- Wird dynamisch mit JavaScript gefüllt -->
            </div>
        </div>
        
        <footer>
            <p>FHP P2 - Datenqualitätsanalyse | MARC21 Metadaten-Anreicherung</p>
        </footer>
    </div>
    
    <script>
        // Lade Statistiken von API
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('stats-content').style.display = 'block';
                renderStatistics(data);
            })
            .catch(error => {
                document.getElementById('loading').innerHTML = 
                    '<p style="color: red;">Fehler beim Laden der Statistiken: ' + error + '</p>';
            });
        
        function renderStatistics(data) {
            const container = document.getElementById('stats-content');
            
            // Zusammenfassung
            const summary = data.summary;
            const successRate = summary.success_rate_percent || 0;
            
            container.innerHTML = `
                <div class="section">
                    <h2>Übersicht</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3>Verarbeitete Records</h3>
                            <div class="value">${summary.processed_records.toLocaleString('de-DE')}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Erfolgreiche Anreicherungen</h3>
                            <div class="value">${summary.successful_enrichments.toLocaleString('de-DE')}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Erfolgsrate</h3>
                            <div class="value">${successRate.toFixed(2)}%</div>
                        </div>
                        <div class="stat-card">
                            <h3>Fehlgeschlagen</h3>
                            <div class="value">${summary.failed_enrichments.toLocaleString('de-DE')}</div>
                        </div>
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${successRate}%">
                            ${successRate.toFixed(1)}%
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Title - Leere Felder befüllen</h2>
                    <img src="/charts/title_enrichment.png" alt="Title Anreicherung - Leere Felder" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Title - Abkürzungen ausschreiben & Fehler korrigieren</h2>
                    <img src="/charts/title_corrections.png" alt="Title Korrekturen" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Title - Gesamtwirkung der Anreicherung</h2>
                    <img src="/charts/title_total_impact.png" alt="Title Gesamtwirkung" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Authors - Leere Felder befüllen</h2>
                    <img src="/charts/authors_enrichment.png" alt="Authors Anreicherung - Leere Felder" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Authors - Abkürzungen ausschreiben & Fehler korrigieren</h2>
                    <img src="/charts/authors_corrections.png" alt="Authors Korrekturen" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Authors - Gesamtwirkung der Anreicherung</h2>
                    <img src="/charts/authors_total_impact.png" alt="Authors Gesamtwirkung" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Publisher - Leere Felder befüllen</h2>
                    <img src="/charts/publisher_enrichment.png" alt="Publisher Anreicherung - Leere Felder" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Publisher - Abkürzungen ausschreiben & Fehler korrigieren</h2>
                    <img src="/charts/publisher_corrections.png" alt="Publisher Korrekturen" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Publisher - Gesamtwirkung der Anreicherung</h2>
                    <img src="/charts/publisher_total_impact.png" alt="Publisher Gesamtwirkung" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Year - Leere Felder befüllen</h2>
                    <img src="/charts/year_enrichment.png" alt="Year Anreicherung - Leere Felder" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Year - Abkürzungen ausschreiben & Fehler korrigieren</h2>
                    <img src="/charts/year_corrections.png" alt="Year Korrekturen" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                
                <div class="section">
                    <h2>Metadatenelement: Year - Gesamtwirkung der Anreicherung</h2>
                    <img src="/charts/year_total_impact.png" alt="Year Gesamtwirkung" style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
            `;
        }
    </script>
</body>
</html>"""


def start_stats_server(stats_file_path: str, charts_dir_path: str, port: int = 8080):
    """
    Startet einen HTTP-Server für die Statistik-Anzeige.
    
    Args:
        stats_file_path: Pfad zur JSON-Statistik-Datei
        charts_dir_path: Pfad zum Verzeichnis mit Diagrammen
        port: Port für den Webserver (default: 8080)
    """
    # Prüfe ob Datei existiert
    if not os.path.exists(stats_file_path):
        raise FileNotFoundError(f"Statistik-Datei nicht gefunden: {stats_file_path}")
    
    if not os.path.exists(charts_dir_path):
        raise FileNotFoundError(f"Diagramm-Verzeichnis nicht gefunden: {charts_dir_path}")
    
    # Setze Dateipfade als Klassenattribute
    StatsRequestHandler.stats_file_path = stats_file_path
    StatsRequestHandler.charts_dir_path = charts_dir_path
    
    # Starte Server
    server = HTTPServer(('localhost', port), StatsRequestHandler)
    print(f"✓ Statistik-Webserver läuft auf http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⚠ Webserver wird beendet...")
        server.shutdown()


if __name__ == "__main__":
    # Test-Modus: Starte Server direkt
    import sys
    
    if len(sys.argv) > 2:
        stats_file = sys.argv[1]
        charts_dir = sys.argv[2]
    else:
        stats_file = "voebvoll-20241027_enriched_stats.json"
        charts_dir = "enrichment_charts"
    
    if not os.path.exists(stats_file):
        print(f"❌ Statistik-Datei nicht gefunden: {stats_file}")
        print(f"   Verwende: python {sys.argv[0]} <stats_file.json> <charts_dir>")
        sys.exit(1)
    
    if not os.path.exists(charts_dir):
        print(f"❌ Diagramm-Verzeichnis nicht gefunden: {charts_dir}")
        sys.exit(1)
    
    print(f"📊 Starte Statistik-Server für: {stats_file}")
    print(f"📁 Diagramme aus: {charts_dir}")
    start_stats_server(stats_file, charts_dir, port=8080)
