# 영상 분석 · 제작 플레이북

레퍼런스 영상을 **측정**해서 제작 규칙으로 바꾸는 도구 모음입니다.
특정 주제에 묶여 있지 않습니다 — 장르는 폴더 하나를 갈아끼우면 바뀝니다.

    analysis/VIDEO_ANALYSIS_PLAYBOOK.html   17절 플레이북 (브라우저로 열기)
    pipeline/shotscan.py                    영상 -> 컷·색·모션 측정 + 컨택트 시트
    pipeline/validate.py                    팩 계약 강제 (위반 시 실행 거부)
    packs/genre/<이름>/                     장르마다 갈아끼우는 규칙
    packs/model/model_registry.yaml         능력코드 -> 오늘의 모델 (유일한 모델명 위치)
    packs/voice/voice_cast.json             배역별 목소리 잠금
    schemas/                                shot manifest 스키마 · ID 규칙

## 빠른 시작

    pip install -r pipeline/requirements.txt

    # 1) 레퍼런스 측정 (비공개 저장 목록이면 --cookies-from-browser chrome)
    python pipeline/shotscan.py --urls urls.txt --out ./out

    # 2) 플레이북을 열고 15절에서 out 폴더를 선택
    #    -> 15·16절 표가 측정값으로 채워집니다

    # 3) 대본이 팩 계약을 지키는지 확인
    python pipeline/validate.py --packs
    python pipeline/validate.py --manifest my_shots.json

## 구조

**코어(1~14절)** 는 주제와 무관하게 항상 적용됩니다: 음성이 마스터 클록,
`end_state == 다음 start_state`, 한 컷 한 동작, 비용 게이트, 최종 렌더까지가 완료.

**장르 팩** 은 달라지는 것만 담습니다: 컷 길이, 시선 규칙, 필수 샷, 카메라 어휘, 금지.
6종이 들어 있습니다 — `arch_technical` `documentary` `finance_explainer`
`timeslip_presenter` `comedy_character` `shorts_retention`.
추가는 폴더 복사, 제거는 폴더 삭제.

영상 시작 시 선언 한 줄로 전환됩니다:

    GENRE_PACK   = arch_technical
    CAPABILITIES = [CAP_DIAGRAM_MOTION, CAP_EXACT_NUMERIC]

규칙·프롬프트·대본·manifest에는 **모델 이름을 쓰지 않습니다.** 능력 코드만 쓰고,
실제 모델은 `packs/model/model_registry.yaml` 한 곳에서만 정합니다.

## 15·16절이 비어 있는 이유

측정하지 않은 수치를 문서에 적으면 그럴듯한 거짓말이 됩니다.
`shotscan.py`를 돌려 나온 `index.json`을 불러오면 그 자리가 채워집니다.
검출 방식과 한계는 17절에 적어 두었습니다.
