import json, math

tcm = json.load(open('tcm.json'))
gsr = json.load(open('gsr.json'))

FAM_KO = {
 'chapter-hunt-or-breakthrough':'챕터','chapter-boss':'챕터 보스','growth-dungeon':'성장 던전',
 'job-step-dungeon':'전직 던전','party-quest':'파티 퀘스트','world-boss':'월드 보스',
 'boss-raid':'보스 레이드','guild-boss':'길드 보스','guild-raid':'길드 레이드',
 'guild-training':'길드 수련장','guild-village':'길드 마을','guild-raid-village':'길드 마을',
 'star-force-field':'스타포스 사냥터','pvp-or-score':'PvP · 스코어','world-arena':'월드 아레나',
 'village':'마을','event-raid':'이벤트 레이드','flag-racing':'깃발 뺏기','maple-beach':'메이플 비치',
}
COND_KO = {
 'RushDefence':'돌파 방어','KillBoss':'보스 처치','KillAllEnemies':'전멸','KillCount':'처치 수',
 'ItemDropCount':'아이템 획득','DefenceArena':'아레나 방어','ArriveGoal':'목표 도달','HighScore':'점수',
}

def sig(x, n=7):
    if x is None: return None
    if x == 0: return 0
    if isinstance(x, int) and abs(x) < 2**53: 
        pass
    e = math.floor(math.log10(abs(x)))
    p = n - 1 - e
    v = round(x, p) if p > 0 else round(x / 10**(-p)) * 10**(-p)
    return v

names = {}
def nid(s):
    if s not in names: names[s] = len(names)
    return names[s]

stages = []
for x in tcm['targets']:
    md = x['metadata']; b = x['battle']; st = x['stats']
    fam = md['contentFamily']
    ccs = b['clearConditions'] or []
    tl = None; ctype = None
    for c in ccs:
        t = (c.get('TimeLimitMs') or [None])[0]
        if t and (tl is None or t < tl): tl = t
        if ctype is None: ctype = c.get('Type')
    dflags = b['flags'].get('dungeon') or []
    if fam == 'chapter-hunt-or-breakthrough':
        mode = '돌파' if 'RushMode' in dflags else '사냥'
    elif fam == 'chapter-boss':
        mode = '보스'
    else:
        mode = FAM_KO.get(fam, fam)

    mons = []
    total = 0.0
    for m in x['monsters']:
        s = m['stats']
        hp = s.get('MaxHp') or 0
        cnt = m.get('spawnCount') or 0
        total += hp * cnt
        mons.append([nid(m['name']), cnt, sig(hp), s.get('Defence'), s.get('AvoidChance'),
                     1 if m['boss'] else 0, sig(s.get('Attack'))])
    stages.append({
        'id': x['id'], 'ch': x['chapter'], 'dg': x['dungeon'],
        'fam': FAM_KO.get(fam, fam), 'mode': mode,
        'lbl': x['label'], 'map': x['mapKey'],
        'tl': tl, 'ct': COND_KO.get(ctype, ctype),
        'hp': sig(total), 'def': st['maxDefense'], 'eva': st['maxEvasion'],
        'bdef': st['maxBossDefense'], 'beva': st['maxBossEvasion'],
        'bhp': sig(st['maxBossHp']), 'sp': st['totalSpawnCount'], 'bsp': st['bossSpawnCount'],
        'bpr': b['battlePowerRuleCode'],
        'fl': [f for f in dflags if f in ('RushMode','NoUserDie','CannotUsePassive','NoSupporter',
               'NoBattlePotion','CannotAutoSkill','IsCampaignBoss','KillScore','DisableSkillSlot')],
        'm': mons,
    })

gap = [[r['gap'], r['evadePercent']] for r in gsr['gapCurves']['rows']]
rules = [{'stat': r['stat'], 'label': r['label'], 'type': r['ruleType'],
          'conf': r['confidence'], 'say': r['gameStatement'], 'stack': r['stacking']}
         for r in gsr['exactRules']]

out = {
  'meta': {
    'appVersion': tcm['generatedFrom']['appVersion'],
    'appVersionCode': tcm['generatedFrom']['appVersionCode'],
    'snapshot': tcm['generatedFrom']['snapshotId'],
    'createdAtUtc': tcm['generatedFrom']['createdAtUtc'],
    'stages': len(stages),
    'monsterRows': sum(len(s['m']) for s in stages),
    'warning': tcm['warning'],
  },
  'names': [k for k, v in sorted(names.items(), key=lambda kv: kv[1])],
  'gap': gap,
  'rules': rules,
  'stages': stages,
}
json.dump(out, open('site-data.json','w'), ensure_ascii=False, separators=(',',':'))
print('stages', len(stages), 'names', len(names))
