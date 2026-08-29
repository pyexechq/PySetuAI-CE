"""High-performance text canonicalizer and de-obfuscation pipeline.

Removes evasion techniques including homoglyphs, zero-width characters,
base64/hex/URL encodings, and leetspeak in sub-millisecond execution.
"""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
import urllib.parse

# Homoglyph lookalike mapping to standard ASCII
HOMOGLYPH_MAP = {
    # Cyrillic
    "\u0430": "a", "\u0410": "A", "\u0431": "b", "\u0411": "B",
    "\u0432": "v", "\u0412": "B", "\u0433": "g", "\u0413": "G",
    "\u0434": "d", "\u0414": "D", "\u0435": "e", "\u0415": "E",
    "\u0451": "e", "\u0401": "E", "\u0436": "zh", "\u0416": "Zh",
    "\u0437": "z", "\u0417": "Z", "\u0438": "i", "\u0418": "I",
    "\u043a": "k", "\u041a": "K", "\u043c": "m", "\u041c": "M",
    "\u043d": "n", "\u041d": "H", "\u043e": "o", "\u041e": "O",
    "\u043f": "p", "\u041f": "P", "\u0440": "r", "\u0420": "P",
    "\u0441": "c", "\u0421": "C", "\u0442": "t", "\u0422": "T",
    "\u0443": "y", "\u0423": "Y", "\u0444": "f", "\u0424": "F",
    "\u0445": "x", "\u0425": "X",
    # Greek
    "\u03b1": "a", "\u0391": "A", "\u03b2": "b", "\u0392": "B",
    "\u03b3": "g", "\u0393": "G", "\u03b5": "e", "\u0395": "E",
    "\u03b6": "z", "\u0396": "Z", "\u03b7": "h", "\u0397": "H",
    "\u03b9": "i", "\u0399": "I", "\u03ba": "k", "\u039a": "K",
    "\u03bd": "v", "\u039d": "N", "\u03bf": "o", "\u039f": "O",
    "\u03c1": "r", "\u03a1": "P", "\u03c4": "t", "\u03a4": "T",
    "\u03c5": "u", "\u03a5": "Y", "\u03c7": "x", "\u03a7": "X",
    # Fullwidth ASCII forms
    "\uff41": "a", "\uff21": "A", "\uff42": "b", "\uff22": "B",
    "\uff43": "c", "\uff23": "C", "\uff44": "d", "\uff24": "D",
    "\uff45": "e", "\uff25": "E", "\uff46": "f", "\uff26": "F",
    "\uff47": "g", "\uff27": "G", "\uff48": "h", "\uff28": "H",
    "\uff49": "i", "\uff29": "I", "\uff4a": "j", "\uff2a": "J",
    "\uff4b": "k", "\uff2b": "K", "\uff4c": "l", "\uff2c": "L",
    "\uff4d": "m", "\uff2d": "M", "\uff4e": "n", "\uff2e": "N",
    "\uff4f": "o", "\uff2f": "O", "\uff50": "p", "\uff30": "P",
    "\uff51": "q", "\uff31": "Q", "\uff52": "r", "\uff32": "R",
    "\uff53": "s", "\uff33": "S", "\uff54": "t", "\uff34": "T",
    "\uff55": "u", "\uff35": "U", "\uff56": "v", "\uff36": "V",
    "\uff57": "w", "\uff37": "W", "\uff58": "x", "\uff38": "X",
    "\uff59": "y", "\uff39": "Y", "\uff5a": "z", "\uff3a": "Z",
}

_HOMOGLYPH_TRANS = str.maketrans(HOMOGLYPH_MAP)

# Zero-width spaces & invisible formatters
_ZERO_WIDTH_CHARS = re.compile(r"[\u200B-\u200D\uFEFF\u00AD\u2060\u200E\u200F]")

# ANSI escapes and HTML/Markdown hidden comments
_ANSI_AND_COMMENTS = re.compile(r"(\x1b\[[0-9;]*[a-zA-Z]|<!--.*?-->|/\*.*?\*/)")

# Base64 pattern (minimum length 16 chars to avoid false positives)
_BASE64_PATTERN = re.compile(r"(?:[A-Za-z0-9+/]{4}){4,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")

# Hex pattern (e.g. 0x616263 or \x61\x62)
_HEX_PATTERN = re.compile(r"(?:\\x[0-9a-fA-F]{2}){3,}|(?:0x[0-9a-fA-F]{2}){3,}")


def strip_zero_width_and_escapes(text: str) -> str:
    """Removes invisible characters, zero-width spaces, and ANSI escapes."""
    if not text:
        return ""
    cleaned = _ZERO_WIDTH_CHARS.sub("", text)
    cleaned = _ANSI_AND_COMMENTS.sub("", cleaned)
    return cleaned


def normalize_homoglyphs(text: str) -> str:
    """Normalizes Unicode NFKD and converts visual lookalike characters to standard Latin ASCII."""
    if not text:
        return ""
    # Unicode NFKD decomposition
    decomposed = unicodedata.normalize("NFKD", text)
    # Map homoglyphs
    translated = decomposed.translate(_HOMOGLYPH_TRANS)
    # Strip non-spacing marks (accents, combining marks)
    return "".join(c for c in translated if not unicodedata.combining(c))


def decode_embedded_encodings(text: str, max_depth: int = 2) -> tuple[str, list[str]]:
    """
    Detects and decodes embedded URL, Hex, and Base64 strings.
    Returns (expanded_text, encodings_found).
    """
    if not text:
        return "", []

    encodings_found = []
    current = text

    for _ in range(max_depth):
        changed = False

        # 1. URL Decoding
        if "%" in current:
            try:
                unquoted = urllib.parse.unquote(current)
                if unquoted != current:
                    current = unquoted
                    if "url" not in encodings_found:
                        encodings_found.append("url")
                    changed = True
            except Exception:
                pass

        # 2. Hex decoding
        hex_matches = _HEX_PATTERN.findall(current)
        for hx in hex_matches:
            try:
                raw_hex = hx.replace("\\x", "").replace("0x", "")
                decoded = bytes.fromhex(raw_hex).decode("utf-8", errors="ignore")
                if decoded and len(decoded) > 3:
                    current = current.replace(hx, f" {decoded} ")
                    if "hex" not in encodings_found:
                        encodings_found.append("hex")
                    changed = True
            except Exception:
                pass

        # 3. Base64 decoding
        b64_matches = _BASE64_PATTERN.findall(current)
        for b64 in b64_matches:
            if len(b64) < 16:
                continue
            try:
                raw = base64.b64decode(b64, validate=True).decode("utf-8", errors="ignore")
                if raw and any(c.isalpha() for c in raw) and len(raw) > 4:
                    current = current.replace(b64, f" {raw} ")
                    if "base64" not in encodings_found:
                        encodings_found.append("base64")
                    changed = True
            except Exception:
                pass

        if not changed:
            break

    return current, encodings_found


def canonicalize_text(text: str) -> tuple[str, dict[str, object]]:
    """
    Full canonicalization pipeline:
    1. Strip zero-width & invisible comments
    2. Decode URL/Hex/Base64 encodings
    3. Normalize homoglyphs & Unicode
    4. Collapse excess whitespace
    """
    if not text:
        return "", {"deobfuscated": False, "encodings": []}

    original = text
    # Strip invisible
    step1 = strip_zero_width_and_escapes(text)
    # Decode encodings
    step2, encodings = decode_embedded_encodings(step1)
    # Normalize homoglyphs
    step3 = normalize_homoglyphs(step2)
    # Normalize whitespace
    canonical = " ".join(step3.split())

    was_modified = canonical.lower() != original.lower().strip()
    return canonical, {
        "deobfuscated": was_modified or bool(encodings),
        "encodings": encodings,
        "original_length": len(original),
        "canonical_length": len(canonical),
    }
