# 무료 오케스트라 악기 조사 (Studio One / Fender Studio Pro 8, Windows)

작성일: 2026-10-27

## 0. 조사 한계 (먼저 읽을 것)

이 조사 환경은 네트워크 정책 때문에 공식 사이트에 접속하지 못했다. 직접 열어서 확인한 곳은 GitHub 페이지뿐이다.

- 접속이 막힌 공식 사이트(CONNECT 403 또는 DNS 실패): spitfireaudio.com, labs.spitfireaudio.com, plogue.com, sfz.tools, musescore.org, presonus.com, vis.versilstudios.com, wikipedia.org
- 아래 표의 "검증 수준" 열에서 **[GitHub 직접]** 은 실제로 페이지를 열어 확인한 항목이고, **[검색 요약]** 은 웹 검색 결과 요약에서 가져온 2차 정보다. 후자는 공식 확인이 아니다.
- 사용자에게는 설치 전에 각 공식 페이지에서 이름, 가격, 용량을 한 번 더 확인하라고 안내해야 한다.

---

## 1. 추천 Top 3 (이 사용자 기준)

사용자는 피아노 MIDI를 호른/첼로 등으로 바꿔 듣고 싶어 한다. 또 내가 만든 GM 멀티트랙 .mid를 열어야 한다. 이 두 조건에 맞춰 골랐다.

### 1위. Spitfire BBC Symphony Orchestra Discover (주 악기)
- 이유: 현악, 목관, 금관, 타악이 들어 있는 무료 오케스트라 플러그인이다. VST/AU/AAX 형식이라 Studio One에서 별도 호스트 없이 쓸 수 있다고 한다. 다만 아래 단계 중 공식 문서로 확인한 것은 없다. 모두 [검색 요약] 기반이다.
- 주의: 합창(choir)이 들어 있는지는 확인하지 못했다. 호른, 트롬본, 팀파니, 바이올린, 비올라, 첼로, 콘트라베이스, 글로켄슈필 개별 포함 여부도 공식 목록으로 확인하지 못했다.

설치와 사용 5단계 (확인 수준: 낮음, 공식 문서 미확인):
1. spitfireaudio.com에서 BBC Symphony Orchestra Discover 페이지를 열고 무료 다운로드를 받는다. 계정 가입 필요 여부는 확인하지 못했다.
2. Spitfire 앱(또는 설치 프로그램)으로 설치한다. 용량은 약 200~240MB라는 보도가 있다.
3. Studio One을 열고 Options > Locations > VST Plug-Ins에서 플러그인 폴더를 다시 스캔한다. (VST3 기본 폴더는 `C:\Program Files\Common Files\VST3`라는 포럼 글이 있다. 공식 문서는 아니다.)
4. 악기 트랙을 만들어 BBCSO Discover를 선택하고, 피아노 MIDI 트랙의 출력을 그 악기로 바꾼다.
5. 악기 안에서 호른, 첼로 등을 고르고 MIDI의 음역에 맞게 옥타브를 조정한다.

### 2위. Plogue sforzando + VSCO 2 CE (SFZ) (무료, 라이선스 가장 분명)
- 이유: VSCO 2 CE는 CC0(퍼블릭 도메인)이라 재배포와 상업 이용에 제약이 가장 적다. 이 점은 GitHub에서 직접 확인했다. sforzando가 Windows에서 VST3로 동작한다는 점은 [검색 요약]이다.
- 단점: sforzando는 악기 슬롯이 1개뿐이다. 트랙이 여러 개면 인스턴스를 여러 개 띄워야 한다.

설치와 사용 5단계 (확인 수준: 중간 이하, 단계 1·2의 sforzando 부분은 공식 확인 못 함):
1. plogue.com/products/sforzando에서 Windows용 sforzando를 받아 설치한다.
2. github.com/sgossner/VSCO-2-CE 의 Releases에서 SFZ 1.1.0을 받는다. (README에 "SFZ version 1.1.0" Quick Download가 있다. 파일 크기는 못 봤다.)
3. 압축을 풀어 영구 폴더(예: `D:\Samples\VSCO-2-CE`)에 둔다.
4. Studio One에서 VST3를 스캔한 뒤 sforzando를 악기 트랙에 올리고, 화면에 SFZ 파일(호른, 첼로 등)을 불러온다.
5. 피아노 MIDI 트랙 출력을 그 트랙으로 바꾼다.

### 3위. SF2 플레이어 VST3 + MuseScore General (GM 멀티트랙 .mid를 한 번에 열기)
- 이유: 내가 만든 GM 프로그램 번호 기반 멀티트랙 .mid를 그대로 재생하려면 GM SoundFont가 가장 간단하다. MuseScore General은 MIT 라이선스라는 보도가 있다 (공식 페이지 미확인).
- 후보 플레이어: Bertom Audio SF2 Player(VST3, Windows, 무료 또는 pay-what-you-want), SFLT(2025, VST3/CLAP, GPLv3, Windows). 모두 [검색 요약]이며 Studio One에서 동작하는지는 확인하지 못했다.
- 단점: 플레이어 하나가 SF2 하나를 로드하므로 .mid의 트랙마다 인스턴스가 필요한 제품이 많다. 멀티팀브럴 지원 여부는 확인하지 못했다. 이 경우 다음 절 "AI가 할 수 있는 일"처럼 내가 FluidSynth로 렌더한 스템을 주는 편이 실용적이다.

설치와 사용 5단계 (확인 수준: 낮음):
1. MuseScore General SF2(약 208MB, SF3는 약 36MB라는 핸드북 요약이 있음)를 받는다. 대부분의 DAW 플러그인은 SF3를 못 읽을 수 있으므로 SF2를 받는다. SF3 지원 여부는 확인하지 못했다.
2. SF2 플레이어 VST3를 설치한다.
3. Studio One에서 VST3 스캔 후 악기 트랙에 플레이어를 올린다.
4. 플레이어에 SF2를 로드하고 프로그램 번호(호른=60, 첼로=42 등 GM)를 선택한다.
5. MIDI 트랙 출력을 이 트랙으로 보낸다.

---

## 2. 질문에 대한 답

### (1) 피아노 MIDI를 호른/첼로로 듣는 가장 쉬운 길
MIDI는 소리가 아니라 음표 데이터이므로 "변환"이 아니다. **MIDI 트랙의 출력 악기만 바꾸면 된다.** 피아노 트랙을 호른 샘플러로 연결하면 같은 음표가 호른 소리로 난다. 다만 아래를 감안해야 한다.
- 음역: 호른이나 첼로의 실제 음역을 벗어나면 어색하다. 옥타브 이동이 필요할 수 있다.
- 피아노 연주를 그대로 보내면 화음이 많고 페달 길이가 달라 관악기·현악기답지 않다. 레가토나 키스위치(아티큘레이션) 선택이 필요하다.
- 오디오를 MIDI로 바꾸거나 소리를 다른 악기로 바꾸는 "음색 변환"은 이 문제와 다른 기술이며 이 조사에서 다루지 않았다.

### (2) AI(나)가 할 수 있는 것과 없는 것
할 수 있는 것
- 무료 GM SoundFont와 FluidSynth로 .mid를 오디오(WAV)로 렌더해 스템(트랙별 오디오)을 주는 것. 사용자는 플러그인 설치 없이 Studio One에 오디오로 불러올 수 있다.
- 사용자가 선택한 악기에 맞춘 MIDI(음역 조정, 옥타브 이동, 벨로시티 정리, 트랙 분리)를 만드는 것.

할 수 없는 것
- 새 샘플 악기 라이브러리를 만드는 것. 샘플은 실제 연주를 녹음해야 하므로 나는 만들 수 없다.

"악기를 만든다"고 말할 수 있는 정직한 범위
- 기존 SF2에서 필요한 프리셋(호른, 첼로 등)만 잘라 작은 SF2로 묶어주는 정도는 기술적으로 가능하다 (예: Polyphone 같은 편집 도구, 이 도구의 동작은 이번에 확인하지 못했다). 이것은 새 악기가 아니라 기존 악기의 재구성이다.
- 이 경우 원본 라이선스 조건을 따라야 한다.

재배포 라이선스
- MuseScore General: MIT라는 보도가 있다 (공식 페이지 미확인). MIT라면 저작권 고지와 라이선스 문구를 함께 넣으면 재배포가 가능하다.
- FluidR3_GM: 라이선스 문구를 이번에 확인하지 못했다. 일반적으로 알려진 바(기억)로는 MIT 계열이라고 하지만 **확인하지 못했으므로 재배포 전에 반드시 원문을 확인해야 한다.**
- VSCO 2 CE, VCSL: CC0 (GitHub에서 직접 확인).
- Sonatina Symphonic Orchestra: Creative Commons Sampling Plus 1.0이라는 보도가 있다 (검색 요약). 이 라이선스 조건의 세부 내용은 확인하지 못했다.
- 결론: 재배포가 필요하면 CC0인 VSCO 2 CE가 가장 안전하다. 그 외는 원문 확인이 먼저다.

---

## 3. 후보 표

| 이름 | 포함 악기(요구 목록 기준) | 형식 | 라이선스/가격 | 용량 | Windows | Studio One 사용 | 검증 수준 | 열어 본 URL |
|---|---|---|---|---|---|---|---|---|
| Spitfire LABS | 확인 못함. 피아노, 스트링, 패드, 합창 등이 있다는 보도만 있음. 개별 호른/트롬본/팀파니 등은 확인 못함 | VST2/VST3/AU/AAX (일부 LABS 제품 기준 보도) | 무료 팩과 유료 LABS+ 혼재(보도). 가입 필요 여부 확인 못함 | 팩마다 다름, 확인 못함 | 보도상 지원 | VST3 스캔으로 가능할 것으로 보이나 미확인 | [검색 요약], 공식 접속 실패 | 접속 실패: https://labs.spitfireaudio.com/ |
| Spitfire BBC Symphony Orchestra Discover | 현악, 목관, 금관, 타악 약 33~34종(보도). 호른/트롬본/팀파니/바이올린/비올라/첼로/콘트라베이스/합창/글로켄슈필 개별 확인 못함 | VST/AU/AAX(보도) | 무료(보도: 즉시 무료 다운로드). 계정 필요 여부 확인 못함 | 약 200~240MB(출처마다 다름) | 보도상 지원 | 가능할 것으로 보이나 미확인 | [검색 요약] | 접속 실패: https://www.spitfireaudio.com/bbc-symphony-orchestra-discover |
| VSCO 2 CE (Versilian Studios Community Orchestra 2) | 폴더 구성이 Brass, Keys, Percussion, Strings, Woodwinds라는 것만 확인. 개별 악기 확인 못함 | SFZ (v1.1.0, GitHub 확인). Kontakt 버전은 확인 못함 | CC0-1.0 (GitHub 확인), 무료 | 확인 못함 | 파일 기반이라 OS 무관, 플레이어는 별도 | sforzando 등 SFZ 플레이어 필요. Studio One 자체로는 SFZ 로드 확인 못함 | [GitHub 직접] | https://github.com/sgossner/VSCO-2-CE |
| VCSL (Versilian Community Sample Library) | 아에로폰, 코드로폰, 이디오폰, 멤브라노폰 분류. 개별 악기 확인 못함 | WAV 원본 + SFZ(Releases) | CC0 1.0 (GitHub 확인) | 악기당 대체로 20~75MB(README) | OS 무관 | SFZ 플레이어 필요 | [GitHub 직접] | https://github.com/sgossner/VCSL |
| Sonatina Symphonic Orchestra | 확인 못함 | SFZ + 16bit WAV(보도) | Creative Commons Sampling Plus 1.0(보도). 무료 | 약 440MB(2011년 보도), 현재 용량 확인 못함 | 파일 기반 | sforzando 등 필요 | [검색 요약]. GitHub URL은 404였고 현재 공식 배포처 확인 못함 | 404: https://github.com/sfzinstruments/sso.sfz |
| Virtual Playing Orchestra | 확인 못함 | SFZ (WAV + SFZ 스크립트 별도 다운로드, 보도) | 로열티 프리(보도), 원문 확인 못함. 일부 샘플은 다른 라이브러리 약관을 따를 수 있음 | 확인 못함 | 파일 기반 | sforzando 또는 sfizz 필요(보도) | [검색 요약]. GitHub URL은 404 | 404: https://github.com/sfzinstruments/virtual-playing-orchestra |
| MuseScore General SoundFont | GM 128 프로그램 전체(GM 구성상). 직접 확인 못함 | SF2 / SF3 | MIT(핸드북 요약, 공식 미확인), 무료 | SF3 약 36MB, SF2 약 208MB(검색 요약) | 파일 기반 | SF2 플레이어 VST3 필요(아래 참조) | [검색 요약]. GitHub URL은 404, 공식 페이지 접속 실패 | 404: https://github.com/musescore/MuseScore_General / 접속 실패: https://musescore.org/en/handbook/4/soundfonts-and-sfz-files |
| FluidR3_GM | GM 전체(구성상) | SF2 | 확인 못함 | 확인 못함 | 파일 기반 | SF2 플레이어 필요 | 미확인 | 열지 못함 |
| Plogue sforzando | 악기 없음(SFZ 플레이어) | VST3, 스탠드얼론. 과거에는 VST2도 있었음(보도). 현재 목록은 확인 못함 | 무료(보도) | 확인 못함 | Windows 10 x64 이상(보도) | VST3 스캔으로 가능할 것으로 보이나 미확인. SF2, DLS를 SFZ로 변환해 읽는다는 보도 있음 | [검색 요약], 공식 접속 실패 | 접속 실패: https://www.plogue.com/products/sforzando.html |
| sfizz | 악기 없음(SFZ 샘플러) | 라이브러리는 sfizz 저장소. VST3, AU, LV2, Pure Data 플러그인은 sfizz-ui 저장소(GitHub 확인). SF2 지원은 README에 언급 없음 | BSD-2-Clause(GitHub 확인), 무료 | 확인 못함 | 릴리스에서 Windows와 Mac용 제공(README) | **두 저장소 모두 2026-06-21에 보관(archived) 처리되어 읽기 전용**. 최신 릴리스 1.2.3(1월 14일, 연도 확인 못함). Windows VST3 파일이 릴리스에 있는지는 확인 못함(자산 목록이 안 열림) | [GitHub 직접] | https://github.com/sfztools/sfizz , https://github.com/sfztools/sfizz-ui , https://github.com/sfztools/sfizz/releases/latest |
| Decent Sampler | 확인 못함 | 확인 못함 | 확인 못함 | 확인 못함 | 확인 못함 | 확인 못함 | **미조사** (공식 접속 불가, 별도 검색 안 함) | 열지 못함 |
| Native Instruments Kontakt Player 무료 라이브러리 | Komplete Start의 Play Series는 신스/패드 위주(보도). 오케스트라는 서드파티 무료 라이브러리(ProjectSAM The Free Orchestra, 약 14패치, 약 1GB 등)가 있다는 보도 | Kontakt Player | 무료(Komplete Start 보도). 계정 필요 여부 확인 못함 | 라이브러리별 상이 | 확인 못함 | Kontakt Player를 VST3로 쓸 수 있는지 확인 못함 | [검색 요약] | 접속 안 함 (검색 결과: https://www.native-instruments.com/blogs/blog/free-kontakt-player-libraries) |
| Orchestral Tools SINE Player 무료 라이브러리 | SINEfactory 15종(보도): 피아노, 스트링, 빅밴드 혼, 플루트, 합창(studio voices), 퍼커션 등. 오케스트라 호른/첼로 개별은 확인 못함 | SINE Player (자체 플레이어) | 무료(보도). 계정 필요 여부 확인 못함 | 확인 못함 | 확인 못함 | 확인 못함 | [검색 요약] | 접속 안 함 (같은 검색 결과 페이지 참조) |
| Studio One 내장 Presence XT | 번들 Sound Set 중 오케스트라 구성 확인 못함. Prime/Artist/Pro 번들에 흔한 사운드가 있고 Pro는 별도 "Presence XT Core Library"가 있다는 책 요약만 있음 | Presence XT 샘플러 | Studio One Prime에 포함(오래된 독일 리뷰). **Fender Studio Pro 8에 포함되는지는 확인 못함** | - | Windows | SF2 로드: 서드파티 안내와 포럼에서 가능하다고 언급, 일부 SF2에서 빈 프리셋 문제 보고(Studio One 5). **SFZ 로드는 어떤 자료에서도 확인 못함** | [검색 요약] | 접속 실패: https://presonus.com/products/studio-one |
| SF2 플레이어 VST3 (Bertom Audio SF2 Player) | 악기 없음 | VST3 (Windows) | 무료 또는 pay-what-you-want(KVR 요약) | 확인 못함 | 예(KVR 요약) | 미확인 | [검색 요약] | 접속 안 함 (https://www.kvraudio.com/product/sf2-player-by-bertom-audio) |
| SF2 플레이어 VST3/CLAP (SFLT) | 악기 없음 | VST3, CLAP, FL Studio 네이티브 | 무료, GPLv3(보도) | 확인 못함 | Windows 전용(보도) | 미확인 | [검색 요약] | 접속 안 함 (https://bedroomproducersblog.com/2025/08/01/sflt-soundfont-player/) |

---

## 4. 확인하지 못한 것

공식 페이지를 열지 못했거나 어떤 자료에서도 확인되지 않은 항목이다.

### 공식 접속 실패로 확인 못함
1. Spitfire LABS에서 무료로 받을 수 있는 오케스트라 악기의 정확한 목록과 형식. 호른, 트롬본, 팀파니, 바이올린, 비올라, 첼로, 콘트라베이스, 합창, 글로켄슈필이 있는지.
2. BBC Symphony Orchestra Discover의 현재 가격(무료 여부), 계정 필요 여부, 정확한 용량, 악기 목록(위 9종 개별 포함 여부, 특히 합창), 지원 형식.
3. Spitfire 제품의 설치 방법(전용 앱 필요 여부).
4. Plogue sforzando의 현재 버전, 지원 형식(VST3 여부), 라이선스 문구, 설치 방법.
5. MuseScore General의 현재 라이선스, 파일 크기, 다운로드 위치(공식 페이지 미열람).
6. FluidR3_GM의 라이선스와 재배포 조건. 기억으로는 MIT 계열이나 확인하지 못했다.
7. Studio One / Fender Studio Pro 8 관련 전부:
   - Presence XT가 Fender Studio Pro 8, Studio One Prime, Artist에 포함되는지(Prime은 오래된 리뷰만 있음).
   - 그 번들에 어떤 오케스트라 콘텐츠가 들어 있는지.
   - Presence XT가 SFZ를 불러올 수 있는지(어떤 자료에도 없음). SF2는 비공식 자료 기준으로만 가능.
   - Studio One 6/7/8에서 VST3 스캔 절차의 공식 문구.
   - Studio One Prime은 서드파티 플러그인을 지원하지 않는다는 오래된 리뷰가 있다. 사용자의 버전이 Prime이 아니면 해당 없다.

### 공식 저장소를 열었으나 비어 있거나 404라서 확인 못함
8. sfizz 저장소의 Windows 자산 목록(VST3 파일 여부)과 SF2 지원 여부. 두 저장소 모두 2026-06-21에 보관되어 앞으로 갱신되지 않는다. 사용자에게 권할 때 이 점을 알려야 한다.
9. VSCO 2 CE의 개별 악기 목록(호른, 트롬본 등)과 다운로드 용량, 최신 릴리스 날짜.
10. VCSL의 개별 악기 목록.
11. Sonatina Symphonic Orchestra의 현재 배포처, 현재 용량, 악기 목록. Creative Commons Sampling Plus 1.0의 세부 조건. 이 저장소 URL은 404였다.
12. Virtual Playing Orchestra의 현재 배포처, 악기 목록, 라이선스 원문. 이 저장소 URL은 404였다. 소개 글에는 virtualplaying.com이 나오지만 열지 못했다.

### 조사하지 않음
13. Decent Sampler의 존재 여부 외 모든 정보(가격, 무료 오케스트라 라이브러리, VST3 지원).
14. Kontakt Player 무료 라이브러리의 현재 목록, Kontakt Player가 Studio One에서 VST3로 동작하는지, NI 계정 필요 여부. ProjectSAM The Free Orchestra의 현재 제공 여부.
15. SINE Player 무료 라이브러리의 현재 구성과 계정 필요 여부.
16. 위 SF2 플레이어들(Bertom Audio SF2 Player, SFLT, DSK SF2)이 Studio One(6/7/8)에서 실제 동작하는지, 멀티팀브럴 지원 여부, SF3 지원 여부.
17. Polyphone 등으로 SF2 일부만 잘라 재패키징하는 구체적 절차와 FluidR3_GM, MuseScore General의 재패키징 허용 범위.
18. 내가 FluidSynth로 렌더할 때의 음질이 사용자가 만족할 수준인지(청음 평가 못함).

### 이 문서의 5단계 안내에 관해
Top 3의 5단계 안내는 **공식 문서에서 검증한 단계가 아니다.** 일반적인 VST3 설치 절차와 2차 자료를 조합한 것이므로 실행 전에 각 공식 안내와 대조해야 한다.

---

## 교차 확인 (부모 세션, 2026-10-27, 웹 검색 요약 기준 — 공식 페이지 직접 확인 아님)

- **Spitfire BBC Symphony Orchestra Discover는 무료**라는 보도가 여러 곳에서 일치한다 (MusicRadar, Rekkerd, MusicTech, Sound On Sound).
  약 200MB, PC/Mac, VST/AU/AAX, 현악·목관·금관·타악 포함, 악기 수는 33~35개로 보도가 엇갈린다.
  **호른·트롬본·첼로·비올라·팀파니가 각각 들어 있는지는 확인하지 못했다.** 설치 전에 공식 제품 페이지에서 악기 목록을 확인할 것.
- **Spitfire LABS의 오케스트라 현악 팩(Symphonic Violins & Violas, Celli & Basses)은 유료(LABS+)로 보인다.**
  금관 무료 팩은 찾지 못했다. LABS는 이 사용자의 호른/첼로 용도로 우선 추천하지 않는다. (바로 위 Top 3 순서와는 별개로, 이 항목은 LABS를 뺀다.)
- **Studio One의 Presence XT 기본 라이브러리**에는 피아노·현악·튜닝 타악·금관·베이스 등이 있다는 리뷰가 있으나, 이는 Studio One 3 시절 글이다.
  Fender Studio Pro 8에 어떤 구성이 들어 있는지는 확인하지 못했다. 오케스트라 전용 `PreSonus Symphonic Orchestra`는 별도 유료 애드온이다.
  Presence XT가 SoundFont를 읽는다는 2차 출처가 하나 있으나 SFZ 지원 근거는 찾지 못했다.
