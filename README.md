# FHP Data Quality Project

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)

## About the Project

This repository contains the code used by students of the Department **Informationswissenschaften** at the *University of Applied Sciences Potsdam* (Fachhochschule Potsdam). The project is supervised by **Prof. Dr. Heike Neuroth** in cooperation with **Carsten Schneemann**, head of the Landesfachstelle für Archive und Öffentliche Bibliotheken Brandenburg.

The focus is the dataset **"VÖB-Katalogabzug vom 27. Oktober 2024"**. It represents the MARC21 records of public libraries in the federal state Brandenburg. The goal is to evaluate the quality of this dataset and identify errors or inconsistencies.

## Features

### Graphical User Interface (GUI)
The project includes a GUI that allows you to execute all analysis and enrichment scripts with a single click. Start the GUI with:

```bash
python start.py
```

### Data Quality Analysis
- **Nach Besitz splitten**: Split records by possession (ISIL codes in field 049)
- **Nach Quelle splitten**: Split records by source (field 040$a)
- **Metadatenelemente auflisten**: List all metadata elements
- **Metadatenelemente (Menge) analysieren**: Analyze metadata element quantities
- **Primärschlüssel prüfen**: Check primary key uniqueness (field 001)
- **ISBN prüfen**: Validate ISBN numbers (field 020)
- **Leader prüfen**: Check MARC21 leader field
- **Datum prüfen**: Validate date fields (field 008)
- **Doppelte ISBN/ISSN prüfen**: Check for duplicate ISBN/ISSN numbers
- **ISIL-Codes validieren**: Validate ISIL codes against the German SIGEL database
- **Besitznachweise zählen**: Count possession records (049 tags) per record

### Metadata Enrichment
- **Sprachcodes korrigieren+anreichern**: Enriches and corrects Language Codes in Controlfield 008 and Datafield 041

The project also includes an advanced metadata enrichment feature that:
- Enriches records via the **German National Library (DNB)** using ISBN lookups
- Adds missing titles, subtitles, publishers, publication years, and author information
- Uses intelligent retry logic with exponential backoff for API requests
- Includes a progress dialog showing real-time statistics
- Generates detailed statistics and visualizations using R

**Enrichment Process:**
1. Select "Metadaten anreichern" from the main menu
2. Choose an XML file to enrich
3. Monitor the progress with detailed statistics
4. View the results in an interactive web-based dashboard

**Enrichment Statistics:**
- View comprehensive enrichment statistics with interactive charts
- Analyze success rates, retry patterns, and API performance
- Generated using R with ggplot2 for publication-quality visualizations

### Utility Tools
- **Große XML-Datei aufteilen**: Split large XML files into smaller test files
- **Webserver für Statistiken**: Built-in HTTP server for viewing enrichment statistics

## Installation

### Prerequisites
- Python 3.10 or newer
- R 4.5.1 or newer (optional, required for enrichment statistics visualization)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/McNamara84/fhp-p2-data-quality.git
cd fhp-p2-data-quality
```

2. (Optional but recommended) Create a virtual environment:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Unix/macOS:
source .venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Install R packages for enrichment statistics:
```bash
Rscript install_r_packages.R
```

### Dependencies

The project uses the following Python packages:
- **isbnlib** (3.10.14) - ISBN validation and processing
- **lxml** (5.3.0) - Efficient XML parsing
- **requests** (2.32.3) - HTTP requests for API calls
- **tqdm** (4.67.1) - Progress bars for console output

Development dependencies:
- **pytest** - Unit testing framework
- **flake8** - Code linting

## Usage

### GUI Mode (Recommended)
Start the graphical user interface:
```bash
python start.py
```

The GUI provides buttons for all available analysis and enrichment scripts.

### Command Line Mode
You can also run scripts individually from the command line:

```bash
# Check ISBN validity
python data_quality/check_isbn.py

# Split records by possession
python data_processing/split_by_possession.py

# Validate ISIL codes
python data_quality/validate_isil_codes.py

# Count possession records
python data_analysis/analyze_possession_counts.py
```

## Project Structure

```
fhp-p2-data-quality/
├── start.py                              # Main GUI application
├── requirements.txt                      # Python dependencies
│
├── data_quality/                         # Data Quality Checks
│   ├── __init__.py
│   ├── check_primary_key.py              # Primary key validation
│   ├── check_isbn.py                     # ISBN validation
│   ├── check_leader.py                   # MARC21 leader validation
│   ├── check_date_field.py               # Date field validation (008)
│   ├── check_duplicate_identifiers.py    # Duplicate ISBN/ISSN detection
│   └── validate_isil_codes.py            # ISIL code validation
│
├── data_analysis/                        # Data Analysis
│   ├── __init__.py
│   ├── analyze_elements_list.py          # List metadata elements
│   ├── analyze_elements_quantity.py      # Analyze element quantities
│   ├── analyze_possession_counts.py      # Count possession records (049 tags)
│   ├── analyze_bib_counts_stats.py       # Analyze possession count statistics
│   └── analyze_language_discrepancies.py # Analyze language discrepancies
│
├── data_processing/                      # Data Processing
│   ├── __init__.py
│   ├── split_by_possession.py            # Split by possession (ISIL)
│   ├── split_by_source.py                # Split by source (field 040)
│   ├── split_large_xml.py                # Split large XML files
│   └── enrich_language.py                # Language enrichment
│
├── metadata_enrichment/                  # Metadata Enrichment
│   ├── __init__.py
│   ├── enrich_metadata.py                # Main enrichment script
│   ├── enrichment_dialog.py              # Progress dialog
│   ├── statistics_dialog.py              # Statistics display
│   ├── enrichment_stats_server.py        # Statistics web server
│   ├── generate_enrichment_charts.R      # R script for visualizations
│   └── install_r_packages.R              # R package installer
│
├── utilities/                            # Utilities
│   ├── __init__.py
│   ├── marc_utils.py                     # MARC21 utility functions
│   └── tag_meanings.py                   # MARC21 tag descriptions
│
├── tests/                                # Unit tests
│   ├── test_check_isbn.py
│   ├── test_check_primary_key.py
│   ├── test_analyze_elements_quantity.py
│   ├── test_chart_generation.py
│   ├── test_enrichment_stats_server.py
│   └── ...
│
├── output_by_possession/                 # Output: Records split by possession
├── output_by_source/                     # Output: Records split by source
└── enrichment_charts/                    # Output: Statistical visualizations
```

## Running Tests

Execute the unit tests with `pytest`:

```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

The GitHub Actions workflow runs the same tests automatically on every pull request.

## Output Files

The scripts generate various output files:
### Enriched xml-Files
- `voebvoll-20241027_enriched.xml` - Enriched MARC21 records
- `enriched_languages.xml` - MARC21 records with enriched and corrected language codes

### Statistics files
- `elements_list.txt` - List of all metadata elements
- `elements_quantity.csv` - Metadata element quantities
- `elements_quantity_008_details.csv` - Detailed analysis of 008 field
- `elements_quantity_008_values.csv` - Distinct values from 008 field
- `elements_quantity_969_details.csv` - Detailed analysis of 969 field
- `possession_counts.csv` - Possession record counts (049 tags)
- `book_counts.csv` - Book counts by library
- `isil_matching_results.csv` - ISIL validation results
- `language_discrepancies.csv` - Language discrepancies in field 008 and 041
- `voebvoll-20241027_enriched_stats.json` - Enrichment statistics
- `enrichment_charts/*.png` - Statistical visualizations

Split records are saved in:
- `output_by_possession/` - Records split by possessiong
- `output_by_source/` - Records split by source

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.

## Acknowledgments

- **Prof. Dr. Heike Neuroth** - Project supervision
- **Carsten Schneemann** - Cooperation partner (Landesfachstelle für Archive und Öffentliche Bibliotheken Brandenburg)
- **German National Library (DNB)** - Metadata enrichment source
- **German ISIL-Agency at Stabi Berlin** - ISIL validation service
