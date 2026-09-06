# 생성 기록 — 무엇을, 어떤 모델로, 얼마에

이 사이트의 모든 첫 프레임과 배경 클립은 Pollo AI에서 생성했습니다.
아래는 재현에 필요한 전부입니다: 모델, 설정, 실제 과금, 프롬프트 뼈대.

## 비용 — 예상이 아니라 실측

요청 조건은 **무료 필수 / 유료 금지**였습니다. 결과부터:

- **추가 결제는 없었습니다.** 계정이 이미 결제된 Ultra 연간 구독
  (2027-08-31까지 활성) 상태였고, 충전·플랜 변경은 하지 않았습니다.
- **보유 크레딧 실측 차감: 12,032 → 11,812 = 220 크레딧** (잔고의 1.8%).

| 항목 | 모델 | 설정 | 사전견적 | 
|---|---|---|---|
| 첫 프레임 이미지 8장 | `openai / gpt-image-2` | 2K · quality **medium** | `discountCost: 0` |
| (버린 시안 4장) | `google / nano-banana-pro` | 2K | `discountCost: 0` |
| 히어로 루프 ×2 | `kling-ai / kling-v2-5-turbo` | 5s · **pro** · start=end | 30 each |
| 문제 제기 루프 | `alibaba / wan-v2-6-flash` | 5s · 1080p · audio off | 10 |
| 스크럽 클립 | `kling-ai / kling-v2-5-turbo` | 10s · std | 32 |
| 카드 루프 ×3 | `alibaba / wan-v2-2-flash` | 5s · 720p | 8 each |
| CTA 루프 | `kling-ai / kling-v2-5-turbo` | 5s · **pro** · start=end | 30 |
| | | **영상 견적 합계** | **156** |

**여기서 주의할 점이 있습니다.** 이미지 모델들은 사전견적에서 일관되게
`discountCost: 0` / `activityMode: unlimited` 를 반환했지만, 실측 차감
220에서 영상 견적 156을 빼면 **64 크레딧**이 남습니다. 즉 이미지 12장에
실제로는 크레딧이 나갔습니다. 사전견적의 0을 "무료"로 그대로 믿으면 안 됩니다 —
**생성 전후로 `pollo_account_status` 잔고를 직접 비교하는 것이 유일하게
신뢰할 수 있는 측정입니다.**

참고로 `quality: high` 로 올리면 사전견적부터 10크레딧이 붙습니다.
그래서 medium 에서 멈췄습니다.

**0크레딧 영상 모델은 존재하지 않습니다** — 호출 가능한 image2video 모델을
전수 조회해 확인했습니다. 가장 싼 축이 `wan-v2-2-flash` 8크레딧입니다.

## 모델 선택이 가이드 표와 다른 부분

| 용도 | 가이드 1순위 | 실제 사용 | 이유 |
|---|---|---|---|
| 사실적 시네마틱 스틸 | `seedream-5-0-pro` | `gpt-image-2` | 참조 이미지가 GPT 계열 룩이었고, 무엇보다 **0크레딧** |
| 스크럽 카메라 무브 | `veo-3-1` | `kling-v2-5-turbo` std 10s | `veo3-1-lite`는 5초를 아예 못 받음(4/6/8만 허용). kling이 등속 dolly 지시를 잘 지키고 크레딧이 1/3 |
| 히어로 루프 | `kling-v2-5-turbo` | 동일 | `imageTail`로 끝 프레임을 첫 프레임과 같게 고정 — **단, pro 모드에서만 가능** |

`imageTail`이 pro 전용이라는 건 스키마에 적힌 제약입니다. std로 뽑으면 끝 프레임이
안 닫혀서 루프 이음매가 보입니다. 히어로에만 pro를 쓴 이유가 이것입니다.

## P-IMG — 첫 프레임 프롬프트 (실제 사용본 뼈대)

```
Ultra-clean photoreal 3D studio render, extremely light and airy, 16:9.

[배경]  seamless very pale gradient  #FAFAFC -> #E9E9F2,
        barely visible hairline perspective grid receding across the floor plane.
[피사체] <오브젝트> in matte-to-satin pure white with a soft ceramic sheen.
        A single small polished gold sphere — the only saturated colour in the frame.
[구도]  centred, strictly inside the central 26 percent of the frame width,
        never touches or approaches any frame edge.
        The left third, right third and bottom third are empty, clean,
        unbroken pale gradient with no detail, reserved for text overlay.
[조명]  one very large soft overhead studio softbox from the upper left,
        long soft diffuse shadow to the lower right, gentle ambient occlusion,
        no harsh speculars, no rim lights.
[질감]  a few tiny out-of-focus dust motes, shallow depth of field.
[카메라] 50mm lens, slight high three-quarter angle.

No text, no letters, no numbers, no logos, no watermark,
no UI elements, no people, no faces.
```

`central 26 percent` 는 장식이 아니라 세이프존 계산값입니다 —
아이폰 풀블리드에서 16:9 소스의 가로 26%만 남기 때문입니다. 사이트 03번 참고.

## P-VID — image→video 프롬프트 (실제 사용본 뼈대)

```
Keep the composition of the attached image exactly as it is.

[모션]   <단 하나의 움직임>. That single motion is the only movement in the shot.
[카메라]  one ultra-slow <push-in | dolly forward | locked off> and nothing else,
         perfectly smooth, no shake, no zoom, no tilt, no orbit.
[유지]   The subject stays fully inside the frame for the entire clip and never
         approaches an edge; the left third, right third and bottom third stay
         empty and clean.
[속도]   close to slow motion, almost nothing changes across the five seconds.
[루프]   the last frame returns to almost exactly the same state as the first
         frame so the clip loops seamlessly.
[일관성]  colour, lighting, shadow direction and surface texture stay identical
         to the first frame throughout. One single continuous take, no cuts.
```

네거티브(전 클립 공통):

```
cut, hard cut, scene change, transition, fade, dissolve, text, letters,
subtitles, caption, logo, watermark, UI, interface, human, face, people, hands,
fast camera movement, zoom in, zoom out, whip pan, handheld shake, camera shake,
split screen, subject leaving the frame, cropped subject, oversaturation,
colour shift, lens flare, distortion, warping, morphing, flicker, strobing,
extra objects appearing
```

스크럽 클립에는 `acceleration, sudden speed change` 를 네거티브에 **추가**했습니다.
스크럽은 스크롤 위치를 시간에 직결하므로, 클립 안에서 속도가 변하면
스크롤은 등속인데 화면만 들쭉날쭉해집니다.

## 샷 리스트

| 클립 | 섹션 | 성격 | 방식 |
|---|---|---|---|
| `s1-hero` | S1 히어로 | 흰 링 조형이 아주 느리게 자전 | 루프 (16:9 + 9:16 별도 생성) |
| `s2-broken` | S2 고장 진단 | 같은 링이 세 조각으로 어긋난 채 정지에 가깝게 | 루프 |
| `s3-corridor` | S3 세이프존 | 흰 회랑을 등속 전진, 끝의 링으로 접근 | **스크럽** |
| `s4-a` | S4 샷 설계 | 오브젝트 하나, 무브 하나 | 3초 루프 |
| `s4-b` | S4 첫 프레임 | 동일한 링 3개 = 재현성 | 3초 루프 |
| `s4-c` | S4 영상·인코딩 | 링이 얇은 단면으로 분해 = 프레임 | 3초 루프 |
| — | S5 타이포 | **영상 없음.** 의도적으로 조용한 구간 | — |
| `s6-cta` | S6 CTA | 링이 닫히고 금구가 정점에 | 루프 |

모바일 세로(9:16)는 히어로만 별도 생성했습니다. 나머지 섹션은 가로 소스를
`object-position`으로 밀어 처리합니다 — 가이드가 말하는 임시방편이고,
그렇게 해도 되는 이유는 그 섹션들의 피사체가 이미 중앙 26% 안에 있기 때문입니다.

## 생성물 확인 링크

이 저장소를 만든 컨테이너는 `videocdn.pollo.ai` 에 접근할 수 없어 **결과물을
한 번도 열어보지 못했습니다.** 구도·컷·톤이 지시대로 나왔는지는 아래에서
직접 확인하시고, 어긋난 것만 같은 프롬프트로 재생성하면 됩니다
(샷당 3~4회 뽑는 게 정상입니다).

| 클립 | 첫 프레임 (0 견적) | 영상 |
|---|---|---|
| `s1-hero` 16:9 | [보기](https://pollo.ai/v/cmtp93qyx2kgc13snvsis2e4b) | [보기](https://pollo.ai/v/cmtp9kcdl2m68zjleawe0m1nv) |
| `s1-hero` 9:16 모바일 | [보기](https://pollo.ai/v/cmtp93uwj2l2ltz3fs620ktc7) | [보기](https://pollo.ai/v/cmtp9khe22mp0ux0hce9o2cr6) |
| `s2-broken` | [보기](https://pollo.ai/v/cmtp988vp2l0vp398y6ta0wtb) | [보기](https://pollo.ai/v/cmtp9kmup2mbhcac288c7cwlc) |
| `s3-corridor` 스크럽 | [보기](https://pollo.ai/v/cmtp9a1732m2p13fs021xvwvr) | [보기](https://pollo.ai/v/cmtp9ksdy2lsqpk4ce3a8mgmn) |
| `s4-a` | [보기](https://pollo.ai/v/cmtp9ikei2mibycuekglw94z0) | [보기](https://pollo.ai/v/cmtp9phpf2n3gmb0x610ge6cs) |
| `s4-b` | [보기](https://pollo.ai/v/cmtp9iovy2lp7p398jktfqlpu) | [보기](https://pollo.ai/v/cmtp9ps292n6itpwk80k57ogb) |
| `s4-c` | [보기](https://pollo.ai/v/cmtp9ishl2lnkpk4cp5g1llqt) | [보기](https://pollo.ai/v/cmtp9qup42lz1ine5tpg4nunh) |
| `s6-cta` | [보기](https://pollo.ai/v/cmtp9a5yb2m02ycuemqibfqpd) | [보기](https://pollo.ai/v/cmtp9p7nd2luzlpegpju2gx0i) |

특히 다음 세 가지를 봐 주세요:

1. **컷이 들어갔는가.** 프롬프트·네거티브 양쪽에 막아뒀지만 모델이 넣을 때가 있습니다.
   배경 루프에 컷이 있으면 그 클립은 못 씁니다.
2. **피사체가 중앙 26% 안에 있는가.** 벗어났다면 모바일에서 사라집니다.
3. **`s1-hero` 와 `s6-cta` 의 첫/끝 프레임이 실제로 닫히는가.**
   `imageTail` 로 고정했지만 pro 모드에서도 완벽하진 않습니다. 이음매가 보이면
   ffmpeg 로 앞뒤 0.2초를 크로스페이드하거나 클립을 짧게 자르세요.
