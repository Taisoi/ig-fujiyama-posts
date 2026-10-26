"""ストーリーズ3枚（1080x1920）を描画する

使い方:
  python3 kit/render_story.py posts/<投稿ID>/story.json
  -> posts/<投稿ID>/story_1.jpg ... story_3.jpg と story_contact.png、story_report.json

story.json の形式は kit/STORY_REEL_SPEC.md を参照。
アンケート・リンク等のスタンプはAPIで付けられないため、文字だけで完結させる。
"""
import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vertical import SERIES, ICONS, person, doc, shoot, contact  # noqa: E402


PERSON_H = 820  # 全フレーム同じ大きさ・同じ位置（体の中心 x=760）に固定してズレを防ぐ
TOP = 424        # 色ブロック（top 372）の内側52px、最初の文字の位置

# リールお知らせの一文は固定（2026-10-26 本人指示：「フジヤマが声で話しています」は不自然なので二度と使わない）。
# story.json の sub に何が書かれていても、この文言で描画する。
REEL_SUB = "フジヤマが音声で解説します"
BANNED = ["声で話しています", "声で話して"]


def check_banned(spec):
    text = json.dumps(spec, ensure_ascii=False)
    for w in BANNED:
        if w in text:
            raise SystemExit(f"禁止表現「{w}」が story.json にあります。「{REEL_SUB}」に直してください")


def frame(i, f, series):
    pill, tag, _ = SERIES[series]
    head = f'<div class="z tag"><i>{tag}</i></div><div class="icon">{ICONS.get(series, "")}</div>'
    t = f["type"]
    who = person(f["pose"], PERSON_H, "anchor", f.get("flip", False)) if f.get("pose") else ""
    if t == "ask":  # 1枚目：問いかけ（今夜の投稿の予告）
        body = (f'<div class="blk"></div>'
                f'<div class="z mid fit stack" style="top:{TOP}px;font-size:46px;color:var(--sub)" data-maxw="888" data-gap="12">{f.get("label", "今日の投稿")}</div>'
                f'<div class="z big fit stack" style="font-size:{f.get("size", 116)}px" data-maxw="888" data-gap="32">{f["title"]}</div>'
                f'<div class="z mid fit stack" style="font-size:54px" data-maxw="888" data-gap="52">{f.get("sub", "")}</div>')
        return f'<section class="v st" id="v{i}">{head}{body}{who}<div class="name"><small>熱血会計おじさん</small><b>フジヤマ</b></div></section>'
    if t == "points":  # 2枚目：要点
        items = "".join(f'<div class="row"><span class="num">{f.get("marker", str(k + 1))}</span><span class="fit" data-maxw="720">{it}</span></div>'
                        for k, it in enumerate(f["items"]))
        body = (f'<div class="blk"></div>'
                f'<div class="z big fit stack" style="top:{TOP}px;font-size:{f.get("size", 104)}px" data-maxw="888" data-gap="32">{f["heading"]}</div>'
                f'<div class="z card stack" style="left:96px;right:96px;padding:22px 32px;font-size:48px;font-weight:700;line-height:1.4" data-gap="56">{items}</div>')
        return f'<section class="v st" id="v{i}">{head}{body}{who}</section>'
    if t == "cta":  # 3枚目：フィード投稿・保存・LINEへの誘導（スタンプなし）
        lines = "".join(f'<div class="row"><span class="num" style="width:60px;height:60px;font-size:34px">✓</span><span class="fit" data-maxw="740">{x}</span></div>' for x in f.get("lines", []))
        body = (f'<div class="blk"></div>'
                f'<div class="z big fit stack" style="top:{TOP}px;font-size:{f.get("size", 108)}px" data-maxw="888" data-gap="32">{f["heading"]}</div>'
                f'<div class="z card stack" style="left:96px;right:96px;padding:18px 32px;font-size:46px;font-weight:700;line-height:1.4" data-gap="24">{lines}</div>'
                f'<div class="z btn stack" style="left:96px;right:96px" data-gap="56">{f.get("button", "プロフィールの<br>最新投稿をチェック")}</div>')
        return f'<section class="v st" id="v{i}">{head}{body}{who}</section>'
    if t == "reel":  # リールのお知らせ：リールの表紙を縮小して再生マークを重ねる
        cover = Path(f["_dir"]) / "reel_cover.jpg"
        if not cover.exists():
            raise SystemExit("reel_cover.jpg がありません（先に render_reel.py を実行）")
        body = (f'<div class="z big fit" style="top:372px;font-size:{f.get("size", 80)}px;text-align:center" data-maxw="888">{f["heading"]}</div>'
                f'<div class="z" style="left:50%;transform:translateX(-50%);top:610px;width:480px;height:853px;border:6px solid #fff;border-radius:28px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.25)">'
                f'<img src="{cover.as_uri()}" style="width:100%;height:100%;object-fit:cover">'
                f'<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:150px;height:150px;border-radius:50%;background:rgba(30,43,72,.85);display:flex;align-items:center;justify-content:center">'
                f'<div style="width:0;height:0;border-left:56px solid #fff;border-top:34px solid transparent;border-bottom:34px solid transparent;margin-left:14px"></div></div></div>'
                f'<div class="z mid fit" style="top:1490px;font-size:46px;text-align:center" data-maxw="888">{REEL_SUB}</div>')
        return f'<section class="v st" id="v{i}">{head}{body}</section>'
    raise SystemExit(f"不明なストーリーズの種類: {t}")


async def main(spec_path):
    spec_path = Path(spec_path).resolve()
    out = spec_path.parent
    spec = json.loads(spec_path.read_text())
    check_banned(spec)
    frames = spec["frames"]
    for f in frames:
        f["_dir"] = str(out)
    html = doc([frame(i + 1, f, spec["series"]) for i, f in enumerate(frames)], spec["series"])
    (out / "story.html").write_text(html)
    paths = [str(out / f"story_{i + 1}.jpg") for i in range(len(frames))]
    warns = await shoot(out / "story.html", len(frames), paths)
    contact(paths, out / "story_contact.png")
    poses = [f["pose"] for f in frames if f.get("pose")]
    if len(set(poses)) != len(poses):
        warns.append("ストーリーズの中で同じポーズを使っています")
    if not 1 <= len(frames) <= 5:
        warns.append(f"ストーリーズは1〜5枚にしてください（{len(frames)}枚）")
    rep = {"frames": len(frames), "poses": poses, "warnings": warns}
    (out / "story_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
