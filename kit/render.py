"""熱血会計おじさんフジヤマ Instagramカルーセル描画

使い方:
  python3 kit/render.py posts/<投稿ID>/post.json
  -> posts/<投稿ID>/01.jpg ... と contact.png（一覧）と render_report.json を出力

post.json の形式は kit/POST_SPEC.md を参照。
"""
import asyncio, json, os, sys, html as H
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"

SERIES = {
    "diagnosis": ("決算書診断", "#フジヤマの決算書診断", "#CDD2BC"),
    "news": ("最新お金ニュース", "#フジヤマの最新お金ニュース", "#C6CDDA"),
    "listed": ("上場会社研究", "#フジヤマの上場会社研究", "#E3D9B6"),
    "accounting": ("会計のはなし", "#フジヤマの会計のはなし", "#E5CDBC"),
    "failure": ("フジヤマの失敗談", "#フジヤマの失敗談", "#D9CBC4"),
}


def pose_img(pose, style):
    p = KIT / "poses" / f"{pose}.png"
    if not p.exists():
        raise SystemExit(f"ポーズがありません: {pose}")
    return f'<img class="person" data-pose="{pose}" src="{p.as_uri()}" style="{style}">'


def person(s, default_h, center=False):
    h = s.get("pose_h", default_h)
    extra = ";transform:scaleX(-1)" if s.get("flip") else ""
    if center:
        return pose_img(s["pose"], f"left:50%;transform:translateX(-50%){' scaleX(-1)' if s.get('flip') else ''};bottom:0;height:{h}px")
    return pose_img(s["pose"], f"right:{s.get('pose_right', 80)}px;bottom:0;height:{h}px{extra}")


def rows_html(rows, total=None):
    out = []
    for i, r in enumerate(rows):
        last = i == len(rows) - 1 and not total
        st = ' style="border:none"' if last else ""
        out.append(f'<div class="kv"{st}><span>{r[0]}</span><b>{r[1]}</b></div>')
    if total:
        out.append(f'<div class="kv" style="border:none;font-size:1.2em;padding-top:22px"><span style="font-weight:900">{total[0]}</span><b class="em">{total[1]}</b></div>')
    return "".join(out)


def slide(i, n, s, series):
    pill, tag, _ = SERIES[series]
    t = s["type"]
    pg = f'<div class="pill">{pill}</div><div class="pg">{i} / {n}</div>'
    src = f'<div class="src">{s["src"]}</div>' if s.get("src") else ""
    if t == "cover":
        lines = "".join(
            f'<div style="font-size:{l.get("size", 120)}px;margin-top:{l.get("mt", 10)}px">{l["html"]}</div>'
            for l in s["title"])
        return (f'<section class="page" id="s{i}"><div class="tag">{tag} で検索</div><div class="block"></div>'
                f'<div class="label">{s["label"]}</div><div class="title">{lines}</div>'
                f'{person(s, 520, center=True)}'
                f'<div class="name"><small>熱血会計おじさん</small><b>フジヤマ</b></div>'
                f'<div class="foot">保存して<br>あとで見る↓</div></section>')
    if t == "bubble":
        nxt = f'<div class="next" style="left:90px;right:auto">{s["next"]}</div>' if s.get("next") else ""
        return (f'<section class="page inner" id="s{i}">{pg}'
                f'<div class="bubble" style="left:90px;right:90px;top:180px">{s["bubble"]}</div>'
                f'<div class="body auto" style="left:90px;right:440px;font-size:{s.get("body_size", 44)}px">{s.get("body", "")}</div>'
                f'{person(s, 560)}{nxt}{src}</section>')
    if t in ("card", "list", "table"):
        hs = s.get("heading_size", 76)
        head = f'<div class="h" style="font-size:{hs}px"><small>{s.get("small", "")}</small>{s["heading"]}</div>'
        right = 340 if t == "table" else 64
        fs = s.get("card_size", 40 if t != "table" else 32)
        if t == "list":
            items = "".join(
                f'<div class="row" style="margin-bottom:26px"><span class="num" style="width:60px;height:60px;font-size:34px">{s.get("marker", str(k + 1))}</span>{it}</div>'
                for k, it in enumerate(s["items"]))
            card = f'<div class="abs card" style="left:64px;right:64px;top:{s.get("card_top", 500)}px;padding:40px 46px 14px;font-size:{fs}px;font-weight:700;line-height:1.55">{items}</div>'
        else:
            inner = rows_html(s["rows"], s.get("total")) if s.get("rows") else s.get("card_html", "")
            note = f'<div style="font-size:0.8em;color:var(--sub);margin-bottom:6px">{s["card_note"]}</div>' if s.get("card_note") else ""
            card = (f'<div class="abs card" style="left:64px;right:{right}px;top:{s.get("card_top", 520 if t == "card" else 430)}px;'
                    f'padding:30px 46px 34px;font-size:{fs}px;font-weight:700;line-height:1.7">{note}{inner}</div>')
        body = f'<div class="body auto" style="right:430px;font-size:{s.get("body_size", 36)}px">{s["body"]}</div>' if s.get("body") else ""
        d = 520 if t == "table" else 470
        return f'<section class="page inner" id="s{i}">{pg}{head}{card}{body}{person(s, d)}{src}</section>'
    if t == "final":
        return (f'<section class="page" id="s{i}">'
                f'<div class="abs" style="left:0;right:0;top:110px;text-align:center;font-size:{s.get("heading_size", 72)}px;font-weight:900;line-height:1.35">{s["heading"]}</div>'
                f'<div class="abs fsub" style="left:0;right:0;top:330px;text-align:center;font-size:40px;font-weight:900">{s.get("sub", "")}</div>'
                f'<div class="abs card fcard" style="left:90px;right:90px;padding:28px 40px;font-size:{s.get("card_size", 32)}px;font-weight:700;line-height:1.75">{s.get("card_html", "")}</div>'
                f'{person(s, 480, center=True)}'
                f'<div class="abs" style="right:60px;bottom:60px;background:var(--navy);color:#fff;font-size:34px;font-weight:900;padding:18px 30px;border-radius:14px;z-index:4;text-align:center;line-height:1.4">{s.get("button", "保存して<br>あとで見返す")}</div>'
                f'{"<div class=src style=left:60px;right:auto;bottom:24px>" + s["note"] + "</div>" if s.get("note") else ""}</section>')
    raise SystemExit(f"不明なスライド種別: {t}")


# 描画後に位置を自動調整し、はみ出し・重なりを検査するスクリプト
FIT_JS = r"""
() => {
  const warn = [];
  document.querySelectorAll('section.page').forEach((sec, idx) => {
    const top = sec.getBoundingClientRect().top;
    const rel = el => { const r = el.getBoundingClientRect(); return {t:r.top-top,b:r.bottom-top,l:r.left,r:r.right}; };
    const card = sec.querySelector('.card:not(.fcard)');
    const body = sec.querySelector('.body.auto');
    const bubble = sec.querySelector('.bubble');
    const h = sec.querySelector('.h');
    const fsub = sec.querySelector('.fsub'), fcard = sec.querySelector('.fcard');
    if (h && card) { const hb = rel(h).b; const ct = rel(card).t; if (hb + 30 > ct) { card.style.top = (hb + 40) + 'px'; } }
    let anchor = card || bubble;
    if (body && anchor) body.style.top = (rel(anchor).b + 50) + 'px';
    if (fsub && fcard) fcard.style.top = (rel(fsub).b + 40) + 'px';
    const person = sec.querySelector('img.person');
    const lowest = Math.max(card ? rel(card).b : 0, fcard ? rel(fcard).b : 0);
    if (person && lowest) {
      const room = 1350 - (lowest - 70);
      const h0 = person.getBoundingClientRect().height;
      const cardRight = Math.max(card ? rel(card).r : 0, fcard ? rel(fcard).r : 0);
      const beside = cardRight < rel(person).l - 10;
      if (!beside && h0 > room) person.style.height = Math.max(360, room) + 'px';
    }
    // 検査
    const p = person ? rel(person) : null;
    if (p && (p.l < 0 || p.r > 1080)) warn.push(`${idx+1}枚目: 人物が画面の端で切れています`);
    if (body) { const rg = document.createRange(); rg.selectNodeContents(body); const rr = rg.getBoundingClientRect(); const b = {t:rr.top-top,b:rr.bottom-top,l:rr.left,r:rr.right}; if (b.b > 1310) warn.push(`${idx+1}枚目: 本文が下にはみ出しています`);
      if (p && b.r > p.l + 10 && b.b > p.t + 40) warn.push(`${idx+1}枚目: 本文と人物が重なっています`); }
    [card, fcard].forEach(c => { if (c && rel(c).b > 1290) warn.push(`${idx+1}枚目: カードが下にはみ出しています`); });
    sec.querySelectorAll('.kv, .row').forEach(r => { if (r.scrollWidth > r.clientWidth + 2) warn.push(`${idx+1}枚目: 表の行が横にはみ出しています`); });
    sec.querySelectorAll('.kv span, .kv b').forEach(r => { if (r.getBoundingClientRect().height > 70) warn.push(`${idx+1}枚目: 表の行が折り返しています「${r.textContent.slice(0,20)}」`); });
  });
  return warn;
}
"""


async def render(spec_path):
    from playwright.async_api import async_playwright
    from PIL import Image
    spec_path = Path(spec_path).resolve()
    out = spec_path.parent
    spec = json.loads(spec_path.read_text())
    series = spec["series"]
    css = (KIT / "style.css").read_text().replace("--series:#E5CDBC", f"--series:{SERIES[series][2]}")
    nm = ROOT / "node_modules" / "@fontsource"
    fonts = "".join(f'<link rel="stylesheet" href="{(nm / f).as_uri()}">' for f in
                    ["zen-maru-gothic/500.css", "zen-maru-gothic/700.css", "zen-maru-gothic/900.css", "klee-one/600.css"])
    slides = spec["slides"]
    n = len(slides)
    poses = [s.get("pose") for s in slides]
    dup = {p for p in poses if poses.count(p) > 1}
    body = "".join(slide(i + 1, n, s, series) for i, s in enumerate(slides))
    doc = f'<!doctype html><html lang="ja"><head><meta charset="utf-8">{fonts}<style>{css}</style></head><body>{body}</body></html>'
    (out / "slides.html").write_text(doc)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.goto((out / "slides.html").as_uri())
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(1200)
        warns = await pg.evaluate(FIT_JS)
        for i in range(1, n + 1):
            png = out / f"_{i:02d}.png"
            await pg.locator(f"#s{i}").screenshot(path=str(png))
            Image.open(png).convert("RGB").save(out / f"{i:02d}.jpg", quality=92)
            png.unlink()
        await b.close()
    sheet = Image.new("RGB", (5 * 432, ((n + 4) // 5) * 540), "white")
    for i in range(n):
        im = Image.open(out / f"{i + 1:02d}.jpg").resize((432, 540))
        sheet.paste(im, ((i % 5) * 432, (i // 5) * 540))
    sheet.save(out / "contact.png")
    if dup:
        warns.append("同じポーズを2回以上使っています: " + ", ".join(sorted(dup)))
    if n < 2 or n > 10:
        warns.append(f"枚数が{n}枚です（Instagramのカルーセルは2〜10枚）")
    rep = {"slides": n, "poses": poses, "warnings": warns}
    (out / "render_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep


if __name__ == "__main__":
    asyncio.run(render(sys.argv[1]))
