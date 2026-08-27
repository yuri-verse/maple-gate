import json, math, statistics as st, collections
site=json.load(open('/home/yuri/maple/data/site-data.json'))
JB={j['id']:j for j in json.load(open('/home/yuri/maple/data/job-data.json'))['jobs']}
ST={s['id']:s for s in site['stages']}
GAP={g[0]:g[1] for g in site['gap']}
SLF=json.load(open('jsi.json'))['skillLevelFactors']['columns']
REP=json.load(open('mgf-reports.json'))
MGF2ID={1:'hero',2:'paladin',3:'dark-knight',4:'ice-lightning',5:'fire-poison',6:'bishop',
        7:'bowmaster',8:'marksman',9:'night-lord',10:'shadower',11:'buccaneer',12:'corsair'}

def evade(g):
    if g<=0: return 0.0
    if g>=100: return 70.0
    lo,hi=math.floor(g),math.ceil(g); a=0 if lo==0 else GAP[lo]; b=GAP[hi]
    return a if lo==hi else a+(b-a)*(g-lo)
def n(x,d=0.0):
    try:
        v=float(x); return v if v==v else d
    except: return d

def lvlmul(factor_idx, lv):
    """스킬 레벨 계수. 컬럼 12/21, 1000분율."""
    col=SLF.get(str(factor_idx))
    if not col: return 1.0
    i=max(1, min(int(lv), len(col)-1))
    v=col[i]
    return (v/1000.0) if v else 1.0

def perhit(S, stg, kind, ACC, PIE):
    hb=(stg.get('bsp') or 0)>0
    dm=5000/(stg['def']*(1-PIE/100)+6000)
    crit=1+min(S['crit'],100)/100*(S['critd']/100)
    rng=(S['dmax'] if S['dmin']>S['dmax'] else (S['dmin']+S['dmax'])/2)/100
    tgt=1+(S['boss'] if hb else S['norm'])/100
    km=1+(S['skill'] if kind=='skill' else S['basic'])/100
    hit=1-evade(max(stg['eva']-ACC,0))/100
    return (S['atk']*dm*(1+S['dmg']/100)*(1+S['amp']/100)*(1+S['statp']/100)
            *tgt*km*crit*rng*(1+S['fin']/100)*hit)

def sim(job, stg, ratio, S, ACC, PIE, ASPD, SKLV, use_lvl=True):
    T=(stg['tl']/1000 if stg['tl'] else 60)*ratio
    spawn=max(stg.get('sp') or 1,1)
    hB=perhit(S,stg,'basic',ACC,PIE); hS=perhit(S,stg,'skill',ACC,PIE)
    def lm(x):
        if not use_lvl: return 1.0
        lv=1+SKLV.get(x.get('step') or 0,0)+SKLV.get('all',0)
        return lvlmul(21 if (x.get('dp') and x.get('step')) else 12, lv) if False else lvlmul(x.get('fi',21), lv)
    bs=[x for x in job['skills'] if x['b']]; basic=bs[-1] if bs else None
    occ=0.0; tot=0.0
    for x in [y for y in job['skills'] if not y['b'] and y['cd']>0]:
        uses=math.floor(T*1000/max(x['cd'],4000))+1
        tk=x.get('ticks') or 1; tg=min(x['tg'] or 1,spawn)
        tot+=uses*tk*hS*(x['dp']/100*lm(x))*(x['hc'] or 1)*tg
        occ+=uses*(0 if tk>1 else (x['du'] or 0))
    if basic:
        cyc=(basic['du'] or 1000)/(1+ASPD/100)
        uses=max(T*1000-occ,0)/cyc; tg=min(basic['tg'] or 1,spawn)
        tot+=uses*hB*(basic['dp']/100*lm(basic))*(basic['hc'] or 1)*tg
        bh=uses*(basic['hc'] or 1)
        for x in [y for y in job['skills'] if not y['b'] and not y['cd'] and not y['cond']
                  and y.get('tt') in ('OnAttack','OnHit')]:
            tot+=bh*((x.get('tr') or 1000)/1000)*hS*(x['dp']/100*lm(x))*(x['hc'] or 1)*min(x['tg'] or 1,spawn)
    return tot

def build():
    out=[]
    for sid,lst in REP.items():
        stg=ST.get(sid+'-v2') or ST.get(sid)
        if not stg or not stg.get('tl'): continue
        for r in lst:
            s=r.get('stats') or {}
            if not s.get('atk'): continue
            j=JB.get(MGF2ID.get(s.get('job_id')))
            if not j: continue
            S=dict(atk=n(s['atk']), crit=min(n(s.get('crit_rate')),100), critd=n(s.get('crit_dmg'),30),
                   dmg=n(s.get('dmg')), amp=n(s.get('dmg_amp')),
                   statp=n(s.get('main_stat'))*0.01+n(s.get('sub_stat'))*0.0025,
                   boss=n(s.get('boss_dmg')), norm=n(s.get('normal_dmg')),
                   skill=n(s.get('skill_dmg')), basic=n(s.get('basic_dmg')),
                   fin=n(s.get('final_dmg')), dmin=n(s.get('min_dmg'),65), dmax=n(s.get('max_dmg'),100))
            SKLV={1:n(s.get('skill1')),2:n(s.get('skill2')),3:n(s.get('skill3')),4:n(s.get('skill4')),
                  0:0,'all':n(s.get('all_skill'))}
            comp=len([c for c in (r.get('companions') or []) if c])
            out.append(dict(sid=sid, stg=stg, job=j, S=S, acc=n(s.get('acc')),
                            pie=min(n(s.get('armor_pierce')),100), aspd=n(s.get('atk_spd')),
                            sklv=SKLV, comp=comp, lv=n(s.get('level')), jid=s.get('job_id')))
    return out

# job-data 에 factorIndex 가 없으므로 스킬별 기본 21 로 두고, dp>=250 인 강타는 12 로 근사
for j in JB.values():
    for x in j['skills']:
        x['fi'] = 12 if x['dp']>=250 else 21

D=build()
print(f"평가 대상 {len(D)}건\n")
def report(tag, ratio, use_lvl, mult=1.0):
    v=[]
    for r in D:
        d=sim(r['job'], r['stg'], ratio, r['S'], r['acc'], r['pie'], r['aspd'], r['sklv'], use_lvl)*mult
        if d>0: v.append(d/r['stg']['hp'])
    v.sort()
    ok=sum(1 for x in v if x>=1)
    print(f"{tag:<44} 중앙 {st.median(v):>8.3f}   10% {v[len(v)//10]:>8.3f}   ≥1.0 {ok/len(v)*100:>5.1f}%")
    return v

report("① 현재 모델 (유효시간 100%)", 1.0, False)
report("② + 스킬 레벨 계수", 1.0, True)
