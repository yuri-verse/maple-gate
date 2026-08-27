#!/usr/bin/env python3
"""data/stages.json + 유물 테이블 -> data/dex.json (몬스터 도감 · 유물 도감)

몬스터는 스테이지에 실제로 등장하는 것만 담는다. 같은 몬스터가 티어별로 여러 번 나와서
스탯이 구간으로 잡히므로 최소~최대를 같이 싣는다.

이름은 커뮤니티 파생본(tcm.json)에서 온 영문명이다 — 클라이언트의 한글 이름은
Localization 테이블에 암호화돼 있어 쓰지 않는다(복호화는 조사 범위 밖).
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'reference', 'client')
L = lambda p: json.load(open(os.path.join(ROOT, p), encoding='utf-8'))
cl = lambda n: json.load(open(os.path.join(SRC, n + '.json'), encoding='utf-8'))

def sig(x, n=5):
    if not x: return 0
    e = math.floor(math.log10(abs(x))); p = n - 1 - e
    return round(x, p) if p > 0 else round(x / 10**(-p)) * 10**(-p)

# ---------- 몬스터 ----------
# 아틀라스 스프라이트 이름은 CodeName 이 아니라 CreatureTable.PortraitIconPath 가 정한다
# ("MonsterPortrait:1210102"). CodeName 이 숫자가 아닌 몬스터가 99종 있어서 직접 파싱하면 샌다.
ICON = {}
for x in cl('CreatureTable'):
    ip = x.get('PortraitIconPath') or ''
    if ':' in ip: ICON[x['CreatureIndex']] = ip.split(':', 1)[1]

agg = {}
for s in L('data/stages.json')['stages']:
    for c in s.get('camps') or []:
        for m in c['m']:
            nm = (m['name'] or '').split('.')[-1].strip()   # 일부는 'Monster.Zakum Rarm1' 로 들어온다
            r = agg.setdefault(m['ci'], dict(n=nm, ic=ICON.get(m['ci'], ''),
                                             code=m['code'].split('.')[-1],
                                             boss=False, st=set(), ch=set(),
                                             hp=[], df=[], ev=[], sp=[]))
            r['boss'] |= bool(m['boss'])
            r['st'].add(s['id']); r['ch'].add(s['ch'])
            t = m['stat']
            r['hp'].append(t.get('MaxHp') or 0)
            r['df'].append(t.get('Defence') or 0)
            r['ev'].append(t.get('AvoidChance') or 0)
            r['sp'].append(t.get('RunSpeedMms') or 0)

def rng(v):
    lo, hi = min(v), max(v)
    return [sig(lo), sig(hi)] if lo != hi else [sig(lo)]

mons = sorted(
    (dict(ci=k, n=v['n'], ic=v['ic'], code=v['code'], boss=1 if v['boss'] else 0,
          ns=len(v['st']), ch=[min(v['ch']), max(v['ch'])],
          hp=rng(v['hp']), df=rng(v['df']), ev=rng(v['ev']), sp=rng(v['sp']))
     for k, v in agg.items()),
    key=lambda x: (x['ch'][0], -x['boss'], x['hp'][0]))

# ---------- 유물 ----------
OPT = {x['OptionIndex']: x.get('StatData', {}) for x in cl('ArtifactOptionTable')}
GK = {'Grade1': '노말', 'Grade2': '레어', 'Grade3': '에픽', 'Grade4': '유니크',
      'Grade5': '레전드리', 'Grade6': '미스틱'}
arts = [dict(code=x['ArtifactCode'], grade=GK.get(x['GradeType'], x['GradeType']),
             gradeKey=x['GradeType'],
             nSkill=len(x.get('EquipSkillIndices') or []),
             opts=[dict(stat=OPT[i].get('Type'), val=float(OPT[i].get('Value') or 0),
                        factor=int(OPT[i].get('Factor') or 0))
                   for i in (x.get('CollectionOptionIndices') or []) if i in OPT])
        for x in cl('ArtifactTable')]
upg = [dict(grade=GK.get(x['Grade'], x['Grade']), need=int(x['UpgradeRequiredCount']),
            to=GK.get(x.get('UpgradeGradeType'), x.get('UpgradeGradeType')))
       for x in cl('ArtifactUpgradeTable')]
power = [dict(stat=x['StatData'].get('Type'), val=float(x['StatData'].get('Value') or 0),
              factor=int(x['StatData'].get('Factor') or 0)) for x in cl('ArtifactPowerTable')]

out = dict(monsters=mons, artifacts=arts, artUpgrade=upg, artPower=power)
p = os.path.join(ROOT, 'data', 'dex.json')
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
noic = sum(1 for m in mons if not m['ic'])
print(f"dex.json {os.path.getsize(p)/1024:.0f}KB · 몬스터 {len(mons)} (보스 {sum(m['boss'] for m in mons)})"
      f" · 유물 {len(arts)}" + (f" · 아이콘 경로 없음 {noic}" if noic else ""))
