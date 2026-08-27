import json, re
src=json.load(open('jsi.json'))

KO={'Hero':'히어로','Paladin':'팔라딘','DarkKnight':'다크나이트',
    'ArchMageIL':'아크메이지(썬,콜)','ArchMageFP':'아크메이지(불,독)','Bishop':'비숍',
    'BowMaster':'보우마스터','Marksman':'신궁','NightLord':'나이트로드','Shadower':'섀도어',
    'Viper':'바이퍼','Captain':'캡틴','NightWalker':'나이트워커','WindBreaker':'윈드브레이커'}
FAM={'Warrior':'전사','Magician':'법사','Bowman':'궁수','Thief':'도적','Pirate':'해적'}

# ---- 설명문 파서: 투사체·소환 스킬의 피해값은 원본 테이블 대신 툴팁 문장에 들어 있습니다 ----
N=r'([\d,]+(?:\.\d+)?)'
RE_DMG   = re.compile(N+r'%\s+damage', re.I)
RE_TGT   = re.compile(N+r'\s+(?:nearby\s+|allied\s+|random\s+)?target\(s\)', re.I)
RE_TIME  = re.compile(N+r'\s+time\(s\)', re.I)
RE_EVERY = re.compile(r'every\s+'+N+r'\s+sec', re.I)
RE_DUR   = re.compile(r'(?:lasts?\s+(?:at[^.]*?)?(?:for\s+)?|for\s+|Sets up[^.]*?for\s+)'+N+r'\s+sec', re.I)
def f(x): return float(x.replace(',',''))

def parse_desc(desc):
    if not desc: return []
    out=[]
    for sent in [x for x in re.split(r'(?<=[.!?])\s+', desc) if x.strip()]:
        for m in RE_DMG.finditer(sent):
            tg=RE_TGT.search(sent)
            tm=RE_TIME.search(sent[m.end():m.end()+60]) or RE_TIME.search(sent)
            ev=RE_EVERY.search(sent); du=RE_DUR.search(sent) or RE_DUR.search(desc)
            out.append({'dp':f(m.group(1)),
                        'tg':int(f(tg.group(1))) if tg else 1,
                        'hc':int(f(tm.group(1))) if tm else 1,
                        'iv':f(ev.group(1)) if ev else None,
                        'du':f(du.group(1)) if (ev and du) else None})
    return out

jobs=[]
for j in src['jobs']:
    ct=j['classType']; skills=[]; nDesc=0
    for s in j['skills']:
        flag=s.get('triggerFlag') or ''
        isBasic='ReplaceBaseAttack' in flag
        common=dict(n=s['displayName'], cd=s.get('cooldownMs') or 0, du=s.get('durationMs') or 0,
                    b=1 if isBasic else 0, step=s.get('jobStep') or 0,
                    tt=s.get('triggerType'),
                    tr=(s.get('triggerRatio') if s.get('triggerRatio') is not None else 1000),
                    cond=1 if s.get('triggerCondition') else 0)
        # 테이블에 계수가 있으면 그대로, 없으면 설명문에서 복구합니다.
        usable=[o for o in s['directOps'] if o.get('damagePercent')]
        if usable:
            for o in usable:
                skills.append(dict(common, dp=o['damagePercent'], hc=o.get('hitCount') or 1,
                                   tg=o.get('maxHitCount') or 1, ticks=1, src='table'))
        elif s['type']=='Active':
            for p in parse_desc(s.get('description')):
                # 소환·장판: 지속시간 ÷ 발동주기 만큼 반복 타격합니다.
                ticks = int(p['du']/p['iv']) if (p['iv'] and p['du']) else 1
                skills.append(dict(common, dp=p['dp'], hc=p['hc'], tg=p['tg'],
                                   ticks=max(ticks,1), src='desc'))
                nDesc+=1

    active=[s for s in j['skills'] if s['type']=='Active']
    # 커버리지 분모는 '피해를 주는 스킬'만. 버프·이동기를 분모에 넣으면 지표가 왜곡됩니다.
    dmgActive=[s for s in active
               if s['directOps'] or '% damage' in (s.get('description') or '').lower()]
    names={x['n'] for x in skills}
    covered=[s for s in dmgActive if s['displayName'] in names]
    jobs.append({'id':j['id'],'ct':ct,'ko':KO.get(ct,j['name']),'en':j['name'],
                 'fam':FAM.get(j['family'],j['family']),'main':j.get('mainStat'),
                 'skills':skills,
                 'cov':round(len(covered)/max(len(dmgActive),1),3),
                 'nActive':len(dmgActive),'nDirect':len(covered),'nDesc':nDesc,
                 'descShare':round(sum(1 for x in skills if x['src']=='desc')/max(len(skills),1),3),
                 'skipped':sum(1 for x in skills if not x['b'] and not x['cd'] and
                               (x['cond'] or x['tt'] in ('OnTimer','OnActiveSkill')))})

json.dump({'meta':{'source':'job-skill-impact.json','appVersion':src['generatedFrom'].get('appVersion','1.14.0'),
                   'note':'directOps(테이블) + 스킬 설명문 파싱(투사체·소환) 병합.'},
           'jobs':jobs}, open('job-data.json','w'), ensure_ascii=False, separators=(',',':'))

print(f"{'직업':<16}{'딜스킬':>6}{'반영':>5}{'커버':>7}{'테이블':>7}{'설명문':>7}{'설명문비중':>10}")
for j in sorted(jobs,key=lambda x:(-x['cov'], x['descShare'])):
    tb=sum(1 for s in j['skills'] if s['src']=='table')
    print(f"{j['ko']:<16}{j['nActive']:>6}{j['nDirect']:>5}{j['cov']*100:>6.0f}%{tb:>7}{j['nDesc']:>7}{j['descShare']*100:>9.0f}%")
