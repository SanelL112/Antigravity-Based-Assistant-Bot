import os
import glob

def test_no_ufffd_in_sources():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    py_files = glob.glob(os.path.join(root_dir, '**', '*.py'), recursive=True)

    py_files = [f for f in py_files if '/venv/' not in f and '/.pytest_cache/' not in f]

    invalid_files = []
    for filepath in py_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if '\ufffd' in content:
                    invalid_files.append(filepath)
        except Exception:
            pass

    assert not invalid_files, f"Found U+FFFD characters in: {invalid_files}"
