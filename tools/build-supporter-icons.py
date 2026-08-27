#!/usr/bin/env python3
"""동료 초상화 -> data/supporter-icons.json (128px WebP data URI).

`uiatlases_assets_uiatlases/supporter.spriteatlasv2.bundle` 의 직업별 초상화 14종.
동료는 "직업 14종 x 등급 4단계 = 56" 이고 등급이 달라도 그림은 같아서 14장만 만든다.

직업 초상화(portrait 아틀라스)와 거의 같아 보이지만 같은 그림이 아니다 — 비숍과
나이트워커는 눈에 띄게 다르다. 그래서 재사용하지 않고 이 아틀라스에서 따로 뽑는다.
아틀라스 트림 복원은 build-icons.py 와 같은 방식이다.
"""
import base64, io, json, pathlib, sys
import UnityPy
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATLAS = ROOT / "reference/hi/uiatlases_assets_uiatlases/supporter.spriteatlasv2.bundle"
OUT = ROOT / "data/supporter-icons.json"
SIZE = 128

# 아틀라스 스프라이트 이름 -> data/web-data.json 의 직업 id
SPRITE2JOB = {
    "Hero": "hero", "Paladin": "paladin", "DarkKnight": "dark-knight",
    "ArchMageIL": "arch-mage-i-l", "ArchMageFP": "arch-mage-f-p", "Bishop": "bishop",
    "BowMaster": "bow-master", "Marksman": "marksman",
    "NightLord": "night-lord", "Shadower": "shadower",
    "Viper": "viper", "Captain": "captain",
    "NightWalker": "night-walker", "WindBreaker": "wind-breaker",
}

def restore(d):
    """아틀라스가 잘라낸 투명 여백을 m_Rect 크기로 되돌린다."""
    img = d.image
    w, h = int(d.m_Rect.width), int(d.m_Rect.height)
    off = getattr(d.m_RD, "textureRectOffset", None)
    cv = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = int(off.x) if off else (w - img.width) // 2
    oy = h - (int(off.y) if off else 0) - img.height
    cv.paste(img, (ox, oy), img)
    return cv.resize((SIZE, SIZE), Image.LANCZOS)

def main():
    if not ATLAS.exists():
        sys.exit(f"없음: {ATLAS.relative_to(ROOT)}")
    env = UnityPy.load(str(ATLAS))
    icons = {}
    for o in env.objects:
        if o.type.name != "Sprite":
            continue
        d = o.read()
        job = SPRITE2JOB.get(d.m_Name)          # Slot_* 배너는 여기서 걸러진다
        if not job:
            continue
        buf = io.BytesIO()
        restore(d).save(buf, "WEBP", quality=88, method=6)
        icons[job] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()

    OUT.write_text(json.dumps(icons, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    total = sum(len(v) for v in icons.values())
    print(f"{OUT.name}  {len(icons)}/{len(SPRITE2JOB)}개 · {total/1024:.0f}KB (base64)")
    missing = sorted(set(SPRITE2JOB.values()) - set(icons))
    if missing:
        print("  없음:", ", ".join(missing))

main()
