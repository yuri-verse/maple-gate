#!/usr/bin/env python3
"""유저 랭킹 수집기 -> data/ranking.json

**기본값은 꺼져 있다.** 켜기 전에 `tools/ranking-sources.json` 의 `enabled` 를 true 로 바꿔야
한다. 남이 모아 놓은 데이터를 우리 화면에 얹는 일이라, 상대 사이트 동의를 받고 켜는 게 맞다
(연락처는 그 파일에 적어 뒀다). robots.txt 가 안 막는다고 약관이 허락하는 건 아니다.

수집 원칙 — 코드로 강제한다:
  · 순위에 필요한 최소 필드만 가져온다. `account_id` · `avatar_url` · `visual_info` ·
    `last_login` 같은 프로필/식별 정보는 **버린다**. 남의 플레이어 개인 데이터를 옮겨오지 않는다.
  · 요청 사이에 딜레이를 두고, 받아온 원문은 캐시해서 같은 걸 두 번 받지 않는다.
  · 출처와 수집 시각을 데이터에 박는다. 화면에서 지울 수 없게 필수 필드다.

사용:
  python3 tools/collect-ranking.py            # 설정대로 수집
  python3 tools/collect-ranking.py --dry      # 받아만 보고 저장 안 함
  python3 tools/collect-ranking.py --status   # 지금 설정과 마지막 수집 상태
"""
import argparse, html, json, os, re, sys, time, urllib.request, urllib.error, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = os.path.join(ROOT, 'tools', 'ranking-sources.json')
OUT = os.path.join(ROOT, 'data', 'ranking.json')
CACHE = os.path.join(ROOT, '.cache', 'ranking')
UA = ('MapleIdleStageGate/1.0 (fan info site ranking collector; contact successyr@gmail.com) python-urllib')

# 화면에 쓰는 필드만. 여기 없는 건 파서가 뭘 주든 버린다.
KEEP = ('rank', 'nickname', 'guild', 'job', 'level', 'combatPower', 'popularity', 'server')


def get(url, delay, timeout=20):
    """캐시 -> 없으면 요청. 원문 그대로 보관해서 파싱을 다시 돌릴 수 있게 한다."""
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(url.encode()).hexdigest()[:16]
    path = os.path.join(CACHE, key + '.html')
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 600:
        return open(path, encoding='utf-8', errors='replace').read(), True
    time.sleep(delay)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ko'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode('utf-8', errors='replace')
    open(path, 'w', encoding='utf-8').write(body)
    return body, False


def parse_next_rsc(html):
    """Next.js 가 흘려보낸 RSC 조각을 이어붙여 원래 문자열로 되돌린다."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    if not chunks:
        return ''
    raw = ''.join(chunks)
    # \" \\ \n 등을 되돌린 뒤, latin-1 로 새어나온 UTF-8 바이트를 복구한다
    s = raw.encode('utf-8').decode('unicode_escape', errors='replace')
    try:
        return s.encode('latin-1', errors='ignore').decode('utf-8', errors='replace')
    except Exception:
        return s


def objects_with(s, key):
    """문자열 안에서 `key` 를 가진 JSON 객체들을 균형 잡힌 중괄호로 잘라낸다."""
    out, i = [], 0
    while True:
        i = s.find('"' + key + '"', i)
        if i < 0:
            return out
        st = s.rfind('{', 0, i)
        if st < 0:
            i += 1
            continue
        depth, j, instr, esc = 0, st, False, False
        while j < len(s):
            c = s[j]
            if instr:
                if esc: esc = False
                elif c == '\\': esc = True
                elif c == '"': instr = False
            elif c == '"': instr = True
            elif c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        try:
            out.append(json.loads(s[st:j + 1]))
        except Exception:
            pass
        i = j + 1


def adapt_mekipick(html):
    rows = []
    for o in objects_with(parse_next_rsc(html), 'combat_power'):
        if 'nickname' not in o:
            continue
        rows.append(dict(
            rank=o.get('global_rank') or o.get('rank'),
            nickname=o.get('nickname'), guild=o.get('guild') or '',
            job=o.get('job') or '', level=o.get('level'),
            combatPower=o.get('combat_power'), popularity=o.get('popularity'),
            server=('Scania ' + str(o['channel'])) if o.get('channel') else None))
    return rows


_KO = {'만': 10**4, '억': 10**8, '조': 10**12, '경': 10**16, '해': 10**20, '자': 10**24}


def _cp(s):
    tot = 0
    for num, unit in re.findall(r'([0-9,]+)\s*(자|해|경|조|억|만)', s):
        tot += int(num.replace(',', '')) * _KO[unit]
    return tot or None


def _txt(m):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m))).strip()


def _cls(tr, name):
    m = re.search(r'class="[^"]*\b' + name + r'\b[^"]*"[^>]*>(.*?)</', tr, re.S)
    return _txt(m.group(1)) if m else None


def adapt_mgf(html_text):
    """mgf.gg 랭킹 표. CSS 클래스로 셀을 집는다. power-tooltip 은 전투력이
    중복되므로 power-kor(요약 표기)만 읽는다. 한 페이지 = 30행."""
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', html_text, re.S):
        if 'power-kor' not in tr:
            continue
        rk = re.search(r'\d+', _cls(tr, 'rank-total') or '')
        lv = re.search(r'\d+', _cls(tr, 'level') or '')
        pop = re.search(r'[\d,]+', _cls(tr, 'badge-pop') or '')
        pk = re.search(r'class="[^"]*power-kor[^"]*"[^>]*>(.*?)</', tr, re.S)
        rows.append(dict(
            rank=int(rk.group()) if rk else None,
            nickname=_cls(tr, 'nickname'), guild=_cls(tr, 'badge-guild') or '',
            job=_cls(tr, 'job-name'), level=int(lv.group()) if lv else None,
            popularity=int(pop.group().replace(',', '')) if pop else None,
            server=_cls(tr, 'server-badge'),
            combatPower=_cp(_txt(pk.group(1))) if pk else None))
    return [r for r in rows if r['nickname'] and r['combatPower']]


ADAPTERS = {'mekipick': adapt_mekipick, 'mgf': adapt_mgf}


def load_conf():
    if not os.path.exists(CONF):
        sys.exit(f'설정이 없다: {os.path.relpath(CONF, ROOT)}')
    return json.load(open(CONF, encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    conf = load_conf()

    if a.status:
        print('설정:')
        for s in conf['sources']:
            print(f"  {s['id']:<12} enabled={s['enabled']}  {s.get('note','')}")
        if os.path.exists(OUT):
            d = json.load(open(OUT, encoding='utf-8'))
            print(f"\n마지막 수집: {d.get('collectedAt')} · {len(d.get('rows', []))}행"
                  f" · 출처 {d.get('source')}")
        else:
            print('\n아직 수집한 적 없음')
        return

    on = [s for s in conf['sources'] if s.get('enabled')]
    if not on:
        print('켜진 출처가 없다. 이건 기본값이다 — 남의 데이터를 옮겨오는 일이라')
        print('상대 사이트 동의를 받고 tools/ranking-sources.json 에서 enabled 를 켜라.')
        print('연락처는 그 파일에 적어 뒀다. 지금은 등록형 보드가 랭킹을 맡는다.')
        return

    delay = float(conf.get('delaySeconds', 2))
    allrows, used, hits = [], [], 0
    for s in on:
        fn = ADAPTERS.get(s['adapter'])
        if not fn:
            print(f"  ! 어댑터 없음: {s['adapter']}", file=sys.stderr); continue
        if s.get('urlTemplate') and s.get('pages'):
            urls = [s['urlTemplate'].format(page=i) for i in range(1, int(s['pages']) + 1)]
        else:
            urls = s.get('urls', [])
        for url in urls:
            try:
                html, cached = get(url, delay)
            except urllib.error.HTTPError as e:
                print(f"  ! {url} HTTP {e.code}", file=sys.stderr); continue
            except Exception as e:
                print(f"  ! {url} {type(e).__name__}", file=sys.stderr); continue
            hits += 0 if cached else 1
            got = fn(html)
            for r in got:
                allrows.append({k: r.get(k) for k in KEEP})
            print(f"  {url} -> {len(got)}행{' (캐시)' if cached else ''}")
        used.append(dict(id=s['id'], name=s['name'], url=s['site'], license=s.get('license')))

    # 닉네임 기준 중복 제거 후 전투력 순
    seen, rows = set(), []
    for r in sorted(allrows, key=lambda x: -(x.get('combatPower') or 0)):
        n = r.get('nickname')
        if not n or n in seen:
            continue
        seen.add(n); r['rank'] = len(rows) + 1; rows.append(r)

    out = dict(source=used, collectedAt=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               rows=rows, note='출처 표기 없이 재배포하지 말 것')
    print(f"\n{len(rows)}행 · 요청 {hits}건 · 출처 {[u['id'] for u in used]}")
    if a.dry:
        print('--dry 라 저장하지 않음'); return
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"-> {os.path.relpath(OUT, ROOT)}")


main()
