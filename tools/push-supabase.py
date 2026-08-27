#!/usr/bin/env python3
"""data/ranking.json (수집기가 만든 행) -> Supabase rankings 테이블 업서트.

쓰기는 service_role 키가 필요하다(공개 publishable 키로는 RLS 때문에 못 쓴다).
그 키는 GitHub Actions 비밀(SUPABASE_SERVICE_KEY)로만 주고, 코드/저장소엔 절대 안 넣는다.
로컬에서 돌릴 땐 환경변수로 준다:  SUPABASE_SERVICE_KEY=... python3 tools/push-supabase.py
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, 'data', 'supabase.json'), encoding='utf-8'))
URL = CONF['url'].rstrip('/') + '/rest/v1/rankings'
KEY = os.environ.get('SUPABASE_SERVICE_KEY', '').strip()

def chunks(a, n):
    for i in range(0, len(a), n):
        yield a[i:i + n]

def main():
    if not KEY:
        print('SUPABASE_SERVICE_KEY 환경변수가 없다 — 업서트 건너뜀.', file=sys.stderr)
        return
    rows = json.load(open(os.path.join(ROOT, 'data', 'ranking.json'), encoding='utf-8')).get('rows', [])
    if not rows:
        print('올릴 행이 없다.'); return
    payload = [dict(nickname=r['nickname'], rank=r.get('rank'), guild=r.get('guild') or '',
                    job=r.get('job') or '', level=r.get('level'),
                    combat_power=r.get('combatPower'), popularity=r.get('popularity'),
                    server=r.get('server') or '') for r in rows if r.get('nickname')]
    sent = 0
    for part in chunks(payload, 1000):
        req = urllib.request.Request(URL, data=json.dumps(part).encode('utf-8'),
            headers={'apikey': KEY, 'Authorization': 'Bearer ' + KEY,
                     'Content-Type': 'application/json',
                     'Prefer': 'resolution=merge-duplicates,return=minimal'})
        with urllib.request.urlopen(req, timeout=40) as r:
            if r.status not in (200, 201, 204):
                print('업서트 실패', r.status, file=sys.stderr); sys.exit(1)
        sent += len(part)
        print(f'  업서트 {sent}/{len(payload)}')
    print(f'Supabase 업서트 완료 · {sent}행')

main()
