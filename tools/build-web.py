#!/usr/bin/env python3
"""data/stages.json + data/job-skills.json -> data/web-data.json (웹용 압축본)"""
import json, os, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = lambda p: json.load(open(os.path.join(ROOT, p), encoding='utf-8'))

def sig(x, n=6):
    if not x: return 0
    e = math.floor(math.log10(abs(x))); p = n - 1 - e
    return round(x, p) if p > 0 else round(x / 10**(-p)) * 10**(-p)

ST = L('data/stages.json')['stages']
JS = L('data/job-skills.json')
GAP = L('data/site-data.json')['gap']
SUP = L('data/supporters.json')
SRC_ = os.path.join(ROOT, 'reference', 'client')
cl = lambda n: json.load(open(os.path.join(SRC_, n + '.json'), encoding='utf-8'))
STARF = [dict(sf=int(x['StarForce']),
              main=float(x.get('MainOptionMultiply') or 0)/10,
              sub=float(x.get('SubOptionMultiply') or 0)/10,
              ok=float(x.get('SuccessProb') or 0)/10000,
              down=float(x.get('DownProb') or 0)/10000,
              boom=float(x.get('DestroyProb') or 0)/10000,
              cost=[[c.get('Value'), int(c.get('Count') or 0)] for c in (x.get('Costs') or [])])
         for x in cl('StarForceTable')]
CUBE = [dict(part=x['GearPartType'], grade=x['GearSlotAbilityGradeType'],
             next=x.get('NextGearSlotAbilityGradeType'),
             prob=float(x.get('GradeUpProb') or 0)/10000,
             pity=int(x.get('GradeUpChangeCount') or 0),
             cost=[[c.get('Value'), int(c.get('Count') or 0)] for c in (x.get('ChangeCosts') or [])])
        for x in cl('GearAbilityGradeTable')]
SUPCOST = cl('SupporterLevelUpCostTable')
# SupporterLevelUpCostTable.MaxLevel (클라이언트 추출값, 라이브 상한과 일치 여부 미확인)
MAXLVL = {'Grade1':100,'Grade2':50,'Grade3':30,'Grade4':10,'Grade5':16}

names = {}
def nid(s):
    if s not in names: names[s] = len(names)
    return names[s]

stages = []
for s in ST:
    if s['mode'] == '사냥' and not s['tl']:
        camps = []                                  # 사냥은 스폰 타이밍이 무의미
    else:
        camps = [[c['t'],
                  [[nid(m['name']), m['cnt'], sig(m['stat'].get('MaxHp', 0)),
                    1 if m['boss'] else 0, int(m['stat'].get('RunSpeedMms') or 1000)]
                   for m in c['m']]]
                 for c in s['camps']]
    stages.append(dict(
        id=s['id'], ch=s['ch'], dg=s['dg'], mode=s['mode'], map=s['map'],
        tl=s['tl'], ct=s['ct'], flags=s['flags'], exitMm=s.get('exitMm'),
        hp=sig(s['hp']), bhp=sig(s['bhp']), spawn=s['spawn'], nCamp=s['nCamp'],
        df=s['def'], ev=s['eva'], camps=camps,
    ))

jobs = [dict(id=j['id'], ko=j['ko'], fam=j['fam'], main=j['main'],
             skills=[dict(n=str(x['n'])[:24], dp=x['dp'], hc=x['hc'], tg=x['tg'],
                          cd=x['cd'], du=x['du'], b=x['b'], step=x['step'], col=x['col'])
                     for x in j['skills']])
        for j in JS['jobs']]

sups = [dict(code=x['code'], ko=x['ko'], grade=x['grade'], gradeKey=x['gradeKey'],
             dur=x['dur'], inheritCol=x['inheritCol'],
             skills=[dict(n=str(k['n'])[:22], dp=k['dp'], hc=k['hc'], tg=k['tg'],
                          cd=k['cd'], du=k['du'], dot=k['dot'], op=k.get('op',1)) for k in x['skills']],
             buffs=[b for b in x['buffs']
                    if b['stat'] in ('Attack','AttackPower','FinalDamage','CriticalPower',
                                     'CriticalChance','AttackSpeed','MaxDamageRatio',
                                     'MinDamageRatio','SkillPower','BaseAttackPower',
                                     'AttackPowerToBoss','AttackPowerExcludeBoss','MainStatR')],
             opts=x['opts'])
        for x in SUP['supporters'] if x['skills']]

out = dict(
    meta=dict(appVersion='1.14.0', source='client tables',
              stages=len(stages), jobs=len(jobs),
              finalAttack=1.25, defaultR=2.80),
    names=[k for k, _ in sorted(names.items(), key=lambda kv: kv[1])],
    gap=GAP,
    levelFactor={k: v for k, v in JS['levelFactor'].items() if int(k) <= 400},
    jobs=jobs, stages=stages,
    supporters=sups, supLevelFactor=SUP['levelFactor'],
    starforce=STARF, cube=CUBE, supCost=SUPCOST, supMaxLv=MAXLVL,
)
p = os.path.join(ROOT, 'data', 'web-data.json')
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f"{os.path.getsize(p)/1e6:.1f}MB · 스테이지 {len(stages)} · 직업 {len(jobs)} · 동료 {len(sups)} · 이름 {len(names)}")
