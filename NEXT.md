# 다시 시작할 때 — 브리핑

## 🚀 배포됨 (2026-08-27)

- **라이브 사이트**: https://yuri-verse.github.io/maple-gate/  (GitHub Pages · 공개)
- **저장소**: github.com/yuri-verse/maple-gate  (git remote origin, gh 로그인됨)
- **아티팩트(미리보기)**: https://claude.ai/code/artifact/da0223a7-9ab7-45bc-a264-8c71871d2412
  · 아티팩트는 CSP 로 외부 fetch 가 막혀 랭킹/공지가 안 뜬다 — 완전판은 라이브 사이트에서만.

### 데이터 파이프라인 (전부 무료)
- **전투력 랭킹**: mgf.gg 파싱 → **Supabase** `rankings` 테이블 (3000명, `pages:100`).
  프론트가 Supabase 에서 읽고 이름 검색은 전체에서 실시간(`nickname=ilike`).
  Supabase URL/publishable 키 = `data/supabase.json`(공개 안전).
  쓰기용 service_role 키 = GitHub Secret `SUPABASE_SERVICE_KEY`(웹 UI 로 넣음, 절대 커밋 금지).
- **공지·이벤트**: 넥슨 공식 포럼 API(`forum.nexon.com/api/v1/community/607/stickyThreads`) → `data/notices.json`.
- **자동 갱신**: `.github/workflows/collect.yml` 3시간마다 (mgf 수집 → notices → Supabase 업서트 → 커밋).
- **배포**: `.github/workflows/deploy.yml` push 시 `dist/` 를 Pages 로.

### 다음에 이어서 할 만한 것
1. **랭킹 인원 늘리기**: `tools/ranking-sources.json` 의 `pages` (100=3000명). 1만~3만은 한 번에 OK.
   전체 48만(16,199페이지, ~7h)은 CI 6h 한도 초과 → 나눠 긁기 설계 필요.
2. **유물 입력 UI** · **모델의 일반몹 데드라인**(원래 남은 계산기 과제, 아래 참조).
3. `git`/`gh` 준비돼 있으니 코드 고치면 `git add/commit/push` → 자동 배포.

⚠️ `reference/`(681MB, 넥슨 클라이언트 원본)와 `node_modules` 는 .gitignore — 커밋 금지.
스크린샷 확인은 `tools/shot.js` (크로미움 로컬 설치됨, `tools/README-shots.md`).

---


마지막 작업: **2026-08-26**

## 지금 어디까지 왔나

스테이지 1,839개 · 직업 14 · 동료 61종을 클라이언트 테이블에서 뽑아
클리어 확률을 계산한다. 실계정 앵커(ch36 비숍 2.4경 → **36-7 클리어 / 36-8 실패**)를
모델이 재현한다: 36-6 89% · **36-7 62%** · **36-8 24%** · 36-9 4%.

오늘 넣은 것 — 동료 스킬 해금 레벨 반영, 여유 배수의 일반/보스 구간 분리,
해석적 클리어 확률(몬테카를로 제거), 스탯 재배분 추천 카드, jsdom 검증 하네스.

**UI 전면 개편 (같은 날 오후)** — 페이지가 논문처럼 길다는 지적을 받고 3층으로 다시 짰다.
① 결과(링 게이지 + 왜 그런지 한 줄) ② `지금 뭘 바꾸면 되나` 단일 우선순위 목록
③ 내 캐릭터 입력 ④ 근거(전부 `<details>` 로 접힘). 히어로 섹션과 설명 문단 대부분을 걷어냈다.
직업 선택은 select 대신 **초상화 버튼 그리드** — `tools/build-icons.py` 가
`reference/hi/uiatlases_assets_uiatlases/portrait.spriteatlasv2.bundle` 에서 뽑아
`data/job-icons.json`(128px WebP data URI, 135KB) 으로 만든다. **14직업 전부** 들어간다.
어느 스프라이트를 쓸지는 `HeroTable.json` 의 `PortraitPath` 를 그대로 따른다.
**동료 선택도 같은 방식** — `tools/build-supporter-icons.py` 가 `supporter.spriteatlasv2.bundle`
에서 14장을 뽑아 `data/supporter-icons.json` 으로 만든다. 56개짜리 드롭다운 대신
슬롯(메인 1 + 서브 6)을 먼저 고르고 직업 → 등급 → 레벨을 채우는 피커로 바꿨다.
동료 초상화는 직업 초상화와 **다른 그림이다** (비숍·나이트워커가 눈에 띄게 다름) — 재사용 금지.

**정보 포털로 확장 (2026-08-27)** — 단일 계산기에서 탭 5개짜리 사이트로 바꿨다.
`홈` · `스테이지 분석` · `동료 도감` · `몬스터 도감` · `강화 · 유물`.
maple.gg 같은 걸 원하셨는데 **닉네임 조회와 유저 랭킹은 데이터 출처가 없다**(넥슨 오픈API 미등록).
그래서 "조회" 대신 **내 스탯으로 계산하는 랭킹**으로 갔다 — 돌파 498개 전수 스캔(내 진행),
동료 56종 DPS 티어, 직업 14종 비교, 필요 DPS 기준 난이도 순위.

**디자인 갈아엎기 (2026-08-27)** — "AI로 만든 티가 난다"는 지적을 받고 홈을 다시 짰다.
문제는 ① SaaS 랜딩식 히어로(eyebrow → 제목 → 설명 → 칩 6개) ② 카드 6개가 전부 같은 골격
③ 청록 단색 팔레트 ④ 초상화를 32px 로만 씀 ⑤ 내 캐릭터가 페이지 맨 아래.

고친 것 — **다크 기본 + 골드 액센트**로 팔레트 교체, 히어로를 **내 캐릭터 패널**(104px 초상화 ·
큰 전투력 · 진행 게이지 · 배경 워터마크 아트)로, 랭킹 카드 껍데기를 걷어내고 섹션 구분선으로,
진행 리스트를 세로 7행에서 **가로 스트립**으로, 랭킹 초상화 34 → 44px + 1·2·3위 배지.

**CSS 를 만질 거면 `tools/shot.js` 로 먼저 렌더해서 봐라** (`tools/README-shots.md`).
이번 문제의 근본 원인은 화면을 못 보고 CSS 를 쓴 것이었다.

**유저 랭킹 = 등록형 보드 (2026-08-27)** — 전투력/길드/인기도 랭킹을 계속 요청받았다.
넥슨에서 긁어오는 건 여전히 불가(공개 API 없음 + 서버 우회 금지). 대신 **각자 자기 기록을
등록하는 보드**를 만들었다. 아티팩트의 `artifact` 런타임 능력(페이지가 자기 자신의 새 버전을
발행)을 쓴다 — 누가 등록하면 그 링크를 가진 모두에게 반영된다.

**포털과 별도 아티팩트다.** 포털이 3.2MB 라 등록할 때마다 그걸 통째로 재발행하면 답이 없어서,
192KB 짜리 보드를 따로 뒀다. 포털 홈에서 링크로 연결하고, 등록 버튼에는 현재 직업·전투력·
도달 스테이지를 `#reg=<base64>` 로 실어 보내 폼이 미리 채워진다.

- 보드: https://claude.ai/code/artifact/a8bb8f1f-0c77-4122-9d9d-2c9b0943a6a1
- 소스 `src/board.html` → `python3 tools/build-board.py <포털URL>` → `board.html` / `board-artifact.html`
- 검증 `node tools/board-test.js` (등록 4회 누적 + **템플릿 고정점** 확인)

한계: **편집 권한이 있는 사람만 등록 가능** → 길드·친구 단위 보드다. 게임 전체 랭킹은
별도 호스팅 + 백엔드가 필요하다. 수치는 자기 신고라 검증되지 않는다(화면에 명시).

**정적 호스팅 + 랭킹 수집기 (2026-08-27)** — "메키픽도 긁어오는데 왜 못 하냐"에서 시작했다.
결론부터: **긁는 건 기술적으로 된다.** 메키픽 랭킹 페이지 HTML 안에 JSON 이 그대로 실려 있고
robots.txt 도 `Allow: /` 다. 못 하는 건 넥슨 **게임 서버** 쪽이지 남의 공개 페이지가 아니다.

진짜 제약은 두 가지였다.
1. 아티팩트는 CSP 로 외부 요청이 막혀서 실시간 조회 자체가 불가 → **정적 배포본(`dist/`)** 을 만들었다.
   `python3 build.py` 가 이제 `artifact.html`(인라인) 과 `dist/`(데이터 분리, 165KB + bundle.js) 를 같이 낸다.
2. 남의 DB 를 우리 화면에 얹는 문제 → 수집기는 만들되 **기본값을 꺼 두었다**.

`tools/collect-ranking.py` + `tools/ranking-sources.json`. 어댑터 구조라 출처를 갈아끼울 수 있다.
메키픽 어댑터는 구현·검증 완료(20행 파싱). 수집 원칙을 코드로 강제한다 —
`account_id`·`avatar_url`·`visual_info`·`last_login` 같은 프로필/식별 정보는 버리고,
순위에 필요한 최소 필드만 남긴다. 출처 표기가 없으면 화면이 표를 아예 안 띄운다.

`.github/workflows/` 에 6시간 주기 수집과 Pages 배포를 넣었다. 출처가 전부 꺼져 있으면 수집은 그냥 빠져나온다.

**2026-08-27 사용자 지시로 mekipick 을 켰다.** 20행 수집·표시 확인. 화면 하단에 출처와
수집 시각을 박는다(출처 없으면 표 자체가 안 뜨게 코드로 막아 뒀다).

**수집 소스를 mgf 로 바꿨다 (2026-08-27).** "20이 전부냐"는 지적이 맞았다 — 그건 메키픽
하이라이트 페이지 한계였고, **mgf.gg 는 전체 사다리를 `?page=N` 로 공개한다** (페이지당 30행,
마지막 page=16199 ≈ 48만 명). CSS 클래스 앵커(`nickname`·`badge-guild`·`job-name`·`power-kor`·
`server-badge`)로 파싱한다. 기본 20페이지=600명 수집, `ranking-sources.json` 의 `pages` 로 조절.
메키픽 어댑터는 남겨 뒀지만 껐다.

**게임 서버에서 직접 가져오는 건 안 한다.** 비공식 클라이언트를 만들어 인증을 우회해야 하는
일이라 범위 밖이다(사용자 원칙 #1). 더 많은 행이 필요하면 제휴(admin@mgf.gg) 나
넥슨 오픈 API 요청이 답이다.

**랭킹은 `dist/` 에서만 보인다.** 아티팩트는 CSP 로 `data/ranking.json` 도 못 읽어서
등록형 보드 안내로 폴백한다. 실제로 띄우려면 정적 호스팅이 필요하다.

## 손대기 전에

```bash
python3 tools/build-icons.py            # 직업 초상화 -> data/job-icons.json
python3 tools/build-supporter-icons.py  # 동료 초상화 -> data/supporter-icons.json
python3 tools/build-dex.py              # 몬스터 465 + 유물 35 -> data/dex.json
python3 tools/build-dex-icons.py        # 도감 아이콘 -> data/dex-icons.json
python3 build.py               # -> artifact.html(인라인) + index.html + dist/(정적 호스팅용)
python3 tools/collect-ranking.py --status   # 랭킹 수집 설정·마지막 수집 상태
node tools/smoke.js            # 추천표 회귀 + '재계산 결정적: true' 확인
node tools/calib.js            # R 스윕 — 36-7 통과 / 36-8 실패 유지 확인
node tools/actions.js          # 직업·동료 버튼 + 우선순위 목록
node tools/portal.js           # 탭 5개 · 홈 랭킹 · 도감 · 강화 계산기 · 통합 검색
node tools/shot.js home dark shots/home.png   # 실제 렌더 스크린샷 (README-shots.md)
```

`src/page.html` 만 편집한다. `index.html` / `artifact.html` 은 생성물이다.
**피해 모델을 건드리면 `calib.js` 로 R 을 다시 맞춰야 한다** (현재 R = 2.80).

## 남은 작업 — 우선순위 순

1. **일반 몬스터 데드라인** ← 지금 모델의 가장 큰 구멍
   돌파는 몬스터가 출구에 닿으면 즉시 실패인데, 모델은 **보스가 출구에 닿는 시각만**
   제한으로 쓴다. 36-8 기준 일반 몬스터 이동속도 1050 vs 보스 675 — 일반 쪽이 훨씬
   먼저 도달한다. 각 캠프의 스폰 시각·이동속도로 개체별 데드라인을 세워야 한다.
   (`availableS()` in `src/page.html`, 캠프 데이터 = `[시각, [[이름, 마리수, HP, 보스여부, 이동속도]]]`)

2. **유물(遺物) 입력 UI** — 처음부터 요구된 축인데 아직 없다.

3. **스턴 / 보스 홀드** — "스턴 스킬을 몇 번 쓸 수 있는지에 따라 다르다"는 실플레이 관찰.
   보스를 멈춘 시간만큼 데드라인이 밀린다.

4. **우선순위 목록의 투자형 기준** — 지금은 "표시 전투력 +5% 를 이 능력치 하나에 몰았을 때"로
   환산해 비교한다. 전투력을 거의 안 먹는 항목(쿨타임 감소)은 이 잣대에 안 잡혀서 목록 아래
   별도 한 줄로만 알린다. 실제 획득 단위(잠재능력 한 줄, 스타포스 한 단계)를 알게 되면
   그쪽이 더 정확하다. (`budgetStep` / `actions` in `src/page.html`)

5. **R = 2.80 이 크다** — 모델이 실제 피해를 그만큼 과소평가한다는 뜻. 절대 피해량은
   아직 못 믿고 **스테이지 간 상대 난이도만** 유효하다. 1·3 을 해결하면 R 이 1 쪽으로
   내려올 가능성이 있다.

6. **아직 안 쓴 아틀라스** — `reference/hi/uiatlases_assets_uiatlases/` 에 38개가 있다.
   `artifact.spriteatlasv2.bundle`(유물 → 남은 작업 2번), `skillicon.spriteatlasv2.bundle`(로테이션 표),
   `supporter.spriteatlasv2.bundle` 의 `Slot_*` 배너 14종(208×88, 아직 안 씀).

7. **유물·몬스터 한글 이름 없음** — 클라이언트 `Localization_ko.json` 의 `Text` 가 암호화돼
   있다(AES 블록으로 보이는 base64). 복호화는 사용자가 정한 조사 범위 밖이라 **하지 않는다**.
   몬스터는 커뮤니티 파생본의 영문명을 쓰고, 유물은 코드(`ARTIFACT_3_1`)와 아이콘으로만 보여준다.
   넥슨이 공개 자료로 이름을 내놓으면 그때 붙인다.

8. **닉네임 조회 / 유저 랭킹** — 데이터 출처 없음(README 의 조사표). 넥슨 오픈API 가 열리면
   홈의 랭킹 카드 자리에 바로 붙일 수 있게 구조는 잡아 뒀다.

## 건드리지 말 것

- MGF.GG 제보 데이터는 내부 보정에만. 화면 표시·저장소 반입 금지.
- 클라이언트 추출값 / 보정값 / 커뮤니티 추정치를 화면과 README 양쪽에서 분리 표기.
- 모델이 못 재는 항목은 "기여 0"이 아니라 **"모델 미반영"**으로 표시.

자세한 근거·검증 과정은 `README.md`.
