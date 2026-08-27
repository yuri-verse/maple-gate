#!/usr/bin/env python3
"""클라이언트 원본 테이블 -> data/stages.json

팬사이트 파생본(target-context-model)은 캠프 슬롯 20개를 고유 패밀리 5개로 압축해
몬스터 수를 58 -> 13 으로 과소집계한다(44-2 기준 총 HP 3.12배 차이).
이 스크립트는 DungeonTable 부터 직접 조립한다.

  DungeonTable.OverrideFamilyIndex[CampIndex] -> CampFamilyTable
  MapDefine.Camps[CampIndex-1].InitTimeMs     -> 등장 시각
  CreatureStatTable x MonsterTierTable/1000   -> 실제 몬스터 스탯
"""
import json, os, re, collections

ROOT = os.path.join(os.path.dirname(__file__), '..')
SRC  = os.path.join(ROOT, 'reference', 'client')
OUT  = os.path.join(ROOT, 'data', 'stages.json')

def load(name):
    p = os.path.join(SRC, name + '.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None

def sig(x, n=7):
    """유효숫자 n자리로 반올림. 2^53 초과 정수의 표시 오차를 막는다."""
    if not x: return 0
    import math
    e = math.floor(math.log10(abs(x)))
    p = n - 1 - e
    return round(x, p) if p > 0 else round(x / 10**(-p)) * 10**(-p)

# ---------- 원본 테이블 ----------
DUNGEON = load('DungeonTable')
CSTAT   = {x['CreatureIndex']: x.get('Stat', {}) for x in load('CreatureStatTable')}
CREAT   = {x['CreatureIndex']: x for x in load('CreatureTable')}
TIER    = {x['TierIndex']: x.get('StatRatio', {}) for x in load('MonsterTierTable')}
CAMP    = {}
for t in ('CampFamilyTable', 'CampFamilyTable1'):
    for x in (load(t) or []):
        CAMP[x['FamilyIndex']] = x

# CodeName -> 영문명 (팬사이트 monsterIndex 를 이름 조회에만 사용)
NAME = {}
_tcm = os.path.join(ROOT, '..', 'tcm.json')
for cand in (_tcm, '/tmp/claude-1000/-home-yuri/5ef6e679-7400-4ddd-b63f-3179cd77f600/scratchpad/tcm.json'):
    if os.path.exists(cand):
        for m in json.load(open(cand, encoding='utf-8'))['targets']:
            for mo in m['monsters']:
                NAME[mo.get('codeName')] = mo.get('name')
        break

MAPCACHE = {}
def mapdef(fn):
    if fn not in MAPCACHE:
        MAPCACHE[fn] = load(re.sub(r'\.json$', '', fn)) or {}
    return MAPCACHE[fn]

STAT_KEYS = ('MaxHp','Attack','Defence','HitChance','AvoidChance','RunSpeedMms',
             'CriticalChance','CriticalPower','PiercePower','Toughness','Weakness',
             'MinDamageRatio','MaxDamageRatio','MaxMp')

def monster_stat(ci, ti):
    """기본 스탯 x 등급 배율 / 1000. 배율이 없는 항목은 기본값 그대로."""
    base  = CSTAT.get(ci, {})
    ratio = TIER.get(ti, {})
    out = {}
    for k in STAT_KEYS:
        b = float(base.get(k, 0) or 0)
        r = float(ratio.get(k, 1000) or 1000)
        v = b * r / 1000
        if v: out[k] = sig(v)
    return out

FAM_KO = {
    'Campaign':'챕터', 'Trial':'돌파', 'Boss':'챕터 보스',
}
def classify(d):
    flags = (d.get('DungeonFlag') or '')
    if d.get('IsTrial') == 'True' or 'RushMode' in flags: return '돌파'
    if 'IsCampaignBoss' in flags: return '챕터 보스'
    return '사냥'

stages = []
for d in DUNGEON:
    ch, dg = d['ChapterIndex'], d['DungeonIndex']
    if ch == '99999999': continue                       # 테스트 던전
    ofi = d.get('OverrideFamilyIndex') or []
    md  = mapdef(d.get('MapDefineFileName') or '')
    mcamps = {int(c['CampIndex']): c for c in (md.get('Camps') or [])}

    # 출구 = 지형(IsGround) 왼쪽 끝. 몬스터는 스폰 지점에서 왼쪽으로 걸어간다.
    # 세 돌파 맵 모두 스폰~출구 21,500~21,640mm 로 일관되며,
    # 보스 이동속도 675mm/s 기준 전투 길이 19+32=51초 (실측 40초~1분과 일치).
    exit_mm = None
    try:
        gx = [float(pl['StartPoint'].split(',')[0]) for pl in (md.get('Platforms') or [])
              if pl.get('IsGround')]
        cx = [float(c['Position'].split(',')[0]) for c in (md.get('Camps') or [])]
        if gx and cx: exit_mm = abs(max(cx) - min(gx))
    except Exception:
        exit_mm = None

    camps = []
    for idx in range(1, len(ofi)):
        fam = ofi[idx]
        if not fam: continue
        fd = CAMP.get(fam)
        if not fd: continue
        mc = mcamps.get(idx, {})
        mons = []
        for m in fd.get('Monster', []):
            ci, ti = m['CreatureIndex'], m['TierIndex']
            cr = CREAT.get(ci, {})
            mons.append({
                'ci': ci, 'ti': ti,
                'name': NAME.get(cr.get('CodeName')) or cr.get('CodeName') or ci,
                'code': cr.get('CodeName'),
                'cnt': int(m.get('SpawnCount', 1)),
                'boss': m.get('IsBoss') == 'True',
                'skills': [str(s) for s in (m.get('ExtraSkill') or [])],
                'base': cr.get('BaseAttack'),
                'stat': monster_stat(ci, ti),
            })
        camps.append({'i': idx, 't': int(mc.get('InitTimeMs', 0) or 0), 'fam': fam, 'm': mons})

    if not camps: continue
    cc  = d.get('ClearCondition') or []
    tl  = None; ctype = None
    for c in cc:
        v = (c.get('TimeLimitMs') or [None])[0]
        if v and (tl is None or int(v) < tl): tl = int(v)
        ctype = ctype or c.get('Type')

    allm  = [(m, c) for c in camps for m in c['m']]
    tot   = sum(m['stat'].get('MaxHp', 0) * m['cnt'] for m, _ in allm)
    bhp   = sum(m['stat'].get('MaxHp', 0) * m['cnt'] for m, _ in allm if m['boss'])
    spawn = sum(m['cnt'] for m, _ in allm)

    stages.append({
        'id': f'{ch}-{dg}', 'ch': int(ch), 'dg': int(dg),
        'mode': classify(d),
        'map': d.get('MapDefineFileName'),
        'bd': d.get('BattleDefineCode'),
        'tl': tl, 'ct': ctype,
        'flags': [f for f in (d.get('DungeonFlag') or '').split(',') if f],
        'maxAcc': int((d.get('CampSpawn') or {}).get('MaxAccMonsterCount', 0) or 0),
        'bossTimer': int(d.get('BossSpawnTimerMs') or 0),
        'bpr': (d.get('BattlePowerRuleCode') or [None])[0] if isinstance(d.get('BattlePowerRuleCode'), list) else d.get('BattlePowerRuleCode'),
        'wave': d.get('WaveDefineCodes'),
        'exitMm': round(exit_mm) if exit_mm else None,
        'hp': sig(tot), 'bhp': sig(bhp), 'spawn': spawn,
        'nCamp': len(camps),
        'def': max((m['stat'].get('Defence', 0) for m, _ in allm), default=0),
        'eva': max((m['stat'].get('AvoidChance', 0) for m, _ in allm), default=0),
        'camps': camps,
    })

meta = {
    'source': 'client tables (tables_assets_all.bundle)',
    'appVersion': '1.14.0', 'appVersionCode': 10003329,
    'stages': len(stages),
    'note': '팬사이트 파생본이 아니라 DungeonTable/CampFamilyTable/MonsterTierTable 원본에서 조립.',
}
json.dump({'meta': meta, 'stages': stages}, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))

print(f"스테이지 {len(stages)}개 -> {OUT}  ({os.path.getsize(OUT)/1e6:.1f}MB)")
bym = collections.Counter(s['mode'] for s in stages)
print("모드:", dict(bym))
print("캠프 수 분포:", dict(collections.Counter(s['nCamp'] for s in stages).most_common(6)))
