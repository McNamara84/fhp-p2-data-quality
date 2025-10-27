"""Test: Vorname-Abkürzungen bei Autoren"""

def is_abbreviation(value, full_value):
    """Prüft, ob value eine Abkürzung von full_value ist."""
    if not value or not full_value:
        return False
    if value.strip().lower() == str(full_value).strip().lower():
        return False
    if value.strip().isdigit() and str(full_value).strip().isdigit():
        return False
    v = value.strip()
    f = str(full_value).strip()
    if v.endswith('.'):
        return True
    # nur wenn v spürbar kürzer ist
    if len(v) < len(f) and f.lower().startswith(v.lower()):
        return len(v) / max(1, len(f)) <= 0.6
    return False

def convert_author_to_marc_format(api_author, marc_author):
    """Konvertiert API-Autorennamen zu MARC-Format"""
    if not api_author or not marc_author:
        return None
    if '.' not in marc_author and ',' not in marc_author:
        return None
    if ',' not in marc_author:
        parts = api_author.strip().split()
        if len(parts) >= 2:
            lastname = parts[-1]
            firstname = " ".join(parts[:-1])
            return f"{lastname}, {firstname}"
        return None
    marc_parts = marc_author.split(',', 1)
    marc_lastname = marc_parts[0].strip()
    marc_firstname = marc_parts[1].strip() if len(marc_parts) > 1 else ""
    has_abbreviation = '.' in marc_firstname
    if not has_abbreviation:
        return None
    api_parts = api_author.strip().split()
    if len(api_parts) < 2:
        return None
    api_lastname = api_parts[-1]
    if marc_lastname.lower() != api_lastname.lower():
        return None
    api_firstname = " ".join(api_parts[:-1])
    return f"{marc_lastname}, {api_firstname}"


print("=" * 80)
print("TEST: Vorname-Abkürzungen bei Autoren")
print("=" * 80)

# Test-Fälle
test_cases = [
    {
        "name": "Max → Maximilian (Abkürzung ohne Punkt)",
        "marc": "Mustermann, Max",
        "api": "Maximilian Mustermann",
    },
    {
        "name": "M. → Maximilian (Abkürzung mit Punkt)",
        "marc": "Mustermann, M.",
        "api": "Maximilian Mustermann",
    },
    {
        "name": "Vollständiger Name (keine Abkürzung)",
        "marc": "Mustermann, Maximilian",
        "api": "Maximilian Mustermann",
    }
]

for test in test_cases:
    print(f"\n{test['name']}:")
    print(f"  MARC: '{test['marc']}'")
    print(f"  API:  '{test['api']}'")
    
    marc_value = test['marc']
    api_value = test['api']
    
    # 1. Prüfe ob vollständig (kein Punkt, hat Komma)
    if ',' in marc_value and '.' not in marc_value:
        # Prüfe ob Vorname eine Abkürzung ist
        marc_parts = marc_value.split(',', 1)
        if len(marc_parts) == 2:
            marc_firstname = marc_parts[1].strip()
            
            # API zu MARC-Format konvertieren für Vergleich
            api_parts = api_value.split()
            if len(api_parts) >= 2:
                api_lastname = api_parts[-1]
                api_firstname = " ".join(api_parts[:-1])
                
                # Prüfe ob Vorname Abkürzung ist
                is_abbrev = is_abbreviation(marc_firstname, api_firstname)
                
                print(f"  MARC Vorname: '{marc_firstname}'")
                print(f"  API Vorname:  '{api_firstname}'")
                print(f"  is_abbreviation(): {is_abbrev}")
                
                if is_abbrev:
                    print(f"  ✅ ERWETERN zu: '{marc_parts[0]}, {api_firstname}'")
                else:
                    print(f"  ⏭️  SKIP: Vorname ist vollständig oder nicht passend")
    else:
        converted = convert_author_to_marc_format(api_value, marc_value)
        if converted:
            print(f"  ✅ CONVERT zu: '{converted}'")
        else:
            print(f"  ⏭️  SKIP")

print("\n" + "=" * 80)
print("PROBLEM: Aktuelle Logik prüft nur auf Punkt, nicht auf Längen-Abkürzung!")
print("=" * 80)
print()
print("LÖSUNG: Auch ohne Punkt prüfen, ob Vorname erweitert werden kann.")
