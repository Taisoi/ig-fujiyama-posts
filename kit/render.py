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


# シリーズごとの右上イラスト（線画アイコン）
ICONS = {
    "accounting": '<svg viewBox="0 0 64 64" fill="none" stroke="#1E2B48" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><rect x="14" y="6" width="36" height="52" rx="5"/><rect x="20" y="12" width="24" height="11" rx="2"/><circle cx="23" cy="32" r="1.6" fill="#1E2B48"/><circle cx="32" cy="32" r="1.6" fill="#1E2B48"/><circle cx="41" cy="32" r="1.6" fill="#1E2B48"/><circle cx="23" cy="41" r="1.6" fill="#1E2B48"/><circle cx="32" cy="41" r="1.6" fill="#1E2B48"/><circle cx="41" cy="41" r="1.6" fill="#1E2B48"/><circle cx="23" cy="50" r="1.6" fill="#1E2B48"/><circle cx="32" cy="50" r="1.6" fill="#1E2B48"/><path d="M41 47v6"/></svg>',
    "news": '<svg viewBox="0 0 64 64" fill="none" stroke="#1E2B48" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10 14h36v38a6 6 0 0 1-6 6H14a4 4 0 0 1-4-4z"/><path d="M46 24h8v28a6 6 0 0 1-12 0"/><path d="M17 22h22M17 30h10M17 38h22M17 46h22"/><rect x="31" y="28" width="8" height="6"/></svg>',
    "diagnosis": '<svg viewBox="0 0 64 64" fill="none" stroke="#1E2B48" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6h26l12 12v38H12z"/><path d="M38 6v12h12"/><path d="M19 28h18M19 36h10"/><circle cx="38" cy="44" r="8"/><path d="M44 50l7 7"/></svg>',
    "listed": '<svg viewBox="0 0 64 64" fill="none" stroke="#1E2B48" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M8 56h48"/><rect x="12" y="34" width="9" height="22"/><rect x="27" y="24" width="9" height="32"/><rect x="42" y="14" width="9" height="42"/><path d="M10 22l14-10 10 6 18-12"/><path d="M46 6h6v6"/></svg>',
    "failure": '<svg viewBox="0 0 64 64" fill="none" stroke="#1E2B48" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M32 8a18 18 0 0 1 10 33v7H22v-7A18 18 0 0 1 32 8z"/><path d="M24 54h16M27 60h10"/><path d="M28 30l4 4 4-4"/></svg>',
}


_PROF = {}


def pose_profile(p, bands=40, flip=False):
    """人物画像を縦40帯に分け、各帯で不透明部分の左端（画像幅に対する割合）を返す。本文と手・腕の重なり判定に使う"""
    key = (p, flip)
    if key not in _PROF:
        from PIL import Image
        a = Image.open(p).convert("RGBA").getchannel("A")
        if flip:
            a = a.transpose(Image.FLIP_LEFT_RIGHT)
        w, h = a.size
        px = a.load()
        out = []
        for k in range(bands):
            y0, y1 = h * k // bands, h * (k + 1) // bands
            left = w
            for y in range(y0, y1, 2):
                for x in range(0, left, 2):
                    if px[x, y] > 40:
                        left = x
                        break
            out.append(round(left / w, 3))
        _PROF[key] = ",".join(map(str, out))
    return _PROF[key]


def pose_img(pose, style, flip=False):
    p = KIT / "poses" / f"{pose}.png"
    if not p.exists():
        raise SystemExit(f"ポーズがありません: {pose}")
    return f'<img class="person" data-pose="{pose}" data-prof="{pose_profile(p, flip=flip)}" src="{p.as_uri()}" style="{style}">'


def person(s, default_h, center=False, v2=False):
    h = default_h if v2 else s.get("pose_h", default_h)
    extra = ";transform:scaleX(-1)" if s.get("flip") else ""
    if center:
        return pose_img(s["pose"], f"left:50%;transform:translateX(-50%){' scaleX(-1)' if s.get('flip') else ''};bottom:0;height:{h}px")
    return pose_img(s["pose"], f"right:{10 if v2 else s.get('pose_right', 80)}px;bottom:0;height:{h}px{extra}", flip=bool(s.get("flip")))


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
                f'{person(s, 700, center=True)}'
                f'<div class="name"><small>熱血会計おじさん</small><b>フジヤマ</b></div>'
                f'<div class="foot">保存して<br>あとで見る↓</div></section>')
    if t == "bubble":
        nxt = f'<div class="next" style="left:90px;right:auto">{s["next"]}</div>' if s.get("next") else ""
        return (f'<section class="page inner v2" id="s{i}">{pg}'
                f'<div class="bubble" style="left:56px;right:56px;top:124px;font-size:96px;padding:40px 40px;line-height:1.4">{s["bubble"]}</div>'
                f'<div class="body auto" style="left:56px;right:440px;font-size:{round(s["body_size"] * 1.5) if s.get("body_size") else 72}px;line-height:1.5">{s.get("body", "")}</div>'
                f'{person(s, 880, v2=True)}{nxt}{src}</section>')
    if t in ("card", "list", "table"):
        hs = round(s["heading_size"] * 1.35) if s.get("heading_size") else 104
        head = f'<div class="h" style="font-size:{hs}px"><small>{s.get("small", "")}</small>{s["heading"]}</div>'
        icon = f'<div class="icon">{ICONS.get(series, "")}</div>'
        right = 40
        base = 54 if t != "table" else 46
        fs = round(s["card_size"] * 1.4) if s.get("card_size") else base
        if t == "list":
            items = "".join(
                f'<div class="row" style="margin-bottom:24px"><span class="num" style="width:72px;height:72px;font-size:40px;margin-right:24px">{s.get("marker", str(k + 1))}</span>{it}</div>'
                for k, it in enumerate(s["items"]))
            card = f'<div class="abs card" style="left:56px;right:56px;top:400px;padding:32px 40px 8px;font-size:{fs}px;font-weight:700;line-height:1.45">{items}</div>'
        else:
            inner = rows_html(s["rows"], s.get("total")) if s.get("rows") else s.get("card_html", "")
            note = f'<div style="font-size:0.78em;color:var(--sub);margin-bottom:4px">{s["card_note"]}</div>' if s.get("card_note") else ""
            card = (f'<div class="abs card{"" if s.get("rows") else " free"}" style="left:56px;right:56px;top:400px;'
                    f'padding:16px 40px 16px;font-size:{fs}px;font-weight:700;line-height:1.6">{note}{inner}</div>')
        bs = round(s["body_size"] * 1.4) if s.get("body_size") else 60
        body = f'<div class="body auto" style="left:56px;right:430px;font-size:{bs}px;line-height:1.55">{s["body"]}</div>' if s.get("body") else ""
        return f'<section class="page inner v2" data-type="{t}" id="s{i}">{pg}{head}{icon}{card}{body}{person(s, 860, v2=True)}{src}</section>'
    if t == "final":
        return (f'<section class="page" id="s{i}">'
                f'<div class="abs fh" style="left:0;right:0;top:56px;text-align:center;white-space:nowrap;font-size:{round(s["heading_size"] * 1.38) if s.get("heading_size") else 104}px;font-weight:900;line-height:1.35">{s["heading"]}</div>'
                f'<div class="abs fsub" style="left:0;right:0;top:330px;line-height:1.4;text-align:center;font-size:56px;font-weight:900;white-space:nowrap">{s.get("sub", "")}</div>'
                f'<div class="abs card fcard" style="left:36px;right:36px;padding:20px 32px;font-size:{round(s["card_size"] * 1.5) if s.get("card_size") else 50}px;font-weight:700;line-height:1.6">{s.get("card_html", "")}</div>'
                f'{person(s, 720, center=True)}'
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
    // 表紙：人物がタイトルに重ならない高さにする
    { const ti = sec.querySelector('.title'), pp = sec.querySelector('img.person');
      if (ti && pp) { const room = 1350 - rel(ti).b - 16; if (pp.getBoundingClientRect().height > room) pp.style.height = Math.max(420, room) + 'px'; } }
    // 最後のページの見出し・サブは改行（<br>）以外で折り返さない大きさに
    sec.querySelectorAll('.fh, .fsub').forEach(el => { const tw = () => { const rg = document.createRange(); rg.selectNodeContents(el); return rg.getBoundingClientRect().width; };
      let f = parseFloat(getComputedStyle(el).fontSize); el.style.whiteSpace = 'nowrap';
      for (let k = 0; k < 30 && tw() > 1080 - 72 && f > 34; k++) { f -= 2; el.style.fontSize = f + 'px'; } });
    { const fh = sec.querySelector('.fh'), fs = sec.querySelector('.fsub'); if (fh && fs) fs.style.top = (rel(fh).b + 18) + 'px'; }
    // 自由記述のカードは、改行（<br>）以外で折り返さない大きさに
    sec.querySelectorAll('.card.free, .fcard').forEach(c => { if (c.querySelector('[style*="grid"]')) return; c.style.whiteSpace = 'nowrap';
      let f = parseFloat(getComputedStyle(c).fontSize); for (let k = 0; k < 30 && c.scrollWidth > c.clientWidth + 1 && f > 30; k++) { f -= 2; c.style.fontSize = f + 'px'; } });
    const card = sec.querySelector('.card:not(.fcard)');
    const body = sec.querySelector('.body.auto');
    const bubble = sec.querySelector('.bubble');
    const h = sec.querySelector('.h');
    const fsub = sec.querySelector('.fsub'), fcard = sec.querySelector('.fcard');
    const person = sec.querySelector('img.person');
    const v2 = sec.classList.contains('v2');
    if (v2) {
      // v2：見出しの直下にカード、その下の残りを本文（左）と大きめの人物（右）で埋める
      const icon = sec.querySelector('.icon');
      // 見出しは2行（小見出し除く）に収まるまで縮める
      if (h) { let f = parseFloat(getComputedStyle(h).fontSize); const sm = h.querySelector('small');
        for (let k = 0; k < 20; k++) { const hh = h.getBoundingClientRect().height - (sm ? sm.getBoundingClientRect().height + 6 : 0);
          if (hh <= f * 1.22 * 2 + 8 || f <= 60) break; f -= 4; h.style.fontSize = f + 'px'; }
        // 改行（<br>）の数より行が増えるなら（＝途中で折り返したら）さらに縮める
        const nl = h.querySelectorAll('br').length + 1;
        for (let k = 0; k < 20; k++) { const hh = h.getBoundingClientRect().height - (sm ? sm.getBoundingClientRect().height + 12 : 0);
          if (hh <= f * 1.2 * nl + 8 || f <= 60) break; f -= 4; h.style.fontSize = f + 'px'; } }
      // 表の行が折り返すならカードの文字を縮める
      const shrinkCard = () => { if (!card) return; let f = parseFloat(getComputedStyle(card).fontSize);
        for (let k = 0; k < 20; k++) { let wrap = false;
          card.querySelectorAll('.kv span, .kv b, .row').forEach(e => { const lh = parseFloat(getComputedStyle(e).fontSize) * 1.75; if (e.getBoundingClientRect().height > lh + 4) wrap = true; });
          if (!wrap || f <= 30) break; f -= 2; card.style.fontSize = f + 'px'; } };
      shrinkCard();
      if (card) { const ks = card.querySelectorAll('.kv span'); let mw = 0; ks.forEach(e => { mw = Math.max(mw, e.getBoundingClientRect().width); });
        if (ks.length && mw < 420) ks.forEach(e => { e.style.width = Math.ceil(mw) + 'px'; });
        const isNum = t => /^[0-9０-９,.万円%％（）()→\-−~〜億＋+▲△▼×＝=約か月年倍]*$/.test(t);
        const allNum = [...card.querySelectorAll('.kv b')].every(b => isNum(b.textContent.replace(/\s/g, '')));
        card.querySelectorAll('.kv b').forEach(b => { const t = b.textContent.replace(/\s/g, ''); b.style.flex = '1';
          b.style.textAlign = allNum && /^[0-9０-９,.万円%％（）()→\-−~〜億＋+▲△▼×＝=約か月年倍]+$/.test(t) ? 'right' : 'left'; }); }
      if (h && card) { const base = Math.max(rel(h).b, icon ? rel(icon).b : 0); card.style.top = (base + 40) + 'px'; }
      // 人物の縦の範囲[t,b]で、手や腕を含めた左端のx座標
      const edge = (t, b) => { const pr = rel(person); const pw = pr.r - pr.l, ph2 = pr.b - pr.t;
        const prof = (person.dataset.prof || '').split(',').map(Number); let m = 1080;
        prof.forEach((f, k) => { const y0 = pr.t + ph2 * k / prof.length, y1 = pr.t + ph2 * (k + 1) / prof.length;
          if (y1 >= t && y0 <= b && f < 1) m = Math.min(m, pr.l + pw * f); });
        return m; };
      // 表が長い・下に余地がないときは「カードの右に人物」の横並びにする
      const hasWrap = () => { let w = false; card.querySelectorAll('.kv span, .kv b, .row').forEach(e => { if (e.getBoundingClientRect().height > parseFloat(getComputedStyle(e).fontSize) * 1.75 + 4) w = true; }); return w; };
      const setCols = (lim) => { const ks = card.querySelectorAll('.kv span'); ks.forEach(e => { e.style.width = ''; }); let mw = 0; ks.forEach(e => { mw = Math.max(mw, e.getBoundingClientRect().width); }); if (ks.length && mw < lim) ks.forEach(e => { e.style.width = Math.ceil(mw) + 'px'; }); };
      let beside = false;
      if (card && person && (sec.dataset.type === 'table' || (1350 - rel(card).b < 470 && card.querySelector('.kv')))) {
        const save = {r: card.style.right, f: card.style.fontSize};
        card.style.right = '372px'; setCols(360); shrinkCard(); setCols(360);
        if (!hasWrap() && parseFloat(getComputedStyle(card).fontSize) >= (sec.dataset.type === 'table' ? 28 : 34) && rel(card).b < 1300) beside = true;
        else { card.style.right = save.r; card.style.fontSize = save.f; setCols(420); }
      }
      // 横並びにしないときは、人物と本文の場所が残るまでカードの文字を小さくする
      if (card && !beside) { let f = parseFloat(getComputedStyle(card).fontSize);
        for (let k = 0; k < 16 && 1350 - rel(card).b < (body ? 430 : 380) && f > 40; k++) { f -= 2; card.style.fontSize = f + 'px'; setCols(420); }  shrinkCard(); setCols(420); shrinkCard(); }
      if (beside) {
        person.style.height = Math.min(900, 1350 - rel(card).t + 40) + 'px';
        for (let k = 0; k < 30; k++) { const c = rel(card); if (edge(c.t, c.b) >= c.r + 12 || person.getBoundingClientRect().height <= 420) break;
          person.style.height = (person.getBoundingClientRect().height - 20) + 'px'; }
      }
      // 吹き出しページ：吹き出しの文字は改行（<br>）以外で折り返さない最大の大きさにする
      if (bubble && !card) { let f = parseFloat(getComputedStyle(bubble).fontSize); const n = bubble.querySelectorAll('br').length + 1;
        for (let k = 0; k < 40; k++) { const lh = parseFloat(getComputedStyle(bubble).lineHeight) || f * 1.45; const pad = parseFloat(getComputedStyle(bubble).paddingTop) + parseFloat(getComputedStyle(bubble).paddingBottom);
          if (bubble.getBoundingClientRect().height <= n * lh + pad + lh * 0.5 + 10 || f <= 50) break; f -= 2; bubble.style.fontSize = f + 'px'; } }
      const anchor2 = card || bubble;
      if (anchor2 && person) {
        const zoneTop = rel(anchor2).b + (card ? 16 : 40);
        const zoneH = 1350 - zoneTop;
        if (!beside) { const ph = card ? Math.max(380, Math.min(person.getBoundingClientRect().height, zoneH - 6)) : Math.min(1000, zoneH + 10);
          person.style.height = ph + 'px'; }
        if (!body && !beside) { const pw = rel(person).r - rel(person).l; person.style.right = Math.round((1080 - pw) / 2) + 'px'; }
        if (body) {
          const f0 = parseFloat(getComputedStyle(body).fontSize);
          const lines = body.querySelectorAll('br').length + 1;
          const fit = (t, b) => {
            body.style.right = (1080 - (edge(t, b) - 32)) + 'px';
            let fsz = f0; body.style.fontSize = fsz + 'px';
            for (let k = 0; k < 30; k++) { const lh = parseFloat(getComputedStyle(body).lineHeight) || fsz * 1.5;
              if (body.getBoundingClientRect().height <= lines * lh + 6 || fsz <= 40) break; fsz -= 2; body.style.fontSize = fsz + 'px'; }
            for (let k = 0; k < 14; k++) { if (body.getBoundingClientRect().height <= zoneH - 50 || fsz <= 34) break; fsz -= 2; body.style.fontSize = fsz + 'px'; }
            const bh = body.getBoundingClientRect().height;
            body.style.top = (zoneTop + 40) + 'px';
            return fsz; };
          // 本文の幅を最低540px確保する（足りなければ人物を少し小さくする）
          for (let k = 0; k < 30; k++) { if (!card || beside || edge(zoneTop + 16, 1330) - 62 >= 540 || person.getBoundingClientRect().height <= 440) break;
            person.style.height = (person.getBoundingClientRect().height - 20) + 'px'; }
          // 1回目：本文が来うる範囲全体で安全側に合わせる → 2回目：実際の本文の位置で広げて合わせ直す
          let f1 = fit(zoneTop + 16, 1330);
          // 本文が小さくなりすぎるときは、人物を少し小さくして本文の幅を広げる
          for (let k = 0; k < 12 && card && !beside && f1 < 56 && person.getBoundingClientRect().height > 560; k++) {
            person.style.height = (person.getBoundingClientRect().height - 30) + 'px'; f1 = fit(zoneTop + 16, 1330); }
          const s1 = {top: body.style.top, right: body.style.right, fs: body.style.fontSize};
          const s0 = {...s1};
          if (!card) { for (let k = 0; k < 4; k++) { const r = rel(body); const fx = fit(r.t - 10, r.b + 10); if (fx <= f1) { body.style.top = s1.top; body.style.right = s1.right; body.style.fontSize = s1.fs; break; } f1 = fx; s1.top = body.style.top; s1.right = body.style.right; s1.fs = body.style.fontSize; } }
          const r1 = rel(body); const f2 = fit(r1.t - 10, r1.b + 10); const r2 = rel(body);
          if (f2 < f1) { body.style.top = s1.top; body.style.right = s1.right; body.style.fontSize = s1.fs; }
          { const rg = document.createRange(); rg.selectNodeContents(body); const rr = rg.getBoundingClientRect();
}
          // 最後に、それでも手や腕にかかる場合は文字を小さくする
          for (let k = 0; k < 20; k++) { const rg = document.createRange(); rg.selectNodeContents(body); let bad = false;
            for (const q of rg.getClientRects()) { if (q.right > edge(q.top - top, q.bottom - top) - 6) bad = true; }
            const fz = parseFloat(getComputedStyle(body).fontSize); if (!bad) break; if (fz <= 34) { body.style.top = s0.top; body.style.right = s0.right; body.style.fontSize = s0.fs; break; } body.style.fontSize = (fz - 2) + 'px'; }
        }
      }
    }
    if (!v2 && h && card) { const hb = rel(h).b; const ct = rel(card).t; if (hb + 30 > ct) { card.style.top = (hb + 40) + 'px'; } }
    let anchor = card || bubble;
    if (!v2 && body && anchor) body.style.top = (rel(anchor).b + 50) + 'px';
    if (fsub) { let f = parseFloat(getComputedStyle(fsub).fontSize); const tw = () => { const rg = document.createRange(); rg.selectNodeContents(fsub); return rg.getBoundingClientRect().width; };
      for (let k = 0; k < 20 && tw() > 1080 - 60 && f > 34; k++) { f -= 2; fsub.style.fontSize = f + 'px'; } }
    if (fsub && fcard) fcard.style.top = (rel(fsub).b + 26) + 'px';
    const lowest = Math.max(card ? rel(card).b : 0, fcard ? rel(fcard).b : 0);
    if (fcard && person) { const room = 1350 - rel(fcard).b - 12; if (person.getBoundingClientRect().height > room) person.style.height = Math.max(360, room) + 'px'; }
    if (!v2 && person && lowest) {
      const room = 1350 - (lowest - 70);
      const h0 = person.getBoundingClientRect().height;
      const cardRight = Math.max(card ? rel(card).r : 0, fcard ? rel(fcard).r : 0);
      const beside = cardRight < rel(person).l - 10;
      if (!beside && h0 > room) person.style.height = Math.max(360, room) + 'px';
    }
    // 検査
    const p = person ? rel(person) : null;
    if (p && (p.l < -2 || p.r > 1082)) warn.push(`${idx+1}枚目: 人物が画面の端で切れています`);
    if (body) { const rg = document.createRange(); rg.selectNodeContents(body); const rr = rg.getBoundingClientRect(); const b = {t:rr.top-top,b:rr.bottom-top,l:rr.left,r:rr.right}; if (b.b > 1310) warn.push(`${idx+1}枚目: 本文が下にはみ出しています`);
      if (person) { const prof = (person.dataset.prof || '').split(',').map(Number); const ph2 = p.b - p.t, pw = p.r - p.l;
        body.querySelectorAll('*').length; const rects = rg.getClientRects();
        for (const q of rects) { const qt = q.top - top, qb = q.bottom - top;
          prof.forEach((f, k) => { const y0 = p.t + ph2 * k / prof.length, y1 = p.t + ph2 * (k + 1) / prof.length;
            if (f < 1 && y1 > qt && y0 < qb && q.right > p.l + pw * f + 2) warn.push(`${idx+1}枚目: 本文と人物が重なっています`); }); } } }
    if (p && card) { const c = rel(card); const prof = (person.dataset.prof || '').split(',').map(Number); const ph2 = p.b - p.t, pw = p.r - p.l; let hit = false;
      prof.forEach((f, k) => { const y0 = p.t + ph2 * k / prof.length, y1 = p.t + ph2 * (k + 1) / prof.length;
        if (f < 1 && y1 > c.t + 4 && y0 < c.b - 4 && p.l + pw * f < c.r - 4) hit = true; });
      if (hit) warn.push(`${idx+1}枚目: 人物がカードに重なっています`); }
    { const fz = el => el ? parseFloat(getComputedStyle(el).fontSize) : 99;
      sec.dataset.dbg = `card=${card ? fz(card) : '-'} body=${body ? fz(body) : '-'}`;
      if (card && fz(card) < 32) warn.push(`${idx+1}枚目: カードの文字が小さすぎます（${fz(card)}px）。文を短くしてください`);
      if (body && fz(body) < 36) warn.push(`${idx+1}枚目: 本文の文字が小さすぎます（${fz(body)}px）。文を短くしてください`); }
    [card, fcard].forEach(c => { if (c && rel(c).b > 1290) warn.push(`${idx+1}枚目: カードが下にはみ出しています`); });
    sec.querySelectorAll('.kv, .row').forEach(r => { if (r.scrollWidth > r.clientWidth + 2) warn.push(`${idx+1}枚目: 表の行が横にはみ出しています`); });
    sec.querySelectorAll('.kv span, .kv b').forEach(r => { if (r.getBoundingClientRect().height > parseFloat(getComputedStyle(r).fontSize) * 1.75 + 4) warn.push(`${idx+1}枚目: 表の行が折り返しています「${r.textContent.slice(0,20)}」`); });
  });
  return [...new Set(warn)];
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
