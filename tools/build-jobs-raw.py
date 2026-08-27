#!/usr/bin/env python3
"""클라이언트 원본 SkillTable -> data/job-skills.json

팬사이트 job-skill-impact.json 대신 원본에서 직접 조립한다.
- 스킬 인덱스 CSSS: C=직업(HeroTable.CreatureIndex), S=차수
- Values[0] 는 1000분율 (표시% x 10)
- ValueLevelFactors 로 스킬 레벨 계수 컬럼을 얻는다
- 투사체 스킬은 CreateProjectile -> SkillProjectileTable -> 해당 스킬의 피해 연산
"""
import json, os, re, collections

ROOT = os.path.join(os.path.dirname(__file__), '..')
SRC  = os.path.join(ROOT, 'reference', 'client')
load = lambda n: json.load(open(os.path.join(SRC, n + '.json'), encoding='utf-8'))

SK = {}
for t in ('SkillTable', 'SkillTable1', 'SkillTable2'):
    for x in load(t): SK[x['SkillIndex']] = x
HERO = {h['CreatureIndex']: h for h in load('HeroTable') if h.get('IsCreatable') != 'False'}
LVF  = {int(x['Level']): x['Factor'] for x in load('SkillLevelFactorTable')}
MAST = load('HeroSkillMasteryTable')

KO = {'Hero':'히어로','Paladin':'팔라딘','DarkKnight':'다크나이트',
      'ArchMageIL':'아크메이지(썬,콜)','ArchMageFP':'아크메이지(불,독)','Bishop':'비숍',
      'BowMaster':'보우마스터','Marksman':'신궁','NightLord':'나이트로드','Shadower':'섀도어',
      'Viper':'바이퍼','Captain':'캡틴','NightWalker':'나이트워커','WindBreaker':'윈드브레이커'}
FAM = {'Str':'전사','Int':'법사','Dex':'궁수','Luk':'도적'}

# 마스터리가 스킬에 더하는 피해량 (GiveDamagePower) 과 타겟 수
mast_dmg = collections.defaultdict(float)
mast_tgt = collections.defaultdict(int)
for m in MAST:
    si = m.get('SkillIndex')
    x  = SK.get(si) if si else None
    if not x: continue
    for o in (x.get('Operations') or []):
        if not o: continue
        v = o.get('Values') or []
        if o.get('Type') == 'ModSkillStat' and len(v) >= 4 and 'DamagePower' in str(v[2]):
            mast_dmg[v[0]] += float(v[3])
        if o.get('Type') == 'ModSkill' and len(v) >= 4 and v[2] == 'MaxHitCount':
            mast_tgt[v[0]] += int(float(v[3]))

# 부모 스킬 -> 자식(실제 피해) 스킬 연결.
# 64030 Genesis(쿨 23s) --UseSkillToTarget--> 64031(700% x6)
# 64060 Bahamute(쿨 80s) --CreateProjectile--> 투사체 -> 64061(3500%)
PROJ = {x['ProjectileIndex']: x for x in load('SkillProjectileTable')}
PARENT = {}
for pi, px in SK.items():
    for o in (px.get('Operations') or []):
        if not o: continue
        vals = [str(v) for v in (o.get('Values') or [])]
        ty = o.get('Type') or ''
        if ty.startswith('UseSkill') and vals:
            PARENT.setdefault(vals[0], pi)
        elif ty == 'CreateProjectile' and vals:
            # 투사체 인덱스와 같은 번호대의 피해 스킬을 자식으로 본다
            for cand in (vals[0], str(int(vals[0]) + 1)):
                if cand in SK and cand != pi:
                    PARENT.setdefault(cand, pi)
    if px.get('NextSkillIndex'):
        PARENT.setdefault(str(px['NextSkillIndex']), pi)

def inherit(si, x):
    """자식 스킬은 부모의 쿨타임·지속시간·기본공격 플래그를 물려받는다."""
    seen = set()
    cur = si
    while cur in PARENT and cur not in seen:
        seen.add(cur)
        cur = PARENT[cur]
        px = SK.get(cur)
        if not px: break
        if num(px.get('CoolTimeMs')):
            return px
    return x

def num(v):
    try: return float(str(v))
    except Exception: return None

def dmg_ops(x):
    """스킬에서 (계수1000분율, 타격수, 최대타겟, 레벨계수컬럼) 을 뽑는다."""
    out = []
    for o in (x.get('Operations') or []):
        if not o or o.get('Type') not in ('GetDamageR', 'GetDamage'): continue
        vals = o.get('Values') or []
        dp = num(vals[0]) if vals else None
        if dp is None: continue
        hc = 1
        if len(vals) >= 3:
            h = num(vals[2])
            if h: hc = int(h)
        vlf = o.get('ValueLevelFactors') or []
        col = None
        for c in vlf:
            ci = num(c)
            if ci and int(ci) in (12, 21, 22, 23): col = int(ci); break
        out.append(dict(dp=dp, hc=hc, tg=int(num(o.get('MaxHitCount')) or 1), col=col))
    return out

# MaxHitCount 가 비어 있는 스킬은 설명문(툴팁)의 '대상 N' 을 대신 쓴다.
# 예: Genesis 64031 은 MaxHitCount 가 없지만 설명문상 10 대상.
DESC_TGT = {}
_jsi = os.path.join(ROOT, '..', 'jsi.json')
for cand in (_jsi, '/tmp/claude-1000/-home-yuri/5ef6e679-7400-4ddd-b63f-3179cd77f600/scratchpad/jsi.json'):
    if os.path.exists(cand):
        for j in json.load(open(cand, encoding='utf-8'))['jobs']:
            for sk in j['skills']:
                d = sk.get('description') or ''
                m = re.search(r'(\d+)\s+(?:nearby\s+|allied\s+|random\s+)?target\(s\)', d)
                if m: DESC_TGT[str(sk['skillIndex'])] = int(m.group(1))
        break

jobs = []
for ci, h in sorted(HERO.items(), key=lambda kv: int(kv[0])):
    cls = h.get('ClassType')
    if cls not in KO: continue
    skills = []
    for si, x in SK.items():
        # CreatureIndex 가 1자리면 5자리 스킬(61010), 2자리면 6자리(101010)
        if not (si.isdigit() and len(si) == len(ci) + 4 and si.startswith(ci)): continue
        step = int(si[len(ci)])
        if step < 1 or step > 4: continue
        src = inherit(si, x)                       # 쿨타임 보유 부모
        flag = (x.get('TriggerFlag') or '') + ',' + (src.get('TriggerFlag') or '')
        for d in dmg_ops(x):
            skills.append(dict(
                idx=si, n=x.get('ActionName') or si, step=step,
                dp=(d['dp'] + mast_dmg.get(si, 0)) / 10.0,      # 표시 %
                hc=d['hc'],
                tg=(d['tg'] if d['tg'] > 1 else
                    DESC_TGT.get(si) or DESC_TGT.get(PARENT.get(si, ''), d['tg'])) + mast_tgt.get(si, 0),
                col=d['col'] or 21,
                cd=int(num(src.get('CoolTimeMs')) or num(x.get('CoolTimeMs')) or 0),
                du=int(num(x.get('DurationTimeMs')) or num(src.get('DurationTimeMs')) or 0),
                b=1 if 'ReplaceBaseAttack' in flag else 0,
                tt=x.get('TriggerType'),
                tr=int(num(x.get('TriggerRatio')) or 1000),
                cond=1 if x.get('TriggerCondition') else 0,
            ))
    jobs.append(dict(id=re.sub(r'(?<!^)(?=[A-Z])', '-', cls).lower(), ct=cls,
                     ko=KO[cls], fam=FAM.get(h.get('MainStat'), h.get('MainStat')),
                     main=h.get('MainStat'), conv=h.get('StatConversion'),
                     skills=skills, nSkill=len(skills)))

out = dict(meta=dict(source='client SkillTable (raw)', appVersion='1.14.0',
                     note='마스터리 GiveDamagePower/MaxHitCount 합산 반영. 계수는 표시 % 단위.'),
           levelFactor={str(k): v for k, v in LVF.items() if k <= 400},
           jobs=jobs)
json.dump(out, open(os.path.join(ROOT, 'data', 'job-skills.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print(f"직업 {len(jobs)} · 딜 연산 {sum(j['nSkill'] for j in jobs)}")
for j in jobs:
    b = [s for s in j['skills'] if s['b']]
    print(f"  {j['ko']:<18}{j['nSkill']:>3}개  기본공격체인 {len(b)}  최대계수 {max((s['dp'] for s in j['skills']), default=0):,.0f}%")
