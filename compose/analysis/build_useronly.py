# -*- coding: utf-8 -*-
"""A version with ONLY the composer's own draft: no added layers, no corrected notes, no staccato cut.

python3 build_useronly.py <their 1안 .mid> <out folder>

Their draft MIDI was exported at a default 120 BPM, but the Studio One song is 140 BPM and the note starts are beat
positions, so the times are rescaled by 120/140. Tracks keep exactly their notes and lengths. The patches are the ones
that fit the sounds they chose: a violin for the two STRING tracks, a piano for the chords, a contrabass for the bass.
"""
import os, sys, subprocess, json
import numpy as np, pretty_midi, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import master_simple as M
from compose import render

SRC, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
pm = pretty_midi.PrettyMIDI(SRC); t0 = float(pm.get_tempo_changes()[1][0]); K = t0 / 140.0
PROG = {0: 43, 1: 43, 2: 40, 3: 40, 4: 0}        # held low C2, bass, STRING, STRING 2, piano
out = pretty_midi.PrettyMIDI(initial_tempo=140.0); n_notes = 0
for i, inst in enumerate(pm.instruments):
    j = pretty_midi.Instrument(program=PROG.get(i, 0), name=["Low C2 (yours)", "Bass (yours)", "STRING (yours)", "STRING 2 (yours)", "Piano chords (yours)"][i])
    for n in inst.notes:
        j.notes.append(pretty_midi.Note(n.velocity, n.pitch, n.start * K, n.end * K)); n_notes += 1
    out.instruments.append(j)
mid = f"{OUT}/useronly_140bpm.mid"; out.write(mid)
raw = render(mid, f"{OUT}/useronly_raw.wav", gain=0.75)
rep = M.master(raw, f"{OUT}/useronly_master.wav", target_lufs=-14.0)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/useronly_master.wav", "-ac", "2", "-b:a", "128k", f"{OUT}/useronly.mp3"], check=True)
os.remove(raw)
print(f"{n_notes} notes (all theirs), {out.get_end_time():.1f} s, {rep['after']['lufs']:+.2f} LUFS, tp {rep['after']['true_peak']:+.2f}")
