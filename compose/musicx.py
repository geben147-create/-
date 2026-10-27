# -*- coding: utf-8 -*-
"""Studio One .musicx performance reader.

The format is a small tagged binary tree, not documented by the vendor; this reader was
derived by inspecting real files. Grammar:
    '{' ... '}'   object        '[' ... ']'   array
    'i' <len:u8> <utf8 bytes>   string (used for keys)
    'i' <u8>                    small integer value (0-127); 'U' <u8> for 128-255; 'I' <int16> above that
    'S' 'i' <len:u8> <utf8>      string used as a value
    'D' <8 bytes>               IEEE-754 double, big-endian
A key is always a string; the token after it is its value, so the parser only has to know
whether it is expecting a key or a value. Note objects carry start, pitch, noteId, length
and velocity. Positions and lengths are in whole-note units (1.0 = one whole note = 4
beats), and velocity is 0..1.
"""
from __future__ import annotations
import struct, zipfile, os


class _R:
    def __init__(self, b: bytes):
        self.b = b; self.i = 0
    def u8(self):
        v = self.b[self.i]; self.i += 1; return v
    def eof(self):
        return self.i >= len(self.b)


def _value(r: _R):
    t = r.b[r.i]
    if t == 0x7B:   # {
        r.i += 1; return _obj(r)
    if t == 0x5B:   # [
        r.i += 1
        out = []
        while not r.eof() and r.b[r.i] != 0x5D:
            out.append(_value(r))
        if not r.eof():
            r.i += 1
        return out
    if t == 0x44:   # D
        r.i += 1
        v = struct.unpack(">d", r.b[r.i:r.i + 8])[0]; r.i += 8; return v
    if t == 0x69:   # i  -> small int value (0-127)
        r.i += 1; return r.u8()
    if t == 0x55:   # U  -> uint8 (128-255)
        r.i += 1; return r.u8()
    if t == 0x49:   # I  -> int16, big-endian (note ids above 255)
        r.i += 1; v = struct.unpack(">h", r.b[r.i:r.i + 2])[0]; r.i += 2; return v
    if t == 0x53:   # S  -> string used as a VALUE: 'S' 'i' <len:u8> <utf8>
        r.i += 1; r.i += 1; n = r.u8()
        v = r.b[r.i:r.i + n].decode("utf-8", "replace"); r.i += n; return v
    raise ValueError(f"unknown .musicx token {t:#x} at {r.i}")   # never skip silently: that undercounted notes


def _key(r: _R):
    if r.eof() or r.b[r.i] != 0x69:
        return None
    r.i += 1
    n = r.u8()
    s = r.b[r.i:r.i + n].decode("utf-8", "replace"); r.i += n
    return s


def _obj(r: _R):
    d = {}
    while not r.eof() and r.b[r.i] != 0x7D:
        k = _key(r)
        if k is None:
            break
        d[k] = _value(r)
    if not r.eof():
        r.i += 1
    return d


def parse(data: bytes) -> dict:
    r = _R(data)
    if not r.eof() and r.b[r.i] == 0x7B:
        r.i += 1
        return _obj(r)
    return {}


def notes(data: bytes, beats_per_whole: float = 4.0) -> list[dict]:
    """Return notes with positions converted to beats."""
    d = parse(data)
    out = []
    for e in d.get("events", []) or []:
        if not isinstance(e, dict) or "pitch" not in e:
            continue
        out.append({
            "start_beats": float(e.get("start", 0.0)) * beats_per_whole,
            "length_beats": float(e.get("length", 0.0)) * beats_per_whole,
            "pitch": int(e["pitch"]),
            "velocity": float(e.get("velocity", 0.8)),
        })
    out.sort(key=lambda n: (n["start_beats"], n["pitch"]))
    return out


def read_song(song_path: str) -> dict[str, list[dict]]:
    """Every performance in a .song, keyed by its path inside the archive."""
    z = zipfile.ZipFile(song_path)
    out = {}
    for n in z.namelist():
        if n.endswith(".musicx"):
            try:
                out[n] = notes(z.read(n))
            except Exception as e:
                out[n] = []
    return out
