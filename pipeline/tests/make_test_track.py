"""파이프라인 검증용 합성 테스트 곡 생성 (Ebm, 112 BPM, 약 2분).

사용자의 실제 원곡(Suno 파생 WAV)은 이 저장소에 없습니다.
파이프라인이 끝까지 도는지 확인하려고 만든 '가짜 원곡'이며, 저작권 이슈가 없는 합성음입니다.
구성: 보컬 유사 리드 + 패드 + 베이스 + 드럼, 섹션(intro/verse/chorus/verse/chorus/outro).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stayfade import synth  # noqa: E402
from stayfade.common import save_wav  # noqa: E402

SR = 44100
BPM = 112.0
SPB = 60.0 / BPM
BAR = SPB * 4
TONIC = 3  # Eb
SCALE = [0, 2, 3, 5, 7, 8, 10]
PROG = [(0, "m"), (8, ""), (3, ""), (10, "")]  # i - VI - III - VII


def bars(n, start=0.0):
    return [(start + i * BAR, start + (i + 1) * BAR) for i in range(n)]


def chord_notes(deg, qual, octave=4):
    root = 12 * (octave + 1) + (TONIC + deg) % 12
    offs = {"": [0, 4, 7], "m": [0, 3, 7]}[qual]
    return [root + o for o in offs]


def build():
    sections = [("intro", 4, 0.35), ("verse", 8, 0.7), ("chorus", 8, 1.0),
                ("verse", 8, 0.75), ("chorus", 8, 1.0), ("outro", 4, 0.4)]
    total_bars = sum(s[1] for s in sections)
    total = total_bars * BAR + 2.0
    rng = np.random.default_rng(5)
    drums, bass, pad, lead = [], [], [], []
    bi = 0
    for name, nbars, energy in sections:
        for k in range(nbars):
            b0 = bi * BAR
            deg, qual = PROG[bi % len(PROG)]
            step = BAR / 16
            if name != "intro":
                for i in [0, 8] + ([6] if energy > 0.9 else []):
                    drums.append({"start": b0 + i * step + rng.normal(0, .006), "end": b0 + i * step + .12,
                                  "pitch": 36, "velocity": int(105 * energy)})
                for i in [4, 12]:
                    drums.append({"start": b0 + i * step + rng.normal(0, .006), "end": b0 + i * step + .12,
                                  "pitch": 38, "velocity": int(100 * energy)})
                for i in range(0, 16, 2):
                    drums.append({"start": b0 + i * step + rng.normal(0, .005), "end": b0 + i * step + .06,
                                  "pitch": 42, "velocity": int((70 if i % 4 else 85) * energy)})
            root = 12 * 3 + (TONIC + deg) % 12
            for i in [0, 6, 10]:
                bass.append({"start": b0 + i * step, "end": b0 + i * step + step * 3,
                             "pitch": root, "velocity": int(100 * energy)})
            for p in chord_notes(deg, qual):
                pad.append({"start": b0, "end": b0 + BAR * .98, "pitch": p, "velocity": int(62 * energy)})
            if name in ("verse", "chorus"):
                degs = [0, 2, 4, 3] if name == "verse" else [4, 5, 4, 2]
                for j, d in enumerate(degs):
                    octv = 5 if name == "chorus" else 4
                    pitch = 12 * (octv + 1) + (TONIC + SCALE[(d + (bi % 2)) % 7]) % 12
                    st = b0 + j * SPB + rng.normal(0, .01)
                    lead.append({"start": st, "end": st + SPB * .8, "pitch": pitch,
                                 "velocity": int(96 * energy)})
            bi += 1
    layers = {
        "drums": synth.render_events(drums, SR, total, drums=True),
        "bass": synth.render_events(bass, SR, total, preset="bass") * 0.9,
        "pad": synth.render_events(pad, SR, total, preset="pad_warm") * 0.8,
        "lead": synth.render_events(lead, SR, total, preset="voice_like") * 1.0,
    }
    mix = np.zeros((2, int(total * SR)), dtype=np.float32)
    for y in layers.values():
        n = min(y.shape[1], mix.shape[1])
        mix[:, :n] += y[:, :n]
    mix = synth.soft_clip(mix, 1.2)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    return mix, layers, total_bars


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/-/work/testtrack_Ebm_112.wav")
    mix, layers, nbars = build()
    save_wav(out, mix, SR, subtype="PCM_24")
    print(f"{out}  {mix.shape[1]/SR:.2f}s  bars={nbars}  bpm={BPM}  key=Ebm")
