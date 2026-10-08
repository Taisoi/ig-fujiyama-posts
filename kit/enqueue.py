"""受付キュー（queue/index.json）に投稿を登録・更新する

使い方（画像をコミットしてpushした後に実行）:
  python3 kit/enqueue.py <画像を含むコミットのSHA(40桁)> <投稿ID> [<投稿ID> ...]

n8n「IG自動投稿_7」が15分ごとにこのファイルを読み、管理シートに登録して承認メールを送る。
同じ投稿IDを再登録すると（画像URLが変わるので）管理シートの行が更新され、承認メールが再送される。
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_RAW = "https://raw.githubusercontent.com/Taisoi/ig-fujiyama-posts"
KEYS = ["id", "date", "time", "series", "category", "title", "problem", "angle", "facts", "target", "origin",
        "sources", "score", "score_detail", "poses", "n", "caption", "hashtags", "stories", "check", "threads", "memo"]


def main():
    sha, ids = sys.argv[1], sys.argv[2:]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit("SHAは40桁の英数字で指定してください")
    qp = ROOT / "queue" / "index.json"
    q = json.loads(qp.read_text()) if qp.exists() else {"items": []}
    items = {it["id"]: it for it in q["items"]}
    for pid in ids:
        d = ROOT / "posts" / pid
        meta = json.loads((d / "meta.json").read_text())
        n = len(sorted(d.glob("[0-9][0-9].jpg")))
        if n != int(meta["n"]):
            raise SystemExit(f"{pid}: 画像の枚数({n})とmeta.jsonのn({meta['n']})が一致しません")
        it = {k: meta[k] for k in KEYS if k in meta}
        it["base"] = f"{REPO_RAW}/{sha}/posts/{pid}/"
        items[pid] = it
        print("登録:", pid, it["date"], it["time"], it["title"])
    keep = sorted(items.values(), key=lambda x: (x["date"], x["time"]))[-30:]
    qp.parent.mkdir(exist_ok=True)
    qp.write_text(json.dumps({"items": keep}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
