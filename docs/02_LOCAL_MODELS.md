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
