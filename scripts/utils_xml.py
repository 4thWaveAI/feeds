# scripts/utils_xml.py
from html import escape
import re

_CONTROL = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')

def clean_text(s):
    if s is None: return ""
    if isinstance(s, bytes):
        s = s.decode("utf-8", "replace")
    # strip BOM + control chars
    s = s.replace("\ufeff", "")
    return _CONTROL.sub("", s)

def xml_text(s):
    # Safe for <title>, <link>, <description> (no CDATA needed)
    return escape(clean_text(s), quote=True)

def cdata_safe(s):
    # Only if you truly need HTML; neutralize "]]>"
    s = clean_text(s).replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{s}]]>"
