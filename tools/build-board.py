#!/usr/bin/env python3
"""src/board.html -> board.html (등록형 랭킹 보드, 자기 자신을 다시 발행할 수 있는 페이지)

이 페이지는 누가 기록을 올릴 때마다 `artifact.publish(html)` 로 **자기 자신의 새 버전**을
저장한다. 그러려면 페이지가 자기 소스를 갖고 있어야 해서 두 가지를 심는다.

  {{SHELL}} — 소스(플레이스홀더가 그대로 남은 상태) 를 base64 로 넣는다.
              페이지는 이걸 꺼내 {{STATE}} 만 갈아끼워 다음 버전을 만든다.
              base64 라서 </script> 같은 문자열이 파싱을 깨지 않는다.
  {{STATE}} — 아이콘 · 직업 목록 · 보드 데이터(JSON).

아이콘은 shell 이 아니라 state 에 넣는다 — shell 은 base64 로 한 번 더 복제되므로
거기에 큰 데이터를 두면 용량이 두 배로 붙는다.
"""
import base64, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'board.html')
OUT = os.path.join(ROOT, 'board.html')
PORTAL = sys.argv[1] if len(sys.argv) > 1 else ''

L = lambda p: json.load(open(os.path.join(ROOT, p), encoding='utf-8'))
icons = L('data/job-icons.json')
jobs = [dict(id=j['id'], ko=j['ko'], fam=j['fam']) for j in L('data/web-data.json')['jobs']]

body = open(SRC, encoding='utf-8').read()
# 소스 어디에도 플레이스홀더가 한 번씩만 있어야 한다 — JS 안의 문자열까지 치환되면
# 스크립트가 통째로 깨진다(실제로 한 번 그랬다). 토큰은 런타임에 조립한다.
for tok in ('{{SHELL}}', '{{STATE}}'):
    n = body.count(tok)
    assert n == 1, f'{tok} 가 {n}번 나온다 — 정확히 1번이어야 한다'


# publish(html) 은 doctype 으로 시작하는 완전한 문서를 요구한다.
# 그래서 base64 로 심는 템플릿도 **완전한 문서**여야 한다 — 그래야 페이지가 만들어내는
# 다음 세대도 완전한 문서가 되고, 그 안의 base64 가 또 같은 템플릿이 된다(고정점).
HEAD = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '</head>\n<body>\n')
TAIL = '\n</body>\n</html>\n'
template = HEAD + body + TAIL

b64 = base64.b64encode(template.encode('utf-8')).decode('ascii')
state = json.dumps(dict(icons=icons, jobs=jobs, portal=PORTAL, board=[]),
                   ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
fill = lambda s: s.replace('{{STATE}}', state).replace('{{SHELL}}', b64)

open(OUT, 'w', encoding='utf-8').write(fill(template))
# 아티팩트 업로드용은 래퍼 없이 (플랫폼이 씌운다). 안에 든 템플릿은 완전한 문서 그대로다.
open(os.path.join(ROOT, 'board-artifact.html'), 'w', encoding='utf-8').write(fill(body))

print(f"board.html {os.path.getsize(OUT)/1024:.0f}KB · 템플릿 {len(template)/1024:.0f}KB"
      f" · base64 {len(b64)/1024:.0f}KB · 아이콘 {len(icons)}개"
      + (f" · 포털 {PORTAL}" if PORTAL else " · 포털 링크 없음"))
