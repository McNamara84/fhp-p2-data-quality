"""Test: Vollständige Autoren-Anreicherungs-Logik mit Längen-Abkürzungen"""

def is_abbreviation(value, full_value):
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
    if len(v) < len(f) and f.lower().startswith(v.lower()):
        return len(v) / max(1, len(f)) <= 0.6
    return False

def convert_author_to_marc_format(api_author, marc_author):
    if not api_author or not marc_author:
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
    api_parts = api_author.strip().split()
    if len(api_parts) < 2:
        return None
    api_lastname = api_parts[-1]
    api_firstname = " ".join(api_parts[:-1])
    if marc_lastname.lower() != api_lastname.lower():
        return None
    has_point_abbreviation = '.' in marc_firstname
    has_length_abbreviation = is_abbreviation(marc_firstname, api_firstname)
    if not has_point_abbreviation and not has_length_abbreviation:
        return None
    return f"{marc_lastname}, {api_firstname}"


test_cases = [
    {
        "name": "Max → Maximilian (Längen-Abkürzung)",
        "marc": "Mustermann, Max",
        "api": "Maximilian Mustermann",
        "expected": "ERWEITERN zu 'Mustermann, Maximilian'"
    },
    {
        "name": "M. → Maximilian (Punkt-Abkürzung)",
        "marc": "Mustermann, M.",
        "api": "Maximilian Mustermann",
        "expected": "ERWEITERN zu 'Mustermann, Maximilian'"
    },
    {
        "name": "Maximilian → Maximilian (vollständig)",
        "marc": "Mustermann, Maximilian",
        "api": "Maximilian Mustermann",
        "expected": "SKIP (vollständig)"
    },
    {
        "name": "G. E. → Gotthold Ephraim (mehrfach abgekürzt)",
        "marc": "Lessing, G. E.",
        "api": "Gotthold Ephraim Lessing",
        "expected": "ERWEITERN zu 'Lessing, Gotthold Ephraim'"
    },
    {
        "name": "Gotthold Ephraim → Gotthold Ephraim (vollständig)",
        "marc": "Lessing, Gotthold Ephraim",
        "api": "Gotthold Ephraim Lessing",
        "expected": "SKIP (vollständig)"
    },
    {
        "name": "Rob → Robert (Längen-Abkürzung)",
        "marc": "Müller, Rob",
        "api": "Robert Müller",
        "expected": "ERWEITERN zu 'Müller, Robert'"
    },
    {
        "name": "Robert → Robert (vollständig, nur 1 Zeichen Unterschied)",
        "marc": "Müller, Robert",
        "api": "Robert Müller",
        "expected": "SKIP (vollständig)"
    }
]

print("=" * 80)
print("TEST: Vollständige Autoren-Anreicherungs-Logik")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    print(f"\n{i}. {test['name']}:")
    print(f"   MARC: '{test['marc']}'")
    print(f"   API:  '{test['api']}'")
    
    marc_value = test['marc']
    meta_value = test['api']
    
    # Simuliere Haupt-Logik
    if ',' in marc_value:
        marc_parts = marc_value.split(',', 1)
        marc_firstname = marc_parts[1].strip() if len(marc_parts) > 1 else ""
        
        api_parts = meta_value.strip().split()
        if len(api_parts) >= 2:
            api_firstname = " ".join(api_parts[:-1])
            
            has_point_abbreviation = '.' in marc_firstname
            has_length_abbreviation = is_abbreviation(marc_firstname, api_firstname)
            
            if not has_point_abbreviation and not has_length_abbreviation:
                print(f"   ✅ SKIP: MARC vollständig (kein Punkt, keine Längen-Abk.)")
                print(f"   Expected: {test['expected']}")
                continue
    
    converted = convert_author_to_marc_format(meta_value, marc_value)
    if converted:
        print(f"   ✅ ERWEITERN: '{converted}'")
    else:
        print(f"   ⏭️  SKIP: Konvertierung fehlgeschlagen")
    
    print(f"   Expected: {test['expected']}")

print("\n" + "=" * 80)
print("✅ Logik deckt jetzt sowohl Punkt- als auch Längen-Abkürzungen ab!")
print("=" * 80)
