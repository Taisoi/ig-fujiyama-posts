"""公開前の検証ゲート（2026-11-01 藤山さん指示の再発防止ルール）

使い方:
  python3 kit/verify.py posts/<投稿ID>            … 検証して verify_report.json を書く（不合格なら終了コード1）
  python3 kit/verify.py posts/<投稿ID> --hash     … 現在の素材のハッシュだけを表示（検証担当が使う）

合格（status=pass）でないと kit/enqueue.py は受付キューに登録しない。
不合格は「保留」。直してから、もう一度ここから通す。検証を省略して公開しない。

必要なファイル（制作担当が書く）
  factcheck.json   … 一次資料・制度の段階・数字の計算式・確認済みの数字と日付（書き方は PRODUCTION.md「2」）
必要なファイル（制作とは別の検証担当が書く）
  verify_review.json … 原資料と完成画像を照合した結果。素材のハッシュ（--hash の値）と、見た画像ごとのハッシュを記録

機械で判定すること（1つでも当てはまれば保留）
  1 一次資料：URL・確認日・該当箇所が無い／取得できていない／官公庁等の一次資料が1件も無い
  2 制度の段階：成立前なのに、件名・表紙に「案」「成立したら／した場合」等が無い。キャプションに「審議中／成立した場合」が無い
    段階の確認日が投稿予定日の3日より前（投稿直前の再確認が必要。recheck_url も必須）
  3 計算：式を計算した値と記載値が合わない。架空例・概算に条件（課税方式など）が書かれていない
  4 表紙：架空例・概算の金額が、表紙・各画像・キャプションで「架空」の表示と条件なしに出ている。不安をあおる表現
  5 照合：画像・キャプション・件名に出てくる「〇万円」「〇億円」「〇%」「YYYY年M月D日」が、確認済みの一覧に無い
    「今月」「先月」「来年」などの相対的な日付表現がある（年月日で書く）
  6 検証担当：verify_review.json が無い／不合格／素材のハッシュが今と違う／画像を1枚でも見ていない
"""
import ast, hashlib, json, operator, re, sys
from datetime import date, datetime
from pathlib import Path

PRIMARY_DOMAINS = ("go.jp", "boj.or.jp", "jpx.co.jp", "e-gov.go.jp", "release.tdnet.info", "disclosure2.edinet-fsa.go.jp",
                   "shugiin.go.jp", "sangiin.go.jp", "nta.go.jp", "mof.go.jp", "jfc.go.jp", "smrj.go.jp")
STAGES_DONE = ("成立", "公布", "施行", "確定")          # これ以外（検討中・法案提出・審議中など）は「未成立」扱い
DRAFT_MARKERS = ("案", "成立したら", "成立した場合", "成立すれば", "審議中", "予定")
CAPTION_DRAFT_MARKERS = ("審議中", "成立した場合", "成立したら", "成立すれば", "未成立", "検討中")
RELATIVE_DATES = ("今月", "先月", "来月", "今年", "昨年", "去年", "来年", "今週", "先週", "来週", "今年度", "来年度", "昨日", "明日")
ALARM = ("を逃す", "を逃し", "逃してる", "知らないと損", "大損", "損してる", "今すぐやらないと")
NUM_RE = re.compile(r"[▲\-]?\d[\d,]*(?:\.\d+)?(?:万円|億円|円|%|％)")
DATE_RE = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日")
MEDIA_GLOBS = ("[0-9][0-9].jpg", "story_[0-9].jpg", "reel.mp4", "reel_cover.jpg")
TEXT_FILES = ("post.json", "story.json", "reel.json")
META_KEYS = ("date", "time", "title", "caption", "hashtags", "series", "kind")


def strip(html):
    return re.sub(r"<[^>]+>", "", str(html or "")).replace("&nbsp;", " ")


def texts(obj):
    """JSONの中の文字列をすべて取り出す（ポーズ名などの記号は除く）"""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("pose", "type", "id", "series", "src_url"):
                continue
            out += texts(v)
    elif isinstance(obj, list):
        for v in obj:
            out += texts(v)
    elif isinstance(obj, str):
        out.append(strip(obj))
    return out


def norm_num(s):
    return s.replace(",", "").replace("％", "%").replace("-", "▲")


def safe_eval(expr):
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
           ast.USub: operator.neg, ast.UAdd: operator.pos}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "round":
            a = [ev(x) for x in n.args]
            return round(*a)
        raise ValueError("使えない式です")

    return ev(ast.parse(expr, mode="eval"))


def file_hash(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def content_hash(d):
    """承認対象の中身（画像・動画・原稿・キャプション・日時）のハッシュ。1文字でも変われば変わる"""
    h = hashlib.sha256()
    for g in MEDIA_GLOBS:
        for p in sorted(d.glob(g)):
            h.update(p.name.encode() + file_hash(p).encode())
    for f in TEXT_FILES:
        p = d / f
        if p.exists():
            h.update(f.encode() + hashlib.sha256(p.read_bytes()).hexdigest().encode())
    meta = json.loads((d / "meta.json").read_text())
    h.update(json.dumps({k: meta.get(k) for k in META_KEYS}, ensure_ascii=False, sort_keys=True).encode())
    return h.hexdigest()


def surfaces(d, meta):
    """読み手が目にする面ごとの文字（件名・表紙・各画像・ストーリーズ・リール字幕・キャプション）"""
    s = {"件名": strip(meta.get("title", "")), "キャプション": strip(meta.get("caption", "")) + "\n" + strip(meta.get("hashtags", ""))}
    if (d / "post.json").exists():
        post = json.loads((d / "post.json").read_text())
        for i, sl in enumerate(post.get("slides", []), 1):
            s["表紙" if i == 1 else f"{i}枚目"] = " ".join(texts(sl))
    if (d / "story.json").exists():
        for i, fr in enumerate(json.loads((d / "story.json").read_text()).get("frames", []), 1):
            s[f"ストーリーズ{i}"] = " ".join(texts(fr))
    if (d / "reel.json").exists():
        reel = json.loads((d / "reel.json").read_text())
        for i, sc in enumerate(reel.get("scenes", []), 1):
            s[f"リール{i}" if i > 1 else "表紙"] = " ".join(texts(sc))
    return s


def verify(d):
    d = Path(d)
    errs, notes = [], []
    meta = json.loads((d / "meta.json").read_text())
    pub = meta.get("date", "")
    fc_p = d / "factcheck.json"
    if not fc_p.exists():
        return {"status": "hold", "errors": ["factcheck.json がありません（一次資料・計算・確認済みの数字を記録してから検証）"],
                "notes": [], "content_hash": content_hash(d)}
    fc = json.loads(fc_p.read_text())
    surf = surfaces(d, meta)

    # 1 一次資料
    srcs = fc.get("sources", [])
    if not srcs:
        errs.append("一次資料が記録されていません")
    ids = set()
    for s in srcs:
        ids.add(s.get("id"))
        name = s.get("title") or s.get("url") or s.get("id")
        if not s.get("url") or not s.get("checked_at") or not (s.get("locator") or s.get("excerpt")):
            errs.append(f"資料「{name}」に URL・確認日・該当箇所のどれかがありません")
        if s.get("fetched") is not True:
            errs.append(f"資料「{name}」を実際に開いて確認できていません（取得失敗）")
    needs_primary = meta.get("series") not in ("会計のはなし",) or fc.get("claims")
    if needs_primary and not any(any(dm in (s.get("url") or "") for dm in PRIMARY_DOMAINS) or s.get("type") == "ir"
                                 for s in srcs if s.get("fetched") is True):
        errs.append("官公庁・国会・取引所・会社IRなどの一次資料を、実際に開いて確認したものが1件もありません")
    for c in fc.get("claims", []):
        if c.get("source") not in ids:
            errs.append(f"記述「{c.get('text', '')[:30]}」の根拠資料が記録にありません")

    # 2 制度の段階
    st = fc.get("status") or {}
    if st.get("kind") in ("bill", "plan", "draft"):
        stage = st.get("stage", "")
        if not stage or not st.get("checked_at") or st.get("source") not in ids:
            errs.append("制度の段階（検討中／法案提出／成立／公布／施行）と確認日・根拠資料を記録してください")
        if not any(x in stage for x in STAGES_DONE):
            for face in ("件名", "表紙"):
                if not any(m in surf.get(face, "") for m in DRAFT_MARKERS):
                    errs.append(f"未成立（{stage}）なのに{face}に「案」「成立したら」等がありません")
            if not any(m in surf["キャプション"] for m in CAPTION_DRAFT_MARKERS):
                errs.append(f"未成立（{stage}）なのにキャプションに「審議中」「成立した場合」等がありません")
            if not st.get("recheck_url"):
                errs.append("未成立の制度は、投稿直前に段階を再確認するページ（recheck_url）が必要です")
        try:
            gap = (date.fromisoformat(pub) - date.fromisoformat(st.get("checked_at", "")[:10])).days
            if gap > 3:
                errs.append(f"制度の段階の確認日（{st.get('checked_at')}）が投稿予定日より{gap}日前です。投稿直前に再確認してください")
        except ValueError:
            errs.append("制度の段階の確認日が読めません（YYYY-MM-DD で書く）")

    # 3 計算と 4 架空例の表示
    allowed = {norm_num(v) for v in fc.get("verified_values", [])}
    for n in fc.get("numbers", []):
        label = n.get("label", "")
        try:
            got = safe_eval(n["expr"])
        except Exception as e:
            errs.append(f"「{label}」の計算式が読めません: {e}")
            continue
        if abs(got - float(n["value"])) > float(n.get("tolerance", 0.5)):
            errs.append(f"「{label}」の計算が合いません（式の結果 {got} ／ 記載 {n['value']}）")
        for disp in n.get("display", []):
            allowed.add(norm_num(disp))
        kind = n.get("kind", "実例")
        if kind in ("架空例", "概算", "試算"):
            conds = n.get("conditions") or []
            if not conds:
                errs.append(f"「{label}」は{kind}なのに、結論を左右する条件（課税方式など）が書かれていません")
            for face, t in surf.items():
                hit = [disp for disp in n.get("display", []) if norm_num(disp).lstrip("▲") in norm_num(t)]
                if not hit:
                    continue
                if "架空" not in t and kind == "架空例":
                    errs.append(f"{face}に「{hit[0]}」がありますが、同じ面に「架空例」の表示がありません")
                if face in ("件名", "表紙") or face.endswith("枚目") or face.startswith("ストーリーズ"):
                    miss = [c for c in conds if c not in t]
                    if miss:
                        errs.append(f"{face}の「{hit[0]}」の近くに条件（{'・'.join(miss)}）がありません")
                if face == "キャプション":
                    for m in re.finditer(re.escape(norm_num(hit[0]).lstrip("▲")), norm_num(t)):
                        window = norm_num(t)[max(0, m.start() - 300): m.end() + 300]
                        miss = [c for c in conds if c not in window]
                        if miss or "架空" not in window:
                            errs.append(f"キャプションの「{hit[0]}」の前後に「架空」と条件（{'・'.join(conds)}）がありません")
                            break

    for face in ("件名", "表紙", "キャプション"):
        for w in ALARM:
            if w in surf.get(face, ""):
                errs.append(f"{face}に不安をあおる表現「{w}」があります")

    # 5 数字・日付の照合
    allowed_dates = set(fc.get("verified_dates", []))
    for face, t in surf.items():
        for tok in NUM_RE.findall(t):
            k = norm_num(tok)
            if k not in allowed and k.lstrip("▲") not in {a.lstrip("▲") for a in allowed}:
                errs.append(f"{face}の「{tok}」が確認済みの数字の一覧（verified_values）にありません")
        for dt in DATE_RE.findall(t):
            if dt not in allowed_dates:
                errs.append(f"{face}の日付「{dt}」が確認済みの日付の一覧（verified_dates）にありません")
        for w in RELATIVE_DATES:
            if w in t:
                errs.append(f"{face}に相対的な日付「{w}」があります（投稿日で意味が変わるため年月日で書く）")

    # 描画の警告
    for rep in ("render_report.json", "story_report.json", "reel_report.json"):
        p = d / rep
        if p.exists() and json.loads(p.read_text()).get("warnings"):
            errs.append(f"{rep} に警告があります")
    media = [p for g in MEDIA_GLOBS for p in sorted(d.glob(g))]
    if not media:
        errs.append("画像・動画がありません")

    # 6 制作とは別の検証担当による照合
    ch = content_hash(d)
    rv_p = d / "verify_review.json"
    if not rv_p.exists():
        errs.append("制作とは別の検証担当の確認（verify_review.json）がありません")
    else:
        rv = json.loads(rv_p.read_text())
        if rv.get("result") != "pass" or rv.get("issues"):
            errs.append("検証担当が不合格としました: " + " / ".join(map(str, rv.get("issues") or ["result が pass ではありません"])))
        if rv.get("content_hash") != ch:
            errs.append("検証担当が確認した後に素材が変わっています（もう一度、検証担当に確認させる）")
        seen = rv.get("media_viewed") or {}
        for p in media:
            if p.suffix == ".mp4":
                key = p.name
                if key not in seen:
                    errs.append(f"検証担当が {p.name} を確認していません")
                continue
            if seen.get(p.name) != file_hash(p):
                errs.append(f"検証担当が {p.name} の完成画像を確認していません（未確認または確認後に変更）")
        if rv.get("reviewer") in (None, "", "producer", "制作担当"):
            errs.append("検証担当が制作担当と同じです（別の担当に確認させる）")

    return {"status": "pass" if not errs else "hold", "errors": errs, "notes": notes, "content_hash": ch,
            "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "stage": st.get("stage", ""), "recheck_url": st.get("recheck_url", ""), "stage_checked_at": st.get("checked_at", "")}


def main():
    d = Path(sys.argv[1])
    if "--hash" in sys.argv:
        print(content_hash(d))
        for g in MEDIA_GLOBS:
            for p in sorted(d.glob(g)):
                print(p.name, file_hash(p))
        return
    rep = verify(d)
    (d / "verify_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    if rep["status"] == "pass":
        print(f"合格: {d.name}（{rep['content_hash'][:12]}）")
    else:
        print(f"保留: {d.name}")
        for e in rep["errors"]:
            print(" -", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
