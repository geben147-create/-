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

## 세 가지 저음 (화음 교정 + 드럼 제거)

`rebuild3.py` — draft 를 고치는 모듈. 고치는 것은 네 가지뿐이고, 전부
"이미 연주된 음을 옮기거나 지우는" 범위 안에 있다.

- `square_loop()` 둘째 바퀴가 0.7초 일찍 들어와 4번째 블록이 3.25초였던 것을 4.0초로
- `snap_early()` 마디선보다 먼저 들어온 음을 마디선에 붙임
- `fix_piano_block3()` 피아노 C major vs STRING F major 충돌 — 피아노를 F/C 로 (두 음)
- `unmask_bass()` 베이스가 피아노 맨 아래 음과 완전 유니즌이라 안 들리던 것 —
  피아노의 중복 음을 제거해 베이스에게 그 음역을 넘김
- `pedal_to_roots()` C2 하나로 고정된 저음을, 연주된 각 화음의 루트로

새로 만드는 것은 `pulse()` (당신 음고에 리듬만) 와 `choir()` (당신 화음의
구성음만) 둘뿐이다. 드럼은 없다. 멜로디는 쓰지 않는다.

`analysis/build3_run.py` — 세 버전을 만들고 마스터링한다.
`analysis/build3_page.py` — 미리 듣기 페이지를 만든다.

검증 (둘 다 실제로 출고된 파일 위에서 돌린다):
- `analysis/verify_collisions.py` 트랙끼리 반음·단9도로 겹치는 구간을 센다.
  draft 227 → 40 (남은 40개는 전부 블록 4의 A♯4 ♭9 하나, 일부러 남긴 것)
- `analysis/verify_masking.py` 베이스 트랙을 빼고 다시 렌더해서 95–190 Hz 가
  얼마나 줄어드는지 잰다. 이전 버전 +0.86 dB (사실상 안 들림) → +5.08 dB

결과: `out/v3/*.mid`, 리포트 `analysis/report_v3.json`,
페이지 `../docs/세가지저음.html`

## 오케스트라 세 편성 (v4)

`orchestra.py` — 드럼 킷도 신스 펄스도 쓰지 않고 오케스트라 악기로만 움직임을 만든다.

- `straighten_block4()` 마지막 블록만 8분음표 격자에서 벗어나 있고 16음이 아니라
  15음이었다. 연주된 음 순서를 그대로 격자에 올리고, 작곡자 자신이 만든
  4음 묶음 패턴을 완성하는 C#5 한 개만 채운다. 선율에 더해진 음은 그것뿐.
- `fill_blocks()` 눌린 긴 음이 블록 끝까지 못 가고 끊기던 것 (베이스는 1블록의
  49%만 울리고 2초가 비었다) 을 길이만 늘려 메운다.
- `horn_voicing_block4()` A#4(♭9) 밑에 루트 A3가 깔려 단9도로 부딪히던 것 —
  A#는 두고 루트를 G3로. 한 음으로 A7의 7음까지 생긴다.
- `tremolo()` / `pizzicato()` / `timpani()` / `glock()` 더하는 색. 전부
  작곡자가 친 화음의 구성음이고, 새로 만드는 것은 리듬과 음색뿐.
- `hall_ir()` 합성 콘서트홀 — 초기 반사 6개 + 주파수별 감쇠 (저 2.6s / 중 2.1s /
  고 1.0s). 총 에너지 1로 정규화해서 잔향이 음량을 바꾸지 않는다.
- `render_stem()` / `seat()` / `mix()` 악기마다 따로 렌더해서 정위상 팬으로
  무대에 앉히고, 뒤쪽 악기일수록 홀 센드를 많이 준다.

`master_simple.shelf()` 고역 셸프 (air). 심벌이 빠지면 8 kHz 위가 비므로 약간만.

검증 (`analysis/verify_v4.py`, 출고 파일 위에서):
- 반음/단9도 충돌 **0** (draft 227 → v3 40 → v4 0)
- 멜로디 대역 500–1000 Hz **28.0%** (처음 8.8%)
- 콘트라베이스 기여도 **+16.1 dB** (처음 +0.86 dB)
- 크레스트 15.2 dB, 클리핑 0, −14.00 LUFS / −1.0 dBTP
- 각 레이어의 기여도는 그 레이어만 빼고 다시 믹스해서 잰다 (`layer_worth_db`).
  희소한 벨은 전체 RMS로는 안 잡히므로 가장 큰 0.2초 구간도 같이 본다.

결과: `out/v4/*.mid`, `analysis/report_v4.json`, `../docs/오케스트라.html`

## 점층 오케스트라 (v5, 10블록 + 마지막 화음)

`finale.py` + `analysis/build5_run.py` — 140 BPM(.song의 실제 템포) 기준, 단위는 박(beat), 1블록 = 8박.

- 블록 1–4: 당신 파트 + 저음 현악 베드. 블록 5: 첼로 오스티나토 입장. 블록 6: 저음 프렌치 호른.
  블록 7: 팀파니. 블록 8: 호른 스웰(CC11)로 다음 블록을 밀어 올림.
- 블록 9 (추가): 드라이빙 시네마틱 록 마디. 드럼 킷 대신 팀파니(킥 자리)·타이코(백비트 자리)·저음 현악 8분음표.
- 블록 10 (추가): 최종 합창. 바이올린 옥타브, 트롬본·호른 스웰, 리버스 심벌, 팀파니 롤 후 6박째에
  D minor 마지막 화음을 8박 유지.
- 지난번 "착착착" 고음 트레몰로와 24연타 팀파니 롤은 삭제.
- 블록 9·10은 당신의 블록 1 음형을 그대로 반복한다. 새 선율은 쓰지 않는다.
- 페이더는 추측하지 않고 측정으로 맞춘다 (`AUTO` 표: 스템을 유닛 게인으로 렌더 → 해당 구간 RMS 측정 → 목표까지의 게인).
  추측으로 놓았을 때 바이올린 II가 I보다 20 dB 작았고 합창은 −54 dB로 안 들렸다.

검증 (`analysis/verify_v5.py`): 반음/단9도 충돌 0, 당신 바이올린·베이스 블록 1–8 노트 전부 동일,
믹스 안에서 측정한 당신 베이스 기여도 +4.7 dB (저음 호른·베드가 베이스 음역을 덮던 것을 한 옥타브 올려서 해결).
결과: `out/progressive/`, 리포트 `analysis/report_v5.json`
