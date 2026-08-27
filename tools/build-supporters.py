#!/usr/bin/env python3
"""동료(서포터) 데이터 -> data/supporters.json

동료는 소환되면 자기 전용 스킬 세트로 싸운다.
스킬 목록은 SupporterTable 의 명시 필드에서 읽는다 (이름 규칙 추측 아님):
  EnterSkillIndex / MainActiveSkillIndices / MainPassiveSkillIndices
  + OpenActiveSkillLevel / OpenPassiveSkillLevel = 스킬별 해금 레벨
자식 스킬(투사체/연계)은 PARENT 체인을 따라 위 목록에 걸리면 함께 포함한다.
공격력은 플레이어에게서 계승하고(SupporterLevelStatFactorTable Factor[8], 상한 90%),
그 외 공격 능력치는 플레이어 값을 그대로 쓴다 (공식 가이드 2.5).
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, 'reference', 'client')
load = lambda n: json.load(open(os.path.join(SRC, n + '.json'), encoding='utf-8'))

SK = {}
for t in ('SkillTable', 'SkillTable1', 'SkillTable2'):
    for x in load(t): SK[x['SkillIndex']] = x
SUP  = load('SupporterTable')
OPT  = {o['OptionIndex']: o for o in load('SupporterOptionTable')}
SLF  = {int(x['Level']): x['Factor'] for x in load('SupporterLevelStatFactorTable')}

KO = {'Hero':'히어로','Paladin':'팔라딘','DarkKnight':'다크나이트',
      'ArchMageIL':'아크메이지(썬,콜)','ArchMageFP':'아크메이지(불,독)','Bishop':'비숍',
      'BowMaster':'보우마스터','Marksman':'신궁','NightLord':'나이트로드','Shadower':'섀도어',
      'Viper':'바이퍼','Captain':'캡틴','NightWalker':'나이트워커','WindBreaker':'윈드브레이커'}
GRADE = {'Grade1':'노말','Grade2':'레어','Grade3':'에픽','Grade4':'유니크','Grade5':'레전드리'}

def num(v):
    try: return float(str(v))
    except Exception: return None

def dmg_ops(x):
    out = []
    for o in (x.get('Operations') or []):
        if not o or o.get('Type') not in ('GetDamageR', 'GetDamage'): continue
        vals = o.get('Values') or []
        dp = num(vals[0]) if vals else None
        if dp is None: continue
        hc = 1
        if len(vals) >= 3 and num(vals[2]): hc = int(num(vals[2]))
        dot = len(vals) >= 2 and str(vals[1]) == 'Dot'
        out.append(dict(dp=dp/10.0, hc=hc, tg=int(num(o.get('MaxHitCount')) or 1), dot=1 if dot else 0))
    return out

# 부모(쿨타임 보유) -> 자식(피해) 연결. 806440 Genesis --UseSkillToTarget--> 806441
PARENT = {}
for pi, px in SK.items():
    for o in (px.get('Operations') or []):
        if not o: continue
        v = [str(y) for y in (o.get('Values') or [])]
        ty = o.get('Type') or ''
        if ty.startswith('UseSkill') and v: PARENT.setdefault(v[0], pi)
        elif ty == 'CreateProjectile' and v:
            for c in (v[0], str(int(v[0]) + 1)):
                if c in SK and c != pi: PARENT.setdefault(c, pi)

def owner(si):
    cur, seen = si, set()
    while cur in PARENT and cur not in seen:
        seen.add(cur); cur = PARENT[cur]
        if num(SK.get(cur, {}).get('CoolTimeMs')): return SK[cur]
    return SK.get(si, {})

sups = []
for s_ in SUP:
    m = re.match(r'SUPPORTER_(\d+)_(\d+)', s_['SupporterCode'])
    if not m: continue

    # --- 명시 필드에서 스킬 목록 + 해금 레벨 ---
    declared = {}                                   # skillIndex -> 해금 레벨
    ent = str(s_.get('EnterSkillIndex') or '')
    if ent in SK: declared[ent] = 1
    for idxk, lvk in (('MainActiveSkillIndices', 'OpenActiveSkillLevel'),
                      ('MainPassiveSkillIndices', 'OpenPassiveSkillLevel')):
        ids = s_.get(idxk) or []
        lvs = s_.get(lvk) or []
        for i, sid in enumerate(ids):
            sid = str(sid)
            if sid not in SK: continue
            declared[sid] = int(num(lvs[i]) or 1) if i < len(lvs) else 1

    # 자식 스킬을 부모 체인으로 흡수 (예: 806440 --> 806441)
    members = dict(declared)
    for k in SK:
        if k in members: continue
        cur, seen = k, set()
        while cur in PARENT and cur not in seen:
            seen.add(cur); cur = PARENT[cur]
            if cur in declared:
                members[k] = declared[cur]; break

    skills, buffs = [], []
    for k in sorted(members, key=int):
        x = SK[k]
        src = owner(k)
        op = members[k]
        for d in dmg_ops(x):
            skills.append(dict(idx=k, n=(x.get('ActionName') or k), dp=d['dp'], hc=d['hc'],
                               tg=d['tg'], dot=d['dot'], op=op,
                               cd=int(num(src.get('CoolTimeMs')) or num(x.get('CoolTimeMs')) or 0),
                               du=int(num(x.get('DurationTimeMs')) or 1000)))
        for o in (x.get('Operations') or []):
            if not o: continue
            v = o.get('Values') or []
            if o.get('Type') in ('ModStat', 'ModStatR') and len(v) >= 2 and num(v[1]) is not None:
                buffs.append(dict(idx=k, stat=str(v[0]), val=num(v[1])/10.0, op=op,
                                  r=1 if o.get('Type') == 'ModStatR' else 0))
    opts = []
    for grp, ids in (('보유', s_.get('CollectionOptionIndices') or []),
                     ('장착', s_.get('EquipOptionIndices') or [])):
        for i in ids:
            o = OPT.get(str(i))
            if not o: continue
            sd = o.get('StatData') or {}
            opts.append(dict(grp=grp, stat=sd.get('Type'), val=num(sd.get('Value')),
                             factor=int(num(sd.get('Factor')) or 0)))
    sups.append(dict(code=s_['SupporterCode'], cls=s_['ClassType'], ko=KO.get(s_['ClassType'], s_['ClassType']),
                     grade=GRADE.get(s_['GradeType'], s_['GradeType']), gradeKey=s_['GradeType'],
                     dur=int(num(s_.get('SpawnDurationTimeMs')) or 30000),
                     inheritCol=int(num(s_.get('LinkedAttackStatLevelFactor')) or 8),
                     baseRatio=num(s_.get('LinkedAttackStatBaseRatio')) or 1000,
                     skills=skills, buffs=buffs, opts=opts))

out = dict(meta=dict(source='client SupporterTable + SkillTable', appVersion='1.14.0',
                     note='스킬 = SupporterTable.EnterSkillIndex/MainActive/MainPassiveSkillIndices (명시 필드). op = 해금 레벨.'),
           levelFactor={str(k): v for k, v in SLF.items() if k <= 300},
           supporters=sups)
json.dump(out, open(os.path.join(ROOT, 'data', 'supporters.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print(f"동료 {len(sups)}종 · 피해 스킬 {sum(len(x['skills']) for x in sups)} · 버프 {sum(len(x['buffs']) for x in sups)}")
for x in sups:
    if x['gradeKey'] == 'Grade5':
        top = max((s['dp'] for s in x['skills']), default=0)
        print(f"  {x['ko']:<18}{x['grade']:<8}딜스킬 {len(x['skills']):>2}  버프 {len(x['buffs']):>2}  최대계수 {top:,.0f}%")
