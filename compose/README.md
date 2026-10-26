# 수동 작곡 도우미 — 당신이 치고, 제가 주변을 만듭니다

멜로디는 당신 것입니다. 이 폴더의 도구는 **반주 후보만 제안**하고, 무엇을 쓸지는 당신이 고릅니다.

## 한 줄 사용법

```bash
python compose/compose.py 내피아노.mid --out work/곡1
```

끝나면 `work/곡1/읽어보기.txt` 를 여세요.

## 나오는 것

| 폴더 | 내용 |
|---|---|
| `01_당신파트/` | 당신이 준 MIDI 원본 (절대 수정 안 함) |
| `02_악기후보/` | 당신 파트를 여러 악기로 바꿔 렌더한 MP3 + MIDI. **양손을 나눠서** 윗선율·아랫화음 각각 추천 |
| `03_반주후보/` | 드럼 A/B/C · 베이스 A/B/C · 패드. 전부 **당신 파트와 섞어서** 들려줌 |
| `04_합본/` | 전체 데모 한 개 |
| `읽어보기.txt` | 조성·스케일·마디별 코드·악기 추천·다음 할 일 |
| `리포트.json` | 같은 내용의 기계 판독용 |

## 옵션

```bash
--tempo 92              # MIDI의 BPM이 틀릴 때 직접 지정
--beats-per-bar 3       # 3박자 곡
--melody-instrument strings   # 당신 파트를 이 악기로 미리듣기에 사용
--no-render             # 오디오 없이 MIDI만 (빠름)
```

악기 이름 목록은 `compose/midi_theory.py` 의 `GM` 사전에 있습니다
(strings, nylon_guitar, flute, violin, cello, alto_sax, warm_pad, rhodes, vibraphone ...).

## 필요한 것

- Python: `numpy scipy soundfile pretty_midi mido`
- 오디오 렌더: `fluidsynth` + General MIDI 사운드폰트
  - Ubuntu/Debian: `sudo apt install fluidsynth fluid-soundfont-gm`
  - Windows: [FluidSynth 릴리스](https://github.com/FluidSynth/fluidsynth/releases) + [GeneralUser GS](https://schristiancollins.com/generaluser.php)
  - 다른 사운드폰트를 쓰려면 `GM_SOUNDFONT` 환경변수로 경로 지정
- MP3 변환: `ffmpeg` (없으면 WAV로 남습니다)

## 설계 원칙

- 당신이 준 파일은 읽기만 하고 절대 덮어쓰지 않습니다.
- 코드·조성 추정은 **자동이라 틀릴 수 있습니다**. 리포트가 그렇게 명시합니다.
- 반주 후보는 확정되지 않습니다. 고르는 것이 당신의 창작 결정이고, 그 기록이 남습니다.
- 멜로디를 대신 만들어 주지 않습니다. 그래야 곡이 당신 것입니다.

## 풍성하게 만들기 (.song 기반)

`musicx.py` — Studio One `.song` 안의 `Performances/*.musicx` 바이너리를 읽어
트랙별 노트를 꺼낸다. 문서화되지 않은 포맷이라 리버스 엔지니어링한 것이고,
시간 단위 해석에는 불확실성이 남아 있다 (`notes(beats_per_whole=...)`).

`enrich.py` — 이미 연주된 음에서만 파생 레이어를 만든다.
`octave()` 는 옥타브 복제, `chord_bed()` 는 당신이 친 화음의 구성음만 길게
늘인 패드. 새로 만드는 것은 `drum_pattern()` (드럼) 뿐이다. 멜로디는
만들지 않는다 — 그건 당신 몫이다.

`master_simple.py` — 20 Hz 하이패스 → 사이드 폭 조절 → EBU R128 측정 →
4× 오버샘플 트루피크 리미터. 측정은 4×, 게인 커브는 원본 샘플레이트에 적용.

`analysis/enrich_run.py` — 위 세 모듈을 묶어 실제로 돌린 스크립트.
`python3 analysis/enrich_run.py <1안.mid 가 있는 폴더>`

결과 리포트: `analysis/master_report_rich.json`
결과 MIDI: `out/풍성한버전.mid`
설명 페이지: `../docs/풍성하게.html`
