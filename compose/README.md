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
