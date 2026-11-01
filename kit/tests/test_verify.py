"""公開前の検証ゲートのテスト（公開はしない。一時フォルダの中だけで動く）

  python3 kit/tests/test_verify.py

確認すること：再発防止ルールの「保留にすべき原稿」がすべて保留になり、正常な原稿だけが通ること。
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

from PIL import Image

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
from verify import verify, content_hash, file_hash  # noqa: E402

PID = "IG-NEWS-20991104"


def make(root):
    d = root / "posts" / PID
    d.mkdir(parents=True)
    post = {"id": PID, "series": "news", "title": "食品の消費税1%案　成立したら還付はどう変わる？", "slides": [
        {"type": "cover", "label": "食品の消費税1%案（審議中）", "pose": "n46",
         "title": [{"html": "成立したら<br>還付はどう変わる？"}, {"html": "架空例・一般課税の場合<br>還付68万円の試算"}]},
        {"type": "card", "pose": "p46", "small": "架空例・一般課税の場合", "heading": "架空の食品店A社<br>還付68万円",
         "rows": [["食品の売上 4,000万円", "40万円"], ["食品の仕入 2,800万円", "▲28万円"], ["光熱費など 800万円", "▲80万円"],
                  ["差し引き", "▲68万円（還付）"]], "src": "※架空例・概算（税抜・一般課税）"},
        {"type": "final", "pose": "p33", "heading": "チェックリスト", "card_html": "□ 食品の割合を出した",
         "note": "※法案は審議中。成立した場合の内容。税率は8%から1%"},
    ]}
    meta = {"id": PID, "date": "2099-11-04", "time": "07:30", "series": "最新お金ニュース", "title": post["title"], "n": 3,
            "caption": "食品の消費税を1%にする法案が審議中です（2099年10月9日提出）。\n架空の食品店A社（一般課税・税抜の概算）\n→差し引き▲68万円（還付）\n※法案は審議中で、成立した場合の内容です。",
            "hashtags": "#フジヤマの最新お金ニュース"}
    fc = {
        "sources": [
            {"id": "S1", "title": "国税庁Q&A", "url": "https://www.nta.go.jp/x.pdf", "checked_at": "2099-11-03", "locator": "問3-6", "fetched": True},
            {"id": "S2", "title": "衆議院 審議経過", "url": "https://www.shugiin.go.jp/x.htm", "checked_at": "2099-11-03", "locator": "審議経過", "fetched": True}],
        "claims": [{"text": "税率1%", "source": "S1"}],
        "status": {"kind": "bill", "stage": "法案提出・審議中", "checked_at": "2099-11-03", "source": "S2",
                   "recheck_url": "https://www.shugiin.go.jp/x.htm"},
        "numbers": [{"label": "A社の還付", "expr": "4000*0.01-2800*0.01-800*0.10", "value": -68, "kind": "架空例",
                     "conditions": ["一般課税"], "display": ["68万円"]}],
        "verified_values": ["1%", "8%", "4,000万円", "2,800万円", "800万円", "40万円", "▲28万円", "▲80万円"],
        "verified_dates": ["2099年10月9日"]}
    (d / "post.json").write_text(json.dumps(post, ensure_ascii=False))
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    (d / "factcheck.json").write_text(json.dumps(fc, ensure_ascii=False))
    (d / "render_report.json").write_text('{"warnings": []}')
    for i in range(1, 4):
        Image.new("RGB", (40, 50), (i * 40, 100, 100)).save(d / f"{i:02d}.jpg")
    review(d)
    return d


def review(d, skip=()):
    """制作とは別の検証担当が、いまの素材を見て合格にした記録"""
    rv = {"reviewer": "independent-verifier", "result": "pass", "issues": [], "content_hash": content_hash(d),
          "media_viewed": {p.name: file_hash(p) for p in sorted(d.glob("[0-9][0-9].jpg")) if p.name not in skip}}
    (d / "verify_review.json").write_text(json.dumps(rv))


def edit(d, fname, fn, rereview=True):
    p = d / fname
    o = json.loads(p.read_text())
    fn(o)
    p.write_text(json.dumps(o, ensure_ascii=False))
    if rereview:
        review(d)


CASES = []


def case(name, expect):
    def deco(f):
        CASES.append((name, expect, f))
        return f
    return deco


@case("正常な原稿は通る", "pass")
def _(d):
    pass


@case("未成立の制度を断定（件名・表紙に『案』等がない）", "hold")
def _(d):
    edit(d, "meta.json", lambda m: m.update(title="食品の消費税1%へ 還付68万円"))
    edit(d, "post.json", lambda p: p["slides"][0].update(label="食品の消費税1%へ", title=[{"html": "還付は<br>どう変わる？"}]))


@case("未成立なのにキャプションに『審議中・成立した場合』がない", "hold")
def _(d):
    edit(d, "meta.json", lambda m: m.update(caption="食品の消費税が1%になります。架空の食品店A社（一般課税）は▲68万円（還付）。"))


@case("架空例の条件欠落（表紙に68万円・架空例の表示なし）", "hold")
def _(d):
    edit(d, "post.json", lambda p: p["slides"][0].update(title=[{"html": "成立したら<br>還付68万円"}]))


@case("架空例の条件欠落（課税方式を記録していない）", "hold")
def _(d):
    edit(d, "factcheck.json", lambda f: f["numbers"][0].update(conditions=[]))


@case("不安をあおる表現（還付を逃す）", "hold")
def _(d):
    edit(d, "meta.json", lambda m: m.update(title="食品の消費税1%案 届出を忘れて還付を逃す"))


@case("計算ミス（式と記載が合わない）", "hold")
def _(d):
    edit(d, "factcheck.json", lambda f: f["numbers"][0].update(value=-86))


@case("画像とキャプションで数字が違う（未確認の数字）", "hold")
def _(d):
    edit(d, "meta.json", lambda m: m.update(caption=m["caption"] + "\n仕入は3,000万円"))


@case("古い日付表現（『先月』）", "hold")
def _(d):
    edit(d, "meta.json", lambda m: m.update(caption=m["caption"] + "\n先月、法案が提出されました。"))


@case("制度の段階の確認が古い（投稿日の3日より前）", "hold")
def _(d):
    edit(d, "factcheck.json", lambda f: f["status"].update(checked_at="2099-10-20"))


@case("資料取得失敗（一次資料を開けていない）", "hold")
def _(d):
    edit(d, "factcheck.json", lambda f: [s.update(fetched=False) for s in f["sources"]])


@case("一次資料なし（ニュースサイトだけ）", "hold")
def _(d):
    edit(d, "factcheck.json", lambda f: f.update(sources=[{"id": "S1", "title": "報道", "url": "https://news.example.com/a",
                                                          "checked_at": "2099-11-03", "locator": "本文", "fetched": True},
                                                         {"id": "S2", "title": "報道2", "url": "https://news.example.com/b",
                                                          "checked_at": "2099-11-03", "locator": "本文", "fetched": True}]))


@case("画像未確認（検証担当が1枚見ていない）", "hold")
def _(d):
    review(d, skip=("03.jpg",))


@case("検証担当の確認がない", "hold")
def _(d):
    (d / "verify_review.json").unlink()


@case("検証担当が不合格", "hold")
def _(d):
    rv = json.loads((d / "verify_review.json").read_text())
    rv.update(result="hold", issues=["表紙の注記が小さく読めない"])
    (d / "verify_review.json").write_text(json.dumps(rv))


@case("承認版の確認後に重要な変更（金額を変えたのに再確認なし）", "hold")
def _(d):
    edit(d, "meta.json", lambda m: m.update(caption=m["caption"].replace("▲68万円", "▲80万円")), rereview=False)


@case("承認版の確認後に画像だけ差し替え", "hold")
def _(d):
    Image.new("RGB", (40, 50), (0, 0, 0)).save(d / "02.jpg")


def run_enqueue_case(tmp):
    """承認される版（コミットSHA）と検証した版がずれていたら、キューに登録しない"""
    root = tmp / "repo"
    shutil.copytree(KIT, root / "kit", ignore=shutil.ignore_patterns("tests", "poses", "__pycache__", "node_modules"))
    make(root)
    g = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, check=True).stdout.strip()
    g("init", "-q"); g("config", "user.email", "t@example.com"); g("config", "user.name", "t")
    g("add", "-A"); g("commit", "-qm", "a")
    sha = g("rev-parse", "HEAD")
    ok = subprocess.run([sys.executable, str(root / "kit/enqueue.py"), sha, PID], capture_output=True, text=True)
    d = root / "posts" / PID
    edit(d, "meta.json", lambda m: m.update(caption=m["caption"] + "\n追記"))  # 検証担当も確認し直した（合格）が、コミットしていない
    ng = subprocess.run([sys.executable, str(root / "kit/enqueue.py"), sha, PID], capture_output=True, text=True)
    q = json.loads((root / "queue/index.json").read_text())
    item = q["items"][0]
    return [("登録：合格した版は受付キューに入り、版のハッシュが付く", ok.returncode == 0 and item["verify"]["status"] == "pass"),
            ("登録：承認対象のコミットと検証した版が違えば保留", ng.returncode != 0 and "違います" in (ng.stdout + ng.stderr))]


def main():
    results = []
    for name, expect, f in CASES:
        with tempfile.TemporaryDirectory() as t:
            d = make(Path(t))
            f(d)
            rep = verify(d)
            ok = rep["status"] == expect
            results.append((name, ok))
            print(("OK " if ok else "NG ") + f"[{expect}] {name}" + ("" if expect == "pass" else f" … {rep['errors'][:1]}"))
            if expect == "pass" and not ok:
                print("   ", rep["errors"])
    with tempfile.TemporaryDirectory() as t:
        for name, ok in run_enqueue_case(Path(t)):
            results.append((name, ok))
            print(("OK " if ok else "NG ") + name)
    ng = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(ng)}/{len(results)} 件 合格")
    sys.exit(1 if ng else 0)


if __name__ == "__main__":
    main()
