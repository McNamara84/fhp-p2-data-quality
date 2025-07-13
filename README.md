# FHP Data Quality Project

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Tests](https://github.com/fhp-his/fhp-p2-data-quality/actions/workflows/python-app.yml/badge.svg)

## About the Project

This repository contains the code used by students of the Department **Informationswissenschaften** at the *University of Applied Sciences Potsdam* (Fachhochschule Potsdam). The project is supervised by **Prof. Dr. Heike Neuroth** in cooperation with **Carsten Schneemann**, head of the Landesfachstelle für Archive und Öffentliche Bibliotheken Brandenburg.

The focus is the dataset **"VÖB catalogue export of 27 October 2024"**. It represents the MARC21 records of all public libraries in the federal state Brandenburg. Our goal is to evaluate the quality of this dataset and identify errors or inconsistencies.

## Installation

1. Install Python 3.10 or newer.
2. Clone this repository.
3. (Optional) Create a virtual environment and activate it.
4. Install the development dependencies:

```bash
pip install flake8 pytest
```

The analysis scripts rely only on the Python standard library, so no further packages are required.

## Running Tests

Execute the unit tests with `pytest`:

```bash
pytest
```

The GitHub Actions workflow runs the same tests automatically on every pull request.

## License
