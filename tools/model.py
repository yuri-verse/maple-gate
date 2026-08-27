#!/usr/bin/env python3
"""돌파(RushDefence) 전투 모델 — 검증된 피해식 + 방어형 판정.

검증 완료
  · 전투력 계산식      실계정 대조 (마스터리 배수만큼만 차이)
  · 1타 피해식         실측 200~900조 재현
  · 스테이지 데이터     방어력·회피가 독립 출처와 1.000배 일치
  · 스폰 타이밍        캠프 20개 · 1초 간격 · 마지막이 보스
  · 출구 거리          지형 왼쪽 끝. 보스 이동 31.9초 -> 전투 51초 (실측 40~60초)

보정 파라미터
  · R (로테이션 효율)  실제 초당 타격이 단순 모델보다 많은 정도. 실측으로 맞춘다.
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding='utf-8'))

_S = load('data/stages.json')['stages']
STAGES = {(s['id'], s['mode']): s for s in _S}
_J = load('data/job-skills.json')
JOBS = {j['ko']: j for j in _J['jobs']}
JOBS_BY_ID = {j['id']: j for j in _J['jobs']}
LVF = {int(k): v for k, v in _J['levelFactor'].items()}
EVADE = {g: v for g, v in load('data/site-data.json')['gap']}

FINAL_ATTACK = 1.25          # BattlePowerRuleTable TRIAL/GROWTHDUNGEON FinalAttackRatio 1250

def evade_pct(gap):
    if gap <= 0: return 0.0
    if gap >= 100: return 70.0
    lo, hi = math.floor(gap), math.ceil(gap)
    a = 0.0 if lo == 0 else EVADE.get(lo, 0.0)
    b = EVADE.get(hi, 0.0)
    return a if lo == hi else a + (b - a) * (gap - lo)

def skill_dp(s, sklv):
    """스킬 계수(%) 에 레벨 계수를 적용. 마스터리는 빌드 단계에서 이미 합산됨."""
    lv = 1 + max(0, sklv.get(s['step'], 0) or 0) + max(0, sklv.get('all', 0) or 0)
    lv = max(1, min(int(lv), max(LVF)))
    return s['dp'] * int(LVF[lv][s['col']]) / 1000

def per_hit(S, stage, kind, boss):
    """공식 피해 계산 순서. 스킬 계수는 제외한 1타 기준값."""
    p = min(max(S['pierce'], 0), 100)
    dmul = 5000 / (stage['def'] * (1 - p / 100) + 6000)
    crit = 1 + min(S['crit'], 100) / 100 * (S['critd'] / 100)
    rng  = (S['dmax'] if S['dmin'] > S['dmax'] else (S['dmin'] + S['dmax']) / 2) / 100
    tgt  = 1 + (S['boss'] if boss else S['norm']) / 100
    kind_mul = 1 + (S['skill'] if kind == 'skill' else S['basic']) / 100
    hit = 1 - evade_pct(max(stage['eva'] - S['acc'], 0)) / 100
    return (S['atk'] * FINAL_ATTACK * dmul
            * (1 + S['dmg'] / 100) * (1 + S['amp'] / 100) * (1 + S['statp'] / 100)
            * tgt * kind_mul * crit * rng * (1 + S['fin'] / 100) * hit)

def simulate(job, stage, S, sklv, R=1.0, extra=1.0, tick_ms=100, cap_s=300):
    """방어형: 몬스터가 출구에 닿기 전에 처치해야 한다."""
    exit_mm = stage.get('exitMm') or 21500
    hit = {(k, b): per_hit(S, stage, k, b) for k in ('basic', 'skill') for b in (False, True)}

    sk = [dict(s, dpx=skill_dp(s, sklv)) for s in job['skills']]
    basics = [x for x in sk if x['b']]
    basic  = max(basics, key=lambda x: x['dpx'] * (x['hc'] or 1)) if basics else None
    cds    = [x for x in sk if not x['b'] and x['cd'] > 0]
    ready  = {i: 0.0 for i in range(len(cds))}
    bcyc   = (basic['du'] or 1000) / (1 + S['aspd'] / 100) / R if basic else 1000.0
    nbasic = 0.0

    mobs = []
    for c in stage['camps']:
        for m in c['m']:
            spd = m['stat'].get('RunSpeedMms') or 1000
            dl  = c['t'] + exit_mm / spd * 1000
            for _ in range(m['cnt']):
                mobs.append([m['stat'].get('MaxHp', 0), m['boss'], dl, c['t']])
    mobs.sort(key=lambda x: x[3])
    alive, si, t = [], 0, 0.0
    while t < cap_s * 1000:
        while si < len(mobs) and mobs[si][3] <= t:
            alive.append(mobs[si]); si += 1
        for m in alive:
            if m[2] <= t:
                return dict(clear=False, sec=t/1000, by='보스' if m[1] else '잡몹', left=None)
        if alive:
            alive.sort(key=lambda x: x[2])
            boss_only = all(m[1] for m in alive)
            def strike(dmg, ntg):
                for m in alive[:min(ntg, len(alive))]:
                    m[0] -= dmg
            for i, x in enumerate(cds):
                if ready[i] <= t:
                    strike(hit[('skill', boss_only)] * (x['dpx']/100) * (x['hc'] or 1) * extra * R,
                           x['tg'] or 1)
                    ready[i] = t + max(x['cd'] - S['cdsec']*1000, 4000)
            if basic and t >= nbasic:
                strike(hit[('basic', boss_only)] * (basic['dpx']/100) * (basic['hc'] or 1) * extra,
                       (basic['tg'] or 1) + S['btgt'])
                nbasic = t + bcyc
            alive = [m for m in alive if m[0] > 0]
        if si >= len(mobs) and not alive:
            return dict(clear=True, sec=t/1000, by=None, left=0.0)
        t += tick_ms
    return dict(clear=False, sec=cap_s, by='시간초과', left=None)

def sustained_dps(job, stage, S, sklv, R=1.0, extra=1.0, boss=False):
    """지속 초당 피해. 광역기는 대상마다 전부 들어가므로 대상 수를 곱한다."""
    sk = [dict(x, dpx=skill_dp(x, sklv)) for x in job['skills']]
    basics = [x for x in sk if x['b']]
    basic = max(basics, key=lambda x: x['dpx']*(x['hc'] or 1)) if basics else None
    hB, hS = per_hit(S, stage, 'basic', boss), per_hit(S, stage, 'skill', boss)
    tgt_cap = max(1, min(stage['spawn'], 12))          # 화면에 동시에 있을 수 있는 대상
    dps = 0.0
    for x in [y for y in sk if not y['b'] and y['cd'] > 0]:
        eff = max(x['cd'] - S['cdsec']*1000, 4000)
        n = min(x['tg'] or 1, tgt_cap) if not boss else 1
        dps += hS*(x['dpx']/100)*(x['hc'] or 1)*n / (eff/1000)
    if basic:
        cyc = (basic['du'] or 1000)/(1 + S['aspd']/100)/1000
        n = min((basic['tg'] or 1) + S['btgt'], tgt_cap) if not boss else 1
        dps += hB*(basic['dpx']/100)*(basic['hc'] or 1)*n / cyc
    return dps * R * extra

def available_s(stage):
    """보스가 출구에 닿기까지의 시간 = 전투에 쓸 수 있는 총 시간."""
    exit_mm = stage.get('exitMm') or 21500
    bt = max((c['t'] for c in stage['camps'] for m in c['m'] if m['boss']), default=0)
    bspd = next((m['stat'].get('RunSpeedMms') or 1000
                 for c in stage['camps'] for m in c['m'] if m['boss']), 1000)
    return (bt + exit_mm/bspd*1000)/1000

def clear_ratio(job, stage, S, sklv, R=1.0, extra=1.0):
    """1.0 이상이면 클리어. 총 피해량 / 총 HP."""
    T = available_s(stage)
    d = sustained_dps(job, stage, S, sklv, R, extra, boss=False)
    return d*T/stage['hp'] if stage['hp'] else 0.0

def stats(**kw):
    d = dict(atk=0, crit=0, critd=30, dmg=0, amp=0, statp=0, boss=0, norm=0,
             skill=0, basic=0, fin=0, dmin=65, dmax=100,
             acc=0, pierce=0, aspd=0, cdsec=0, btgt=0)
    d.update(kw); return d
