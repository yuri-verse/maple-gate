#!/usr/bin/env python3
"""원본 스테이지 + 스폰 페이스 모델로 커뮤니티 클리어 기록과 대조.

이전 calibrate.py 는 '총 HP를 제한시간으로 나눈' 모델이었다.
실제로는 캠프가 1초 간격으로 등장하므로, 초반에는 때릴 대상 자체가 없다.
여기서는 100ms 틱으로 스폰과 처치를 함께 굴린다.
"""
import json, math, os, sys, collections, statistics as st

ROOT = os.path.join(os.path.dirname(__file__), '..')
STG  = {}
for s in json.load(open(os.path.join(ROOT,'data','stages.json'), encoding='utf-8'))['stages']:
    STG[s['id'] + ('-v2' if s['mode']=='돌파' else '')] = s
    STG.setdefault(s['id'], s)
JOBS = {j['id']: j for j in json.load(open(os.path.join(ROOT,'data','job-data.json'), encoding='utf-8'))['jobs']}
GAP  = {int(r['Gap']): r for r in json.load(open(os.path.join(ROOT,'reference','client','StatGapValueTable.json'), encoding='utf-8'))} \
       if os.path.exists(os.path.join(ROOT,'reference','client','StatGapValueTable.json')) else {}

def evade(gap, table):
    if gap <= 0: return 0.0
    if gap >= 100: return 70.0
    lo, hi = math.floor(gap), math.ceil(gap)
    a = 0 if lo == 0 else table.get(lo, 0); b = table.get(hi, 0)
    return a if lo == hi else a + (b-a)*(gap-lo)

def num(x, d=0.0):
    try:
        v = float(x); return v if v == v else d
    except Exception: return d

def per_hit(S, stage, kind, acc, pierce, boss_target):
    dm  = 5000/(stage['def']*(1-pierce/100)+6000)
    cr  = 1 + min(S['crit'],100)/100*(S['critd']/100)
    rng = (S['dmax'] if S['dmin']>S['dmax'] else (S['dmin']+S['dmax'])/2)/100
    tgt = 1 + (S['boss'] if boss_target else S['norm'])/100
    km  = 1 + (S['skill'] if kind=='skill' else S['basic'])/100
    hit = 1 - evade(max(stage['eva']-acc,0), EV)/100
    return (S['atk']*dm*(1+S['dmg']/100)*(1+S['amp']/100)*(1+S['statp']/100)
            *tgt*km*cr*rng*(1+S['fin']/100)*hit)

EV = {}

def skill_dps(job, stage, S, acc, pierce, aspd, cdpct, cdsec, btgt, mastery=1.0):
    """스킬별로 (초당 단일대상 피해, 동시 타격 대상 수) 를 낸다.
    광역기는 대상마다 전부 들어가므로 대상 수를 나누지 않고 개수로 들고 간다."""
    out = {}
    for boss in (False, True):
        hB = per_hit(S, stage, 'basic', acc, pierce, boss)
        hS = per_hit(S, stage, 'skill', acc, pierce, boss)
        bs = [x for x in job['skills'] if x['b']]
        basic = bs[-1] if bs else None
        rows = []; occ = 0.0; T = 60.0
        for x in [y for y in job['skills'] if not y['b'] and y['cd'] > 0]:
            eff = max(x['cd']*(1-cdpct/100) - cdsec*1000, 4000)
            uses = T*1000/eff
            tk = x.get('ticks') or 1
            dps = uses*tk*hS*(x['dp']/100*mastery)*(x['hc'] or 1)/T
            rows.append((dps, x['tg'] or 1))
            occ += uses*(0 if tk > 1 else (x['du'] or 0))
        if basic:
            cyc = (basic['du'] or 1000)/(1+aspd/100)
            uses = max(T*1000-occ, 0)/cyc
            dps = uses*hB*(basic['dp']/100*mastery)*(basic['hc'] or 1)/T
            rows.append((dps, (basic['tg'] or 1) + btgt))     # 기본 공격 대상 수 증가
            bh = uses*(basic['hc'] or 1)
            for x in [y for y in job['skills'] if not y['b'] and not y['cd'] and not y['cond']
                      and y.get('tt') in ('OnAttack','OnHit')]:
                d2 = bh*((x.get('tr') or 1000)/1000)*hS*(x['dp']/100*mastery)*(x['hc'] or 1)/T
                rows.append((d2, x['tg'] or 1))
        out[boss] = rows
    return out

def dps_profile(job, stage, S, acc, pierce, aspd, cdpct):
    """구버전 호환: 합산 DPS 와 최대 타겟 수."""
    r = skill_dps(job, stage, S, acc, pierce, aspd, cdpct, 0.0, 0)
    return {k: (sum(d for d, _ in v), max((t for _, t in v), default=1)) for k, v in r.items()}

def simulate(job, stage, S, acc, pierce, aspd, cdpct, tick_ms=100,
             cdsec=0.0, btgt=0, mastery=1.0, extra=1.0,
             final_attack=1.0, wave_bonus_ms=0, wave_cool_ms=0, max_time_ms=600000):
    """쿨타임을 실제로 추적하는 이산 시뮬레이션.

    BattlePowerRuleTable(TRIAL/GROWTHDUNGEON):
      FinalAttackRatio        1250  최종 공격력 x1.25
      WaveClearBonusTimeMs   10000  웨이브 클리어 시 제한시간 +10초
      WaveModRemainCoolTimeMs -7000 웨이브 클리어 시 남은 쿨타임 -7초
    """
    S = dict(S); S['atk'] = S['atk'] * final_attack
    limit = (stage['tl'] or 60000)
    hitB = {b: per_hit(S, stage, 'basic', acc, pierce, b) for b in (False, True)}
    hitS = {b: per_hit(S, stage, 'skill', acc, pierce, b) for b in (False, True)}

    bs = [x for x in job['skills'] if x['b']]
    basic = bs[-1] if bs else None
    cds = [x for x in job['skills'] if not x['b'] and x['cd'] > 0]
    procs = [x for x in job['skills'] if not x['b'] and not x['cd'] and not x.get('cond')
             and x.get('tt') in ('OnAttack', 'OnHit')]
    ready = {i: 0 for i, _ in enumerate(cds)}          # 다음 사용 가능 시각
    basic_cyc = (basic['du'] or 1000)/(1+aspd/100) if basic else 1000
    next_basic = 0.0; busy_until = 0.0

    pool = []
    events = sorted(((c['t'], c) for c in stage['camps']), key=lambda x: x[0])
    spawned = set(); cleared = set()
    ei = 0; t = 0

    def strike(dmg, ntg):
        for row in pool[:min(ntg, len(pool))]:
            row[0] -= dmg

    while t < limit and t < max_time_ms:
        while ei < len(events) and events[ei][0] <= t:
            c = events[ei][1]
            for m in c['m']:
                for _ in range(m['cnt']):
                    pool.append([m['stat'].get('MaxHp', 0), m['boss'], c['i']])
            spawned.add(c['i']); ei += 1

        if pool:
            boss_only = all(b for _, b, _ in pool)
            hB, hS = hitB[boss_only], hitS[boss_only]
            if t >= busy_until:
                fired = False
                for i, x in sorted(enumerate(cds), key=lambda kv: -kv[1]['dp']*(kv[1]['hc'] or 1)):
                    if ready[i] <= t:
                        tk = x.get('ticks') or 1
                        strike(hS*(x['dp']/100*mastery)*(x['hc'] or 1)*tk*extra, x['tg'] or 1)
                        eff = max(x['cd']*(1-cdpct/100) - cdsec*1000, 4000)
                        ready[i] = t + eff
                        busy_until = t + (0 if tk > 1 else (x['du'] or 0))
                        fired = True; break
                if not fired and basic and t >= next_basic:
                    strike(hB*(basic['dp']/100*mastery)*(basic['hc'] or 1)*extra,
                           (basic['tg'] or 1) + btgt)
                    for x in procs:
                        strike(hS*(x['dp']/100*mastery)*(x['hc'] or 1)
                               * ((x.get('tr') or 1000)/1000)*(basic['hc'] or 1)*extra, x['tg'] or 1)
                    next_basic = t + basic_cyc
            pool = [r for r in pool if r[0] > 0]
            alive = {r[2] for r in pool}
            for ci in spawned - cleared:
                if ci not in alive:
                    cleared.add(ci)
                    limit += wave_bonus_ms
                    for i in ready:                       # 웨이브 클리어 -> 남은 쿨타임 감소
                        ready[i] = max(t, ready[i] - wave_cool_ms)
        if ei >= len(events) and not pool:
            return True, t/1000, 0.0
        t += tick_ms
    total = sum(m['stat'].get('MaxHp',0)*m['cnt'] for c in stage['camps'] for m in c['m'])
    left = sum(r[0] for r in pool) + sum(m['stat'].get('MaxHp',0)*m['cnt']
               for c in stage['camps'] for m in c['m'] if c['t'] > t)
    return False, t/1000, left/total if total else 1.0

# ---------- 대조 ----------
def main(reports_path):
    global EV
    sg = os.path.join(ROOT,'reference','client','StatGapValueTable.json')
    if os.path.exists(sg):
        raw = json.load(open(sg, encoding='utf-8'))
        k0 = sorted(raw[0].keys())
        EV = {}
        for r in raw:
            g = int(r.get('Gap') or r.get('StatGap') or r.get('Value') or 0)
            for f in r:
                if 'void' in f.lower() or 'vade' in f.lower():
                    EV[g] = float(r[f])/10 if float(r[f]) > 100 else float(r[f])
                    break
    if not EV:
        site = json.load(open(os.path.join(ROOT,'data','site-data.json'), encoding='utf-8'))
        EV = {g: v for g, v in site['gap']}

    REP = json.load(open(reports_path, encoding='utf-8'))
    M2J = {1:'hero',2:'paladin',3:'dark-knight',4:'ice-lightning',5:'fire-poison',6:'bishop',
           7:'bowmaster',8:'marksman',9:'night-lord',10:'shadower',11:'buccaneer',12:'corsair'}
    F = ['atk','main_stat','acc','crit_rate','crit_dmg','dmg','dmg_amp','final_dmg','boss_dmg',
         'normal_dmg','basic_dmg','skill_dmg','armor_pierce','atk_spd','min_dmg','max_dmg']
    rows = []
    for sid, lst in REP.items():
        stage = STG.get(sid+'-v2') or STG.get(sid)
        if not stage or not stage.get('tl'): continue
        for r in lst:
            s = r.get('stats') or {}
            if not s.get('atk'): continue
            if sum(1 for f in F if s.get(f) not in (None,'',0,'0')) < 15: continue
            job = JOBS.get(M2J.get(s.get('job_id')))
            if not job: continue
            S = dict(atk=num(s['atk']), crit=min(num(s.get('crit_rate')),100), critd=num(s.get('crit_dmg'),30),
                     dmg=num(s.get('dmg')), amp=num(s.get('dmg_amp')),
                     statp=num(s.get('main_stat'))*0.01+num(s.get('sub_stat'))*0.0025,
                     boss=num(s.get('boss_dmg')), norm=num(s.get('normal_dmg')),
                     skill=num(s.get('skill_dmg')), basic=num(s.get('basic_dmg')),
                     fin=num(s.get('final_dmg')), dmin=num(s.get('min_dmg'),65), dmax=num(s.get('max_dmg'),100))
            ok, sec, left = simulate(job, stage, S, num(s.get('acc')),
                                     min(num(s.get('armor_pierce')),100),
                                     num(s.get('atk_spd')), 0.0)
            rows.append(dict(ch=int(sid.split('-')[0]), ok=ok, left=left, sec=sec))
    g = collections.defaultdict(list)
    for r in rows: g[(r['ch']//5)*5].append(r)
    print(f"평가 {len(rows)}건 — 전부 '클리어했다'는 기록이므로 통과율이 높을수록 정확\n")
    print(f"{'챕터':<12}{'n':>5}{'통과율':>9}{'평균 잔여HP':>13}")
    for k in sorted(g):
        v = g[k]
        if len(v) < 5: continue
        ok = sum(1 for x in v if x['ok'])
        lf = st.mean([x['left'] for x in v if not x['ok']]) if ok < len(v) else 0
        print(f"  ch{k}~{k+4:<6}{len(v):>5}{ok/len(v)*100:>8.1f}%{lf*100:>12.1f}%")
    ok = sum(1 for x in rows if x['ok'])
    print(f"\n전체 통과율 {ok}/{len(rows)} = {ok/len(rows)*100:.1f}%")

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         '/tmp/claude-1000/-home-yuri/5ef6e679-7400-4ddd-b63f-3179cd77f600/scratchpad/mgf-reports.json')
