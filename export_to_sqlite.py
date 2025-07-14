import sqlite3
import xml.etree.ElementTree as ET
from typing import Iterable, Tuple, Optional

from marc_utils import (
    DEFAULT_FILE_NAME,
    iter_records,
    get_subfield_values,
    get_controlfield_value,
)


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all database tables and indexes if they do not exist."""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            control_number VARCHAR(50) UNIQUE NOT NULL,
            leader VARCHAR(24) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_control_number ON records(control_number);

        CREATE TABLE IF NOT EXISTS controlfields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            tag CHAR(3) NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_record_tag ON controlfields(record_id, tag);

        CREATE TABLE IF NOT EXISTS datafields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            tag CHAR(3) NOT NULL,
            ind1 CHAR(1) DEFAULT ' ',
            ind2 CHAR(1) DEFAULT ' ',
            field_occurrence INTEGER DEFAULT 1,
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_record_tag_occ ON datafields(record_id, tag, field_occurrence);

        CREATE TABLE IF NOT EXISTS subfields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datafield_id INTEGER NOT NULL,
            code CHAR(1) NOT NULL,
            value TEXT NOT NULL,
            subfield_occurrence INTEGER DEFAULT 1,
            FOREIGN KEY (datafield_id) REFERENCES datafields(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_datafield_code ON subfields(datafield_id, code);

        CREATE TABLE IF NOT EXISTS libraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(20) UNIQUE NOT NULL,
            name TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_code ON libraries(code);

        CREATE TABLE IF NOT EXISTS record_libraries (
            record_id INTEGER NOT NULL,
            library_id INTEGER NOT NULL,
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
            FOREIGN KEY (library_id) REFERENCES libraries(id),
            PRIMARY KEY (record_id, library_id)
        );

        CREATE TABLE IF NOT EXISTS publishers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_name ON publishers(name);

        CREATE TABLE IF NOT EXISTS publication_places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place TEXT UNIQUE NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_place ON publication_places(place);

        CREATE TABLE IF NOT EXISTS record_main_data (
            record_id INTEGER PRIMARY KEY,
            isbn VARCHAR(20),
            title TEXT,
            subtitle TEXT,
            author TEXT,
            publisher_id INTEGER,
            publication_place_id INTEGER,
            publication_year INTEGER,
            edition TEXT,
            physical_description TEXT,
            language_code CHAR(3),
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
            FOREIGN KEY (publisher_id) REFERENCES publishers(id),
            FOREIGN KEY (publication_place_id) REFERENCES publication_places(id)
        );
        CREATE INDEX IF NOT EXISTS idx_isbn ON record_main_data(isbn);
        CREATE INDEX IF NOT EXISTS idx_title ON record_main_data(title);
        CREATE INDEX IF NOT EXISTS idx_author ON record_main_data(author);
        CREATE INDEX IF NOT EXISTS idx_year ON record_main_data(publication_year);

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT UNIQUE NOT NULL,
            subject_type INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_term ON subjects(term);
        CREATE INDEX IF NOT EXISTS idx_type ON subjects(subject_type);

        CREATE TABLE IF NOT EXISTS record_subjects (
            record_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            PRIMARY KEY (record_id, subject_id)
        );

        CREATE TABLE IF NOT EXISTS classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            classification_scheme VARCHAR(10),
            classification_number VARCHAR(50),
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_record ON classifications(record_id);
        CREATE INDEX IF NOT EXISTS idx_number ON classifications(classification_number);

        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_title ON series(title);

        CREATE TABLE IF NOT EXISTS record_series (
            record_id INTEGER NOT NULL,
            series_id INTEGER NOT NULL,
            volume VARCHAR(50),
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
            FOREIGN KEY (series_id) REFERENCES series(id),
            PRIMARY KEY (record_id, series_id)
        );
        """
    )
    conn.commit()


def _get_language_from_008(value: str) -> Optional[str]:
    if value and len(value) >= 38:
        code = value[35:38].strip()
        if code:
            return code
    return None


def import_marc_to_db(xml_file: str, db_path: str = "metadata.db") -> None:
    """Parse ``xml_file`` and store all metadata in ``db_path``."""

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    cur = conn.cursor()

    for record in iter_records(xml_file):
        leader_elem = record.find("leader")
        leader = leader_elem.text.strip() if leader_elem is not None and leader_elem.text else ""
        control_number = get_controlfield_value(record, "001")

        cur.execute(
            "INSERT INTO records (control_number, leader) VALUES (?, ?)",
            (control_number, leader),
        )
        record_id = cur.lastrowid

        language_code = None
        isbn: Optional[str] = None
        title = None
        subtitle = None
        author = None
        publisher_id = None
        place_id = None
        publication_year = None
        edition = None
        physical_description = None
        subjects: list[Tuple[str, int]] = []
        series_title = None
        series_volume = None

        for cf in record.findall("controlfield"):
            tag = cf.get("tag") or ""
            value = cf.text.strip() if cf.text else ""
            cur.execute(
                "INSERT INTO controlfields (record_id, tag, value) VALUES (?, ?, ?)",
                (record_id, tag, value),
            )
            if tag == "008":
                language_code = _get_language_from_008(value)

        field_occ: dict[str, int] = {}
        for df in record.findall("datafield"):
            tag = df.get("tag") or ""
            ind1 = df.get("ind1") or " "
            ind2 = df.get("ind2") or " "
            field_occ[tag] = field_occ.get(tag, 0) + 1
            cur.execute(
                "INSERT INTO datafields (record_id, tag, ind1, ind2, field_occurrence) VALUES (?, ?, ?, ?, ?)",
                (record_id, tag, ind1, ind2, field_occ[tag]),
            )
            datafield_id = cur.lastrowid

            sub_occ: dict[Tuple[str, str], int] = {}
            for sf in df.findall("subfield"):
                code = sf.get("code") or ""
                value = sf.text.strip() if sf.text else ""
                key = (tag, code)
                sub_occ[key] = sub_occ.get(key, 0) + 1
                cur.execute(
                    "INSERT INTO subfields (datafield_id, code, value, subfield_occurrence) VALUES (?, ?, ?, ?)",
                    (datafield_id, code, value, sub_occ[key]),
                )

            if tag == "020":
                vals = [sf.text.strip() for sf in df.findall('subfield[@code="a"]') if sf.text]
                if vals:
                    isbn = vals[0]
            elif tag == "245":
                vals_a = [sf.text.strip() for sf in df.findall('subfield[@code="a"]') if sf.text]
                vals_b = [sf.text.strip() for sf in df.findall('subfield[@code="b"]') if sf.text]
                if vals_a:
                    title = vals_a[0]
                if vals_b:
                    subtitle = vals_b[0]
            elif tag == "100":
                vals = [sf.text.strip() for sf in df.findall('subfield[@code="a"]') if sf.text]
                if vals:
                    author = vals[0]
            elif tag == "260":
                pub = None
                place = None
                year = None
                for sf in df.findall("subfield"):
                    code = sf.get("code")
                    if code == "a" and sf.text:
                        place = sf.text.strip().rstrip(" :;/[]")
                    elif code == "b" and sf.text:
                        pub = sf.text.strip().rstrip(" :;/[]")
                    elif code == "c" and sf.text:
                        digits = ''.join(ch for ch in sf.text if ch.isdigit())
                        year = digits[:4] if digits else None
                if pub:
                    cur.execute("INSERT OR IGNORE INTO publishers (name) VALUES (?)", (pub,))
                    cur.execute("SELECT id FROM publishers WHERE name=?", (pub,))
                    publisher_id = cur.fetchone()[0]
                if place:
                    cur.execute("INSERT OR IGNORE INTO publication_places (place) VALUES (?)", (place,))
                    cur.execute("SELECT id FROM publication_places WHERE place=?", (place,))
                    place_id = cur.fetchone()[0]
                if year:
                    publication_year = int(year)
            elif tag == "049":
                for sf in df.findall('subfield'):
                    if sf.get('code') == 'a' and sf.text:
                        code = sf.text.strip()
                        cur.execute("INSERT OR IGNORE INTO libraries (code) VALUES (?)", (code,))
                        cur.execute("SELECT id FROM libraries WHERE code=?", (code,))
                        lib_id = cur.fetchone()[0]
                        cur.execute(
                            "INSERT OR IGNORE INTO record_libraries (record_id, library_id) VALUES (?, ?)",
                            (record_id, lib_id),
                        )
            elif tag == "250":
                vals = [sf.text.strip() for sf in df.findall('subfield[@code="a"]') if sf.text]
                if vals:
                    edition = vals[0]
            elif tag == "300":
                vals = [sf.text.strip() for sf in df.findall('subfield[@code="a"]') if sf.text]
                if vals:
                    physical_description = vals[0]
            elif tag == "653":
                subject_type = 0
                try:
                    subject_type = int(ind2) if ind2.isdigit() else 0
                except ValueError:
                    subject_type = 0
                for sf in df.findall('subfield[@code="a"]'):
                    if sf.text:
                        subjects.append((sf.text.strip(), subject_type))
            elif tag == "490":
                for sf in df.findall('subfield'):
                    if sf.get('code') == 'a' and sf.text:
                        series_title = sf.text.strip()
                    elif sf.get('code') == 'v' and sf.text:
                        series_volume = sf.text.strip()
            elif tag == "084":
                scheme = None
                number = None
                for sf in df.findall('subfield'):
                    code = sf.get('code')
                    if code == 'a' and sf.text:
                        number = sf.text.strip()
                    elif code in {'2', '9'} and sf.text:
                        scheme = sf.text.strip()
                if number:
                    cur.execute(
                        "INSERT INTO classifications (record_id, classification_scheme, classification_number) VALUES (?, ?, ?)",
                        (record_id, scheme, number),
                    )

        for term, stype in subjects:
            cur.execute("INSERT OR IGNORE INTO subjects (term, subject_type) VALUES (?, ?)", (term, stype))
            cur.execute("SELECT id FROM subjects WHERE term=?", (term,))
            subj_id = cur.fetchone()[0]
            cur.execute(
                "INSERT OR IGNORE INTO record_subjects (record_id, subject_id) VALUES (?, ?)",
                (record_id, subj_id),
            )

        if series_title:
            cur.execute("INSERT OR IGNORE INTO series (title) VALUES (?)", (series_title,))
            cur.execute("SELECT id FROM series WHERE title=?", (series_title,))
            series_id = cur.fetchone()[0]
            cur.execute(
                "INSERT OR IGNORE INTO record_series (record_id, series_id, volume) VALUES (?, ?, ?)",
                (record_id, series_id, series_volume),
            )

        cur.execute(
            "INSERT INTO record_main_data (record_id, isbn, title, subtitle, author, publisher_id, publication_place_id, publication_year, edition, physical_description, language_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record_id,
                isbn,
                title,
                subtitle,
                author,
                publisher_id,
                place_id,
                publication_year,
                edition,
                physical_description,
                language_code,
            ),
        )

        conn.commit()

    conn.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Export MARC21 to SQLite")
    parser.add_argument("xml", nargs="?", default=DEFAULT_FILE_NAME, help="XML file to read")
    parser.add_argument("db", nargs="?", default="metadata.db", help="SQLite database file")
    args = parser.parse_args()

    import_marc_to_db(args.xml, args.db)


if __name__ == "__main__":
    main()