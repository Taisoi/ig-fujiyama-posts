"""n8n「IG自動投稿_9」の実行結果（ファイルに保存されたJSON）から、セリフごとのWAVを取り出す

使い方:
  python3 kit/voice_from_n8n.py <実行結果のJSONファイル> posts/<投稿ID>
  -> posts/<投稿ID>/voice/01.wav, 02.wav … と voice/voice.json（秒数とセリフ）

実行結果は mcp__n8n__get_workflow_execution（includeData: true, nodeNames: ["Code_WavBase64"]）で取得する。
結果が大きいため、ツールが自動でファイルに保存する。そのファイルのパスを渡す。
"""
import base64, json, sys
from pathlib import Path


def find_payload(obj):
    if isinstance(obj, dict):
        if obj.get("ok") is True and isinstance(obj.get("lines"), list) and obj["lines"] and "wav_b64" in obj["lines"][0]:
            return obj
        for v in obj.values():
            r = find_payload(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_payload(v)
            if r:
                return r
    return None


def main(src, post_dir):
    raw = Path(src).read_text()
    data = json.loads(raw)
    if isinstance(data, list):  # ツールの出力が [{type:text,text:...}] の形で保存される場合
        for x in data:
            if isinstance(x, dict) and isinstance(x.get("text"), str) and x["text"].lstrip().startswith("{"):
                data = json.loads(x["text"])
                break
    p = find_payload(data)
    if not p:
        raise SystemExit("音声データ（Code_WavBase64 の出力）が見つかりません")
    out = Path(post_dir) / "voice"
    out.mkdir(parents=True, exist_ok=True)
    info = []
    for ln in sorted(p["lines"], key=lambda x: x["i"]):
        f = out / f"{int(ln['i']):02d}.wav"
        f.write_bytes(base64.b64decode(ln["wav_b64"]))
        info.append({"i": ln["i"], "seconds": ln["seconds"], "text": ln["text"]})
    (out / "voice.json").write_text(json.dumps({"id": p.get("id"), "lines": info}, ensure_ascii=False, indent=1))
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
