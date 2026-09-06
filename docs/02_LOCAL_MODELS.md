# 8GB VRAM(RTX 4070 Laptop)에서 실제로 되는 것

VRAM 8GB는 영상 생성에서 하한선이다. 아래는 되는 것과 안 되는 것.

## 로컬에서 되는 오픈소스 영상 모델

| 모델 | 라이선스 | 8GB 실현성 | 비고 |
|---|---|---|---|
| **LTX-Video** (Lightricks, 2B distilled) | 오픈 웨이트 | 잘 됨 | 8GB에서 가장 빠름. 짧은 클립 위주 |
| **Wan 2.1 T2V-1.3B** (Alibaba) | Apache 2.0 | 잘 됨 | 480p, 품질/속도 균형 좋음 |
| **Wan 2.2 TI2V-5B** | Apache 2.0 | 오프로딩 필요 | 느리지만 가능 |
| **FramePack** (lllyasviel) | 오픈 | 저VRAM 설계 | 6GB 목표로 만들어짐, 긴 영상 |
| **CogVideoX-2B** | 오픈 | 됨 | 구세대, 품질 낮음 |
| **HunyuanVideo 13B** | 오픈 | GGUF Q4 + block swap 필요 | 8GB에선 매우 고통스러움 |

## 로컬에서 안 되는 것

- MiniMax Hailuo / video-01 — 가중치 비공개
- Sora 2, Veo 3, Kling, Runway — 전부 클로즈드
- MiniMax M1/M2 LLM — 오픈소스지만 수백B MoE, H100 다중 필요

## 판단

로컬 오픈소스로 뽑는 결과물의 품질은 Pollo를 통해 접근 가능한
Veo 3.1 / Sora 2 / Kling v3 / Seedance 2.5 와 같은 급이 아니다.

크레딧 12,040이 남아 있고 구독이 2027년까지 유효하므로:

- **주력 파이프라인** → Pollo API (Claude Code에서 MCP로 직접 호출 가능)
- **로컬 GPU** → 무제한 반복이 필요한 실험, 파인튜닝/LoRA, 오프라인 작업, 프라이버시 필요 소재
- **로컬 GPU가 확실히 유리한 영역** → 이미지 생성(SDXL/Flux dev), 업스케일, 로컬 TTS,
  Whisper 자막 추출. 이쪽은 8GB로도 실용적이다.

---

# 양자화하면 미니맥스가 되나?

영상과 LLM에서 답이 완전히 다르다.

## 미니맥스 영상 — 양자화 자체가 성립하지 않는다

양자화는 **가중치 파일을 압축**하는 기술이다. MiniMax는 영상 모델 가중치를 공개한 적이 없으므로
압축할 파일이 손에 없다. 하드웨어 문제가 아니라 라이선스 문제이며, 어떤 장비를 사도 로컬 실행은 불가능하다.

## 모델별 양자화 후 필요 메모리

| 모델 | 원본 | Q4 이후 | 필요 메모리 | 4070 8GB |
|---|---|---|---|---|
| MiniMax 영상 (Hailuo) | 비공개 | — | — | 영구 불가 |
| MiniMax-M2 (230B MoE, 활성 10B) | ~460GB | ~115GB | RAM 128GB (CPU 추론) | 램 사면 가능하나 매우 느림 |
| MiniMax-M1 (456B MoE, 활성 46B) | ~900GB | ~230GB | RAM 256GB+ | 사실상 불가 |
| HunyuanVideo 13B | ~26GB | ~7GB | VRAM 8GB + block swap | **됨** (GGUF Q4) |
| Wan 2.2 14B | ~28GB | ~8GB | VRAM 8GB 빠듯 / 12GB 편함 | 빠듯하게 됨 |
| Wan 2.1 1.3B | ~3GB | ~1GB | VRAM 6GB | 양자화 없이도 됨 |

영상 모델에서는 양자화가 확실히 효과가 있다. HunyuanVideo 13B가 8GB에 들어가는 것은 GGUF Q4 덕분이다.
MiniMax는 양자화로 해결되는 문제가 아니다.

---

# 원화 기준 추가 지출별 가능 범위

> 가격은 대략적인 시세 범위다. 구매 전에 현재가를 직접 확인할 것.

| 지출 | 사는 것 | 되는 것 | 판단 |
|---|---|---|---|
| **0원** | 이미 보유 — Pollo 크레딧 12,040 | 아레나 1위권 전부 (Veo 3.1, Sora 2, Kling v3, Seedance 2.5, Hailuo 2.3, Wan 3.0) | **여기부터 쓸 것** |
| 90~130만원 | RTX 3090 24GB 중고 | Wan 14B / HunyuanVideo 양자화 없이, LoRA 학습 | 가성비 1위 |
| 50~80만원 | RAM 128GB | MiniMax-M2 Q4 CPU 추론 | 느려서 실무 불가, 비추천 |
| 350~450만원 | RTX 5090 32GB | 로컬 영상 쾌적 | 지금 우선순위 아님 |
| 1,300만원~ | Mac Studio 512GB 통합메모리 | 대형 MoE LLM | 영상엔 오히려 느림 |
| 얼마든 | 어떤 하드웨어든 | MiniMax 영상 로컬 | 불가능 — 돈 문제가 아님 |

크레딧 12,040이 남아 있고 구독이 2027년 8월까지다. 이걸 소진하기 전에 GPU를 사면 같은 능력을 두 번 사는 셈이다.
로컬이 실제로 필요해지는 시점(무제한 반복, LoRA 학습, 오프라인 소재)이 오면 RTX 3090 24GB 중고가 첫 카드로 가장 합리적이다.

---

# 아레나 1위권

> 순위는 거의 매달 바뀐다. artificialanalysis.ai 의 Video Arena 에서 현재 순위를 직접 확인할 것.

- **클로즈드 상위권**: Veo 3.1, Sora 2 Pro, Kling v3, Seedance 2.5, Hailuo 2.3, Runway Gen-4
  → **전부 Pollo 구독에 포함되어 있다. 1위권을 쓰기 위해 추가로 살 것이 없다.**
- **오픈웨이트 1위권**: Wan 2.2 / 2.5 계열 (Apache 2.0, 상업 이용 자유), HunyuanVideo, LTX-Video

주의: 8GB에서 돌리는 Wan 1.3B와 아레나 순위표의 Wan 14B / 2.5는 완전히 다른 물건이다.
순위표의 Wan을 로컬에서 쓰려면 VRAM 24GB가 필요하다.
