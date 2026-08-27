#!/usr/bin/env python3
"""페이지를 두 가지로 낸다.

  artifact.html  — 데이터를 전부 인라인한 단일 파일 (아티팩트 배포용)
  index.html     — 위와 같은 단일 파일 (로컬에서 열어보기 · jsdom 검증용)
  dist/          — 정적 호스팅용. 데이터를 data/bundle.js 로 떼어낸다.

dist 를 따로 두는 이유: 아티팩트는 외부 네트워크 요청이 CSP 로 막혀서 랭킹 같은
자주 바뀌는 데이터를 따로 실을 수 없다. 정적 호스팅에서는 데이터 파일만 갈아끼우면 된다.
데이터를 `<script src>` 로 먼저 읽어 전역에 올리므로 페이지 코드는 손대지 않는다.
"""
import json, pathlib, shutil

ROOT = pathlib.Path(__file__).parent
page = (ROOT / "src" / "page.html").read_text(encoding="utf-8")

def load(name):
    # JSON 문자열 안의 </script> 가 인라인 스크립트를 먼저 닫아버리는 걸 막는다
    return (ROOT / "data" / name).read_text(encoding="utf-8").replace("</", "<\\/")

def inject(text, token, payload):
    a = text.index(f"/*__{token}__*/")
    b = text.index(f"/*__END{token}__*/") + len(f"/*__END{token}__*/")
    return text[:a] + payload + text[b:]

SLOTS = [("DATA", "web-data.json"), ("ICONS", "job-icons.json"),
         ("SUPICONS", "supporter-icons.json"), ("DEX", "dex.json"),
         ("DEXICONS", "dex-icons.json")]

# ---------- 단일 파일 ----------
body = page
for token, fn in SLOTS:
    body = inject(body, token, load(fn))
(ROOT / "artifact.html").write_text(body, encoding="utf-8")

meta = json.loads((ROOT / "data" / "web-data.json").read_text(encoding="utf-8"))["meta"]
HEAD = ('<!doctype html>\n<html lang="ko">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="메이플키우기 스테이지 클리어 확률과 동료·몬스터 도감. '
        '클라이언트 원본 테이블에서 직접 계산합니다.">\n'
        '<meta name="robots" content="index,follow">\n'
        '</head>\n<body>\n')
(ROOT / "index.html").write_text(HEAD + body + "\n</body>\n</html>\n", encoding="utf-8")

# ---------- 정적 호스팅용 ----------
dist = ROOT / "dist"
if dist.exists():
    shutil.rmtree(dist)
(dist / "data").mkdir(parents=True)

split = page
for token, _ in SLOTS:
    split = inject(split, token, f"window.__D.{token.lower()}")
split = split.replace("<script>\nconst DATA =",
                      '<script src="data/bundle.js"></script>\n<script>\nconst DATA =', 1)
(dist / "index.html").write_text(HEAD + split + "\n</body>\n</html>\n", encoding="utf-8")

parts = ["window.__D={};"]
for token, fn in SLOTS:
    parts.append(f"window.__D.{token.lower()}=" + load(fn) + ";")
(dist / "data" / "bundle.js").write_text("\n".join(parts), encoding="utf-8")

# 랭킹·공지는 따로 — 수집기가 이 파일만 갈아끼운다
import shutil as _sh
_sup = ROOT / "data" / "supabase.json"
if _sup.exists():
    _sh.copy(_sup, dist / "data" / "supabase.json")

for fn, empty in (("ranking.json", {"source": None, "collectedAt": None, "rows": []}),
                  ("notices.json", {"source": None, "collectedAt": None, "notices": [], "events": []})):
    src = ROOT / "data" / fn
    (dist / "data" / fn).write_text(
        src.read_text(encoding="utf-8") if src.exists()
        else json.dumps(empty, ensure_ascii=False), encoding="utf-8")

size = lambda p: f"{p.stat().st_size/1024:>8,.0f} KB"
print(f"artifact.html   {size(ROOT/'artifact.html')}")
print(f"index.html      {size(ROOT/'index.html')}")
print(f"dist/index.html {size(dist/'index.html')}   (데이터 분리)")
print(f"dist/data/bundle.js {size(dist/'data'/'bundle.js')}")
print(f"데이터 v{meta['appVersion']} / 스테이지 {meta['stages']} / 직업 {meta['jobs']}")
