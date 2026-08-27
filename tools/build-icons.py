#!/usr/bin/env python3
"""직업 초상화 -> data/job-icons.json (128px WebP data URI).

우선 순위:
  1. reference/hi/uiatlases_assets_uiatlases/portrait.spriteatlasv2.bundle  (14직업 전부)
  2. reference/hi/resources.assets 의 BuiltIn_Portrait_*                    (10직업만)

어느 스프라이트를 쓸지는 우리가 정하지 않고 클라이언트가 정한다 — HeroTable.json 의
`PortraitPath`("Portrait:Portrait_Viper_Male") 를 그대로 따른다.

아틀라스 스프라이트는 여백이 잘려 들어 있다(`textureRectOffset`). m_Rect 가 전부 300x300
이므로 오프셋만큼 되돌려 원본 프레임을 복원한다 — 안 하면 직업마다 얼굴 크기가 달라진다.
"""
import base64, io, json, pathlib, sys
import UnityPy
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATLAS = ROOT / "reference/hi/uiatlases_assets_uiatlases/portrait.spriteatlasv2.bundle"
BUILTIN = ROOT / "reference/hi/resources.assets"
HEROTABLE = ROOT / "reference/client/HeroTable.json"
OUT = ROOT / "data/job-icons.json"
SIZE = 128

# HeroTable 의 ClassType -> data/web-data.json 의 직업 id
CLASS2JOB = {
    "Hero": "hero", "Paladin": "paladin", "DarkKnight": "dark-knight",
    "ArchMageIL": "arch-mage-i-l", "ArchMageFP": "arch-mage-f-p", "Bishop": "bishop",
    "BowMaster": "bow-master", "Marksman": "marksman",
    "NightLord": "night-lord", "Shadower": "shadower",
    "Viper": "viper", "Captain": "captain",
    "NightWalker": "night-walker", "WindBreaker": "wind-breaker",
}

def wanted():
    """job id -> 스프라이트 이름 (클라이언트 테이블이 정한 대로)"""
    out = {}
    for r in json.loads(HEROTABLE.read_text(encoding="utf-8")):
        job = CLASS2JOB.get(r.get("ClassType"))
        if not job:
            continue
        out[job] = r["PortraitPath"].split(":", 1)[-1]     # "Portrait:Portrait_X" -> "Portrait_X"
    return out

def to_icon(img):
    return img.resize((SIZE, SIZE), Image.LANCZOS)

def from_atlas(want):
    """아틀라스에서 뽑고 트림된 여백을 되돌린다."""
    icons = {}
    env = UnityPy.load(str(ATLAS))
    rev = {v: k for k, v in want.items()}
    for o in env.objects:
        if o.type.name != "Sprite":
            continue
        d = o.read()
        job = rev.get(d.m_Name)
        if not job:
            continue
        img = d.image
        w, h = int(d.m_Rect.width), int(d.m_Rect.height)
        off = getattr(d.m_RD, "textureRectOffset", None)
        cv = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        # 유니티 오프셋은 좌하단 기준 — PIL 은 좌상단이라 y 를 뒤집는다
        ox = int(off.x) if off else (w - img.width) // 2
        oy = h - (int(off.y) if off else 0) - img.height
        cv.paste(img, (ox, oy), img)
        icons[job] = to_icon(cv)
    return icons

def from_builtin(want, have):
    """아틀라스가 없을 때만. 로그인 화면용 BuiltIn 세트에는 10직업만 있다."""
    icons = {}
    env = UnityPy.load(str(BUILTIN))
    rev = {"BuiltIn_" + v: k for k, v in want.items()}
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        d = o.read()
        job = rev.get(d.m_Name)
        if not job or job in have:
            continue
        img = d.image
        bb = img.getbbox()
        if bb:
            img = img.crop(bb)
        s = max(img.size)
        cv = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        cv.paste(img, ((s - img.width) // 2, s - img.height), img)
        icons[job] = to_icon(cv)
    return icons

def main():
    want = wanted()
    icons, src = {}, {}
    if ATLAS.exists():
        icons = from_atlas(want)
        src["아틀라스"] = sorted(icons)
    else:
        print(f"! 아틀라스 없음: {ATLAS.relative_to(ROOT)}", file=sys.stderr)
    if len(icons) < len(want) and BUILTIN.exists():
        extra = from_builtin(want, icons)
        icons.update(extra)
        if extra:
            src["BuiltIn"] = sorted(extra)

    enc = {}
    for job, img in icons.items():
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=88, method=6)
        enc[job] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    OUT.write_text(json.dumps(enc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    total = sum(len(v) for v in enc.values())
    print(f"{OUT.name}  {len(enc)}/{len(want)}개 · {total/1024:.0f}KB (base64)")
    for k, v in src.items():
        print(f"  {k}: {len(v)}개")
    missing = sorted(set(want) - set(enc))
    if missing:
        print("  없음:", ", ".join(missing), "— 페이지에서 SVG 글리프로 대체됨")

main()
