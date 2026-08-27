#!/usr/bin/env python3
"""돌파(RushDefence) 전용 시뮬레이터 — 방어형.

실제 구조 (게임 확인):
  · 화면 타이머 없음. TimeLimitMs 는 내부 백스톱
  · 몬스터가 출구에 닿으면 즉시 실패
  · 캠프 20개가 1초 간격 스폰, 마지막 캠프가 보스
  · 보스도 걸어온다

따라서 제약은 '몬스터별 이동 시간 안에 처치'다.
  이동 시간 = 스폰 지점 ~ 출구 거리 / RunSpeedMms
"""
import json, math, os

ROOT = os.path.join(os.path.dirname(__file__), '..')

def per_hit(S, stage, kind, acc, pierce, boss, evade_tbl):
    dm  = 5000/(stage['def']*(1-pierce/100)+6000)
    cr  = 1 + min(S['crit'],100)/100*(S['critd']/100)
    rng = (S['dmax'] if S['dmin']>S['dmax'] else (S['dmin']+S['dmax'])/2)/100
    tgt = 1 + (S['boss'] if boss else S['norm'])/100
    km  = 1 + (S['skill'] if kind=='skill' else S['basic'])/100
    gap = max(stage['eva']-acc, 0)
    ev  = 0.0 if gap <= 0 else (70.0 if gap >= 100 else
          (lambda lo, hi: (0 if lo==0 else evade_tbl.get(lo,0)) if lo==hi else
           (0 if lo==0 else evade_tbl.get(lo,0)) + (evade_tbl.get(hi,0)-(0 if lo==0 else evade_tbl.get(lo,0)))*(gap-lo))
          (math.floor(gap), math.ceil(gap)))
    return (S['atk']*dm*(1+S['dmg']/100)*(1+S['amp']/100)*(1+S['statp']/100)
            *tgt*km*cr*rng*(1+S['fin']/100)*(1-ev/100))

def simulate(job, stage, S, acc, pierce, aspd, evade_tbl,
             travel_s=None, exit_mm=None, cdsec=0.0, btgt=0, extra=1.0,
             final_attack=1.0, tick_ms=100, cap_s=600):
    """travel_s 를 직접 주거나, exit_mm(출구까지 거리)로 몬스터별 이동시간을 계산."""
    S = dict(S); S['atk'] = S['atk']*final_attack
    hitB = {b: per_hit(S, stage, 'basic', acc, pierce, b, evade_tbl) for b in (False, True)}
    hitS = {b: per_hit(S, stage, 'skill', acc, pierce, b, evade_tbl) for b in (False, True)}
    bs = [x for x in job['skills'] if x['b']]
    basic = bs[-1] if bs else None
    cds = sorted([x for x in job['skills'] if not x['b'] and x['cd'] > 0],
                 key=lambda x: -x['dp']*(x['hc'] or 1)*(x['tg'] or 1))
    ready = {i: 0.0 for i, _ in enumerate(cds)}
    bcyc = (basic['du'] or 1000)/(1+aspd/100) if basic else 1000.0
    nbasic = 0.0

    mobs = []                       # [hp, boss, deadline_ms, tg_priority]
    for c in stage['camps']:
        for m in c['m']:
            spd = m['stat'].get('RunSpeedMms') or 1000
            tt = travel_s*1000 if travel_s else (exit_mm/spd*1000)
            for _ in range(m['cnt']):
                mobs.append([m['stat'].get('MaxHp',0), m['boss'], c['t']+tt, c['t']])
    mobs.sort(key=lambda x: x[2])
    alive = []; idx = 0; t = 0.0
    order = sorted(range(len(mobs)), key=lambda i: mobs[i][3])
    spawn_q = [mobs[i] for i in order]
    si = 0
    while t < cap_s*1000:
        while si < len(spawn_q) and spawn_q[si][3] <= t:
            alive.append(spawn_q[si]); si += 1
        alive.sort(key=lambda x: x[2])                 # 마감 임박 순
        for m in alive:
            if m[2] <= t:                              # 출구 도달
                return False, t/1000, m[1]
        if alive:
            boss_only = all(m[1] for m in alive)
            hB, hS = hitB[boss_only], hitS[boss_only]
            def strike(dmg, ntg):
                for m in alive[:min(ntg, len(alive))]:
                    m[0] -= dmg
            fired = False
            for i, x in enumerate(cds):
                if ready[i] <= t:
                    strike(hS*(x['dp']/100)*(x['hc'] or 1)*extra, x['tg'] or 1)
                    ready[i] = t + max(x['cd'] - cdsec*1000, 4000)
                    fired = True
            if basic and t >= nbasic:
                strike(hB*(basic['dp']/100)*(basic['hc'] or 1)*extra, (basic['tg'] or 1)+btgt)
                nbasic = t + bcyc
            alive = [m for m in alive if m[0] > 0]
        if si >= len(spawn_q) and not alive:
            return True, t/1000, False
        t += tick_ms
    return False, cap_s, False
