# 햄찌중국가족 — 중국어 voice_block 작성 규칙 v1 (메인 세션용)

> 메인 세션(공장)이 `EPNN_*.json`의 `voice_block`을 만들 때 따르는 규칙.
> 제출 세션(세션B)은 여전히 `clip.prompt + " " + voice_block`을 그대로 제출하며, 대사를 직접 고치지 않는다.
> `요구사항_총정리_v1.md` 규칙 4의 "일본어"는 "중국어(普通话)"로 바꾼다.

---

## 1. 기본 원칙

1. 대사 = **자연스러운 중국어(普通话)**, 간체 표기. 대만식·방언 표현은 쓰지 않는다.
2. 한 클립(8초)에 **대사 1~2줄, 합계 15자 안팎**. 너무 길면 말이 잘리거나 빨라진다.
3. 쉬운 구어체와 감탄사(哇, 哎呀, 嗯嗯, 好吃)를 쓴다. 성어·문어체는 피한다.
4. **배경음악 없음.** 가벼운 효과음만 쓴다(발소리, 뽁, 바삭 등).
5. **화면 글자·자막 없음.** 자막은 모두 편집 단계에서 넣는다.
6. 스토리·컷 순서·캐릭터 행동은 일본어판과 같다. **언어만 바꾼다.**

## 2. 목소리 일관성 (모든 voice_block에 매번 그대로 넣기)

| 캐릭터 | 목소리 |
|---|---|
| 엄마 | 귀여운 아이 목소리, 또렷하고 야무진 톤 |
| 아빠 | 귀여운 아이 목소리, 살짝 억울한 톤 |
| 딸 | 아기 옹알이(말이 되다 만 소리, 예: "嗯…吃吃!") |
| 반려묘 | 짧은 야옹 효과음만 (편마다 1번) |

## 3. voice_block 템플릿 (영문 지시 + 중국어 대사)

```
Audio: no background music, light cute sound effects only, no on-screen text or subtitles.
Voices: Mom speaks Mandarin Chinese in a cute childlike voice, clear and confident.
Dad speaks Mandarin Chinese in a cute childlike voice with a slightly aggrieved, sulky tone.
Baby daughter only babbles in baby talk.
Dialogue — Mom: "<중국어 대사>" / Dad: "<중국어 대사>" / Baby: "<옹알이>"
```

예시 (식당 장면):
```
Dialogue — Mom: "哇，看起来好好吃！" / Dad: "我的那份呢…？" / Baby: "嗯嗯，吃吃！"
```

---

## 4. 마지막 클립의 "한국어 한 마디" 규칙

목적은 **스토리를 해치지 않고 한국 여행에서 바로 쓰는 한국어 한 문장을 자연스럽게 가르치는 것**이다.

### 4-1. 넣는 방법 (권장: A, 발음이 나쁘면 B로 전환)

- **A. 말로 하기 + 편집 자막 (권장)**
  - **넣는 곳:** 에피소드 **마지막 클립 1개**만. 엄마나 아빠가 장면에 맞는 한국어 한 마디를 말한다.
  - **딸:** 옹알이로 따라 해도 된다(예: "마시써!"). 귀여움 포인트가 된다.
  - **나머지 대사:** 그 클립의 다른 대사는 중국어 그대로 둔다. 한국어는 **한 문장, 2~6음절**로 제한한다.
  - **편집 자막:** `한국어 원문 / 발음 / 뜻`을 넣는다. 예: `맛있어요! · mashisseoyo · 好吃！`
- **B. 자막만 (대체안)**
  - **언제:** Flow(Omni Flash)의 한국어 발음이 어색하게 나올 때.
  - **어떻게:** 대사는 전부 중국어로 두고, 편집에서 마지막 장면에 같은 형식의 한국어 자막만 얹는다.
  - **장점:** 영상을 다시 만들 필요가 없다.

### 4-2. 스토리를 지키는 조건

1. 한국어 문장은 **그 장면 행동에 딱 맞아야** 한다. 먹는 장면이면 "맛있어요", 계산 장면이면 "얼마예요?".
2. 한국어 때문에 새 장면이나 새 행동을 추가하지 않는다.
3. 앞 클립들은 한국어를 **예고하거나 설명하지 않는다**. 마지막에 툭 나오는 느낌으로 둔다.
4. 에피소드마다 문장을 바꾼다. 같은 문장은 10편 안에 반복하지 않는다.

### 4-3. voice_block 표기법 (마지막 클립만)

```
Dialogue — Mom: "好好吃！" then says in Korean: "맛있어요!" / Baby babbles: "마시써!"
Korean line spoken slowly and clearly.
```

### 4-4. 여행 한국어 후보 (장면별)

| 장면 | 한국어 | 발음 | 중국어 뜻 |
|---|---|---|---|
| 식사 시작 | 잘 먹겠습니다 | jal meokgesseumnida | 我开动了 |
| 먹는 중 | 맛있어요! | mashisseoyo | 好吃！ |
| 식사 끝 | 잘 먹었습니다 | jal meogeosseumnida | 吃饱了，谢谢 |
| 주문 | 이거 주세요 | igeo juseyo | 请给我这个 |
| 계산 | 얼마예요? | eolmayeyo | 多少钱？ |
| 계산 | 계산해 주세요 | gyesanhae juseyo | 请结账 |
| 감사 | 감사합니다 | gamsahamnida | 谢谢 |
| 인사 | 안녕하세요 | annyeonghaseyo | 你好 |
| 사과 | 죄송해요 | joesonghaeyo | 对不起 |
| 길 묻기 | 화장실 어디예요? | hwajangsil eodiyeyo | 洗手间在哪里？ |
| 매운맛 | 안 맵게 해 주세요 | an maepge hae juseyo | 请做不辣的 |
| 매운맛 | 너무 매워요! | neomu maewoyo | 太辣了！ |
| 쇼핑 | 깎아 주세요 | kkakka juseyo | 便宜一点吧 |
| 택시 | 여기로 가 주세요 | yeogiro ga juseyo | 请去这里 |
| 사진 | 사진 찍어 주세요 | sajin jjigeo juseyo | 请帮我拍照 |
| 감탄 | 대박! | daebak | 太棒了！ |
| 헤어질 때 | 안녕히 계세요 | annyeonghi gyeseyo | 再见（对留下的人） |

---

## 5. 메인 세션 체크리스트 (EP JSON 넘기기 전)

- [ ] 모든 `voice_block`이 중국어(普通话)이고, 일본어가 남아 있지 않다
- [ ] 모든 `voice_block`에 목소리 지시(엄마·아빠 아이 목소리, 아빠 억울 톤, 딸 옹알이)가 있다
- [ ] 클립당 대사 합계가 약 15자 이하다
- [ ] 한국어는 마지막 클립에만, 한 문장, 장면 행동과 일치한다
- [ ] no background music / no on-screen text 문구가 있다
- [ ] JSON에 `korean_line`(원문·발음·뜻)을 따로 적어 편집 자막에 쓴다
