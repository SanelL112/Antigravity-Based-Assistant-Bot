import re

def fix_utils_pii():
    with open('utils.py', 'r') as f:
        content = f.read()

    new_regexes = """# Student ID patterns
_STUDENT_ID_RE = _re.compile(r'\\b(?:student\\s*id|sid|id\\s*#?)\\s*:?\\s*\\d{4,10}\\b', _re.IGNORECASE)
# IP Addresses (IPv4)
_IP_RE = _re.compile(r'\\b\\d{1,3}(?:\\.\\d{1,3}){3}\\b')
# Home directories
_HOME_DIR_RE = _re.compile(r'/home/[a-zA-Z0-9_-]+/?')"""

    content = content.replace(
        """# Student ID patterns
_STUDENT_ID_RE = _re.compile(r'\\b(?:student\\s*id|sid|id\\s*#?)\\s*:?\\s*\\d{4,10}\\b', _re.IGNORECASE)""",
        new_regexes
    )

    new_replacements = """    'dob': '[DATE]',
    'student_id': '[ID]',
    'ip': '[IP_ADDRESS]',
    'home_dir': '[HOME_DIR]',
}"""

    content = content.replace(
        """    'dob': '[DATE]',
    'student_id': '[ID]',
}""",
        new_replacements
    )

    new_subs = """    text = _EMAIL_RE.sub(_PII_REPLACEMENTS['email'], text)
    text = _PHONE_RE.sub(_PII_REPLACEMENTS['phone'], text)
    text = _SSN_RE.sub(_PII_REPLACEMENTS['ssn'], text)
    text = _CC_RE.sub(_PII_REPLACEMENTS['cc'], text)
    text = _DOB_RE.sub(_PII_REPLACEMENTS['dob'], text)
    text = _STUDENT_ID_RE.sub(_PII_REPLACEMENTS['student_id'], text)
    text = _IP_RE.sub(_PII_REPLACEMENTS['ip'], text)
    text = _HOME_DIR_RE.sub(_PII_REPLACEMENTS['home_dir'], text)"""

    content = content.replace(
        """    text = _EMAIL_RE.sub(_PII_REPLACEMENTS['email'], text)
    text = _PHONE_RE.sub(_PII_REPLACEMENTS['phone'], text)
    text = _SSN_RE.sub(_PII_REPLACEMENTS['ssn'], text)
    text = _CC_RE.sub(_PII_REPLACEMENTS['cc'], text)
    text = _DOB_RE.sub(_PII_REPLACEMENTS['dob'], text)
    text = _STUDENT_ID_RE.sub(_PII_REPLACEMENTS['student_id'], text)""",
        new_subs
    )

    with open('utils.py', 'w') as f:
        f.write(content)

fix_utils_pii()
print("Fixed utils.py PII")
