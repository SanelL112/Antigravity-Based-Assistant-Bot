import os

def test_no_duplicate_requirements():
    req_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'requirements.txt')
    with open(req_path, 'r') as f:
        lines = f.readlines()

    seen = set()
    duplicates = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Get base package name
        base_name = line.split('=')[0].split('[')[0].split('>')[0].split('<')[0].strip().lower()
        if base_name in seen:
            duplicates.add(base_name)
        seen.add(base_name)

    assert not duplicates, f"Duplicate requirements found: {duplicates}"
