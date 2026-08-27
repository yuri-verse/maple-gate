#!/usr/bin/env python3
"""몬스터 초상화 + 유물 아이콘 -> data/dex-icons.json

스테이지에 실제로 등장하는 몬스터(dex.json)만 뽑는다. 아틀라스에는 566장이 있지만
등장하지 않는 것까지 넣으면 페이지만 무거워진다.
"""
import base64, io, json, os, sys
import UnityPy
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AT = os.path.join(ROOT, 'reference/hi/uiatlases_assets_uiatlases')
OUT = os.path.join(ROOT, 'data', 'dex-icons.json')
MON_SIZE, ART_SIZE = 48, 64

def restore(d, size):
    img = d.image
    w, h = int(d.m_Rect.width), int(d.m_Rect.height)
    off = getattr(d.m_RD, 'textureRectOffset', None)
    cv = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ox = int(off.x) if off else (w - img.width) // 2
    oy = h - (int(off.y) if off else 0) - img.height
    cv.paste(img, (ox, oy), img)
    return cv.resize((size, size), Image.LANCZOS)

def enc(img, q):
    b = io.BytesIO(); img.save(b, 'WEBP', quality=q, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()

def sprites(bundle):
    p = os.path.join(AT, bundle)
    if not os.path.exists(p):
        print('  없음:', bundle, file=sys.stderr); return {}
    out = {}
    for o in UnityPy.load(p).objects:
        if o.type.name == 'Sprite':
            d = o.read(); out[d.m_Name] = d
    return out

dex = json.load(open(os.path.join(ROOT, 'data', 'dex.json'), encoding='utf-8'))

# 스프라이트 이름 규칙이 몬스터마다 다르다 — PortraitIconPath 가 맞는 것도 있고
# CodeName 숫자가 맞는 것도 있어서 아틀라스에 실제로 있는 이름을 순서대로 찾는다.
SP = sprites('monsterportrait.spriteatlasv2.bundle')
mons = {}
for m in dex['monsters']:
    for cand in (m['ic'], m['code'], m['ci']):
        if cand and cand in SP:
            mons[m['ci']] = enc(restore(SP[cand], MON_SIZE), 74); break

AS = sprites('artifact.spriteatlasv2.bundle')
arts = {a['code']: enc(restore(AS[a['code']], ART_SIZE), 86)
        for a in dex['artifacts'] if a['code'] in AS}

json.dump(dict(mon=mons, art=arts), open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
miss = [m['n'] for m in dex['monsters'] if m['ci'] not in mons]
print(f"dex-icons.json {os.path.getsize(OUT)/1024:.0f}KB · 몬스터 {len(mons)}/{len(dex['monsters'])}"
      f" · 유물 {len(arts)}/{len(dex['artifacts'])}")
if miss: print(f"  초상화 없음 {len(miss)}종:", ', '.join(miss[:8]), '…' if len(miss) > 8 else '')
