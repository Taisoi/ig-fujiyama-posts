"""縦型（1080x1920）の共通部品：ストーリーズとリールで使う

画面の上下はInstagramの表示（アカウント名・返信欄・ボタン）と重なるため、
文字は上250px・下340px・右140pxを避けて置く（人物の足元は重なってもよい）。
"""
import asyncio, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"
# カルーセル側（render.py）のシリーズ色・アイコンを使う。render.py の作り替えで読めなくなっても動くように控えを持つ
SERIES = {
    "diagnosis": ("決算書診断", "#フジヤマの決算書診断", "#CDD2BC"),
    "news": ("最新お金ニュース", "#フジヤマの最新お金ニュース", "#C6CDDA"),
    "listed": ("上場会社研究", "#フジヤマの上場会社研究", "#E3D9B6"),
    "accounting": ("会計のはなし", "#フジヤマの会計のはなし", "#E5CDBC"),
    "failure": ("フジヤマの失敗談", "#フジヤマの失敗談", "#D9CBC4"),
}
ICONS = {}
try:
    import render as _r
    SERIES = getattr(_r, "SERIES", SERIES)
    ICONS = getattr(_r, "ICONS", ICONS)
except Exception:
    pass

W, H = 1080, 1920

CSS = """
:root{--ink:#262626;--sub:#4a4a4a;--brown:#A6531E;--navy:#1E2B48;--series:#E5CDBC;--card:#FBF8F3;--line:#D8CFC2}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#777;font-family:"Zen Maru Gothic","Noto Sans CJK JP",sans-serif;color:var(--ink)}
.v{width:1080px;height:1920px;position:relative;overflow:hidden;background:#ECE6DC;margin-bottom:30px}
.v::before{content:"";position:absolute;inset:0;opacity:.5;pointer-events:none;z-index:0;
 background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .45  0 0 0 0 .40  0 0 0 0 .33  0 0 0 .22 0'/></filter><rect width='300' height='300' filter='url(%23n)'/></svg>");}
.em{color:var(--brown)}
.z{position:absolute;z-index:2}
.tag{left:56px;right:140px;top:250px;font-size:34px;font-weight:900;letter-spacing:.08em;color:#3a3a3a}
.tag i{font-style:normal;display:inline-block;background:var(--series);padding:8px 22px;border-radius:30px}
.blk{position:absolute;left:40px;right:40px;top:330px;border-radius:56px;background:var(--series);z-index:1}
.big{left:56px;right:140px;font-weight:900;line-height:1.22;text-align:left;white-space:nowrap}
.mid{left:56px;right:140px;font-weight:700;line-height:1.5;white-space:nowrap}
.card{background:var(--card);border:2px solid var(--line);border-radius:20px}
.num{display:inline-flex;align-items:center;justify-content:center;width:74px;height:74px;border-radius:50%;background:var(--brown);color:#fff;font-size:42px;font-weight:900;margin-right:24px;flex:none}
.row{display:flex;align-items:center;margin:14px 0}
.person{position:absolute;z-index:3;bottom:0}
.name{position:absolute;left:56px;bottom:360px;background:var(--navy);color:#fff;font-weight:900;padding:10px 22px 12px;border-radius:8px;z-index:4;line-height:1.2}
.name small{display:block;font-size:24px;letter-spacing:.06em;color:#E3B98F}
.name b{display:block;font-size:42px;letter-spacing:.16em}
.icon{position:absolute;right:150px;top:236px;width:120px;height:120px;border-radius:50%;background:var(--series);z-index:2;display:flex;align-items:center;justify-content:center}
.icon svg{width:76px;height:76px}
.sub{left:56px;right:140px;background:rgba(30,43,72,.92);color:#fff;font-size:46px;font-weight:700;line-height:1.5;padding:22px 30px;border-radius:16px;white-space:nowrap;text-align:center}
.btn{background:var(--navy);color:#fff;font-size:44px;font-weight:900;padding:22px 34px;border-radius:14px;text-align:center;line-height:1.4}
"""

# 改行（<br>）以外で折り返さず、枠に収まる最大の大きさに縮める
FIT_JS = r"""
() => {
  const warn = [];
  document.querySelectorAll('.fit').forEach(el => {
    const max = parseFloat(el.dataset.maxw || (1080 - 56 - 140));
    const tw = () => { const rg = document.createRange(); rg.selectNodeContents(el); return rg.getBoundingClientRect().width; };
    let f = parseFloat(getComputedStyle(el).fontSize);
    for (let k = 0; k < 60 && tw() > max && f > 30; k++) { f -= 2; el.style.fontSize = f + 'px'; }
    if (tw() > max + 2) warn.push('文字が枠からはみ出しています: ' + el.textContent.slice(0, 20));
  });
  // 縦の重なり：.stack の要素を上から順に並べる
  document.querySelectorAll('section.v').forEach((sec, i) => {
    const top = sec.getBoundingClientRect().top;
    if (sec.classList.contains('fixed')) {  // リール：位置は固定。字幕が人物の頭や下の表示エリアにかからないかだけ確かめる
      const sub = sec.querySelector('.sub'), p = sec.querySelector('img.person');
      if (sub && p && sub.getBoundingClientRect().bottom - top > p.getBoundingClientRect().top - top + 30) warn.push(`${i + 1}枚目: 字幕が長すぎて人物にかかっています（2行以内に）`);
      return;
    }
    let y = null;
    sec.querySelectorAll('.stack').forEach(el => {
      if (y === null) { y = el.getBoundingClientRect().top - top; }
      el.style.top = y + 'px';
      y = el.getBoundingClientRect().bottom - top + parseFloat(el.dataset.gap || 40);
    });
    const blk = sec.querySelector('.blk');
    if (blk && y !== null) blk.style.height = Math.max(200, y - 330) + 'px';
    const p = sec.querySelector('img.person');
    const lastText = [...sec.querySelectorAll('.stack, .sub')].map(e => e.getBoundingClientRect().bottom - top).reduce((a, b) => Math.max(a, b), 0);
    if (p) { const room = 1920 - lastText - 10; const h = Math.min(parseFloat(p.dataset.h), room);
      p.style.height = Math.max(520, h) + 'px'; }
    if (lastText > 1920 - 340) warn.push(`${i + 1}枚目: 文字が下の表示エリア（下340px）にかかっています`);
  });
  return warn;
}
"""


def fonts():
    nm = ROOT / "node_modules" / "@fontsource"
    return "".join(f'<link rel="stylesheet" href="{(nm / f).as_uri()}">' for f in
                   ["zen-maru-gothic/500.css", "zen-maru-gothic/700.css", "zen-maru-gothic/900.css", "klee-one/600.css"])


def person(pose, h=900, pos="right", flip=False):
    p = KIT / "poses" / f"{pose}.png"
    if not p.exists():
        raise SystemExit(f"ポーズがありません: {pose}")
    tf = "transform:scaleX(-1);" if flip else ""
    if pos == "anchor":  # 体の中心を x=760 に固定（ポーズの横幅が違っても顔の位置がそろう）
        return (f'<img class="person" data-pose="{pose}" data-h="{h}" src="{p.as_uri()}" '
                f'style="left:760px;transform:translateX(-50%){" scaleX(-1)" if flip else ""};height:{h}px">')
    side = {"right": "right:60px;", "left": "left:20px;", "center": "left:50%;transform:translateX(-50%);"}[pos]
    if pos == "center" and flip:
        side = "left:50%;transform:translateX(-50%) scaleX(-1);"
        tf = ""
    return f'<img class="person" data-pose="{pose}" data-h="{h}" src="{p.as_uri()}" style="{side}{tf}height:{h}px">'


def doc(sections, series):
    css = CSS.replace("--series:#E5CDBC", f"--series:{SERIES[series][2]}")
    return f'<!doctype html><html lang="ja"><head><meta charset="utf-8">{fonts()}<style>{css}</style></head><body>{"".join(sections)}</body></html>'


async def shoot(html_path, n, out_paths):
    """html を開き、#v1..#vn を out_paths に JPEG で保存。warnings を返す"""
    from playwright.async_api import async_playwright
    from PIL import Image
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": W, "height": H})
        await pg.goto(Path(html_path).as_uri())
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(1000)
        warns = await pg.evaluate(FIT_JS)
        for i in range(1, n + 1):
            tmp = Path(out_paths[i - 1]).with_suffix(".png")
            await pg.locator(f"#v{i}").screenshot(path=str(tmp))
            Image.open(tmp).convert("RGB").save(out_paths[i - 1], quality=92)
            tmp.unlink()
        await b.close()
    return warns


def contact(paths, out):
    from PIL import Image
    n = len(paths)
    sheet = Image.new("RGB", (n * 360, 640), "white")
    for i, pth in enumerate(paths):
        sheet.paste(Image.open(pth).resize((360, 640)), (i * 360, 0))
    sheet.save(out)
