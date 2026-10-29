"""リール動画（1080x1920・MP4）を作る

使い方:
  python3 kit/render_reel.py posts/<投稿ID>/reel.json
  -> posts/<投稿ID>/reel.mp4、reel_cover.jpg、reel_contact.png、reel_report.json

・各シーンを縦型の画像にして、ゆっくり寄る動きとクロスフェードでつなぐ
・posts/<投稿ID>/voice/01.wav … があれば、その長さでシーンを切り、ナレーションとして重ねる
  （フジヤマさんの声：2026-10-29からHeyGenの新しい声。n8n「IG自動投稿_9b」経由で kit/voice_from_n8n.py が置く）
・音声がないときは、字幕の文字数からシーンの長さを決める（1秒7文字が目安）
・BGMは毎回このスクリプトで作る自作の短いループ（著作権の心配なし）。声があるときは小さくする
・Instagramの条件：MP4（H.264・AAC 48kHz）、9:16、3秒〜15分、300MBまで
"""
import asyncio, json, math, re, subprocess, sys, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vertical import SERIES, ICONS, person, doc, shoot, contact  # noqa: E402

FPS = 30
XF = 0.35  # クロスフェードの秒数
SR = 48000


def scene(i, s, series, n):
    """全シーン同じ位置・同じ大きさで描く（シーンが変わっても文字・字幕・人物の位置が動かないように）"""
    pill, tag, _ = SERIES[series]
    small = f'<div class="z mid fit" data-maxw="888" style="top:424px;font-size:46px;color:var(--sub)">{s["small"]}</div>' if s.get("small") else ""
    big = (f'<div class="z" style="left:96px;right:96px;top:488px;height:332px;display:flex;align-items:center">'
           f'<div class="big fit" data-maxw="888" style="position:static;font-size:{s.get("size", 116)}px">{s["text"]}</div></div>')
    sub = (f'<div class="z sub" style="left:40px;right:40px;top:904px;padding:24px 56px;font-size:42px;white-space:normal;text-align:left;line-break:strict">{s["caption"]}</div>'
           if s.get("caption") else "")
    name = '<div class="name" style="bottom:400px"><small>熱血会計おじさん</small><b>フジヤマ</b></div>' if i == 1 else ""
    return (f'<section class="v fixed st" id="v{i}"><div class="z tag"><i>{tag}</i></div>'
            f'<div class="icon">{ICONS.get(series, "")}</div>'
            f'<div class="blk" style="height:500px"></div>{small}{big}{sub}'
            f'{person(s["pose"], 820, "anchor", s.get("flip", False))}{name}</section>')


def wrap_caption(t):
    """字幕は句読点の位置で2行に分ける（単語の途中で折り返さないように）"""
    if "<br>" in t or len(t) <= 20:
        return t
    mid = len(t) / 2
    cands = [k + 1 for k, ch in enumerate(t[:-1]) if ch in "、。？！"]
    if not cands:
        return t
    k = min(cands, key=lambda x: abs(x - mid))
    return t[:k] + "<br>" + t[k:]


def wav_seconds(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def plain(html):
    return re.sub(r"<[^>]+>", "", html.replace("<br>", ""))


def make_bgm(path, seconds, seed=0):
    """やわらかい和音のループ（C-Am-F-G、90BPM）。自作の音なので権利の心配はない"""
    import numpy as np
    rng = np.random.default_rng(seed)
    t_total = int(seconds * SR)
    out = np.zeros(t_total)
    beat = 60 / 90
    bar = beat * 4
    chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]
    f = lambda m: 440 * 2 ** ((m - 69) / 12)
    nb = math.ceil(seconds / bar)
    for b in range(nb):
        ch = chords[b % 4]
        s0 = int(b * bar * SR)
        L = int(bar * SR)
        tt = np.arange(L) / SR
        env = np.minimum(1, tt / 0.6) * np.minimum(1, (bar - tt) / 0.6)
        pad = sum(np.sin(2 * np.pi * f(m) * tt) * 0.5 + np.sin(2 * np.pi * f(m) * 1.003 * tt) * 0.5 for m in ch) / 3
        seg = pad * env * 0.22
        # 8分音符のやさしいアルペジオ
        for k in range(8):
            m = ch[k % 3] + 12 * (1 + (k // 3) % 2)
            a0 = int(k * beat / 2 * SR)
            al = int(beat / 2 * SR)
            ta = np.arange(al) / SR
            seg[a0:a0 + al] += np.sin(2 * np.pi * f(m) * ta) * np.exp(-ta * 6) * 0.10 * (0.8 + 0.4 * rng.random())
        # ベース
        tb = np.arange(L) / SR
        seg += np.sin(2 * np.pi * f(ch[0] - 24) * tb) * np.exp(-(tb % beat) * 3) * 0.18
        e = min(t_total, s0 + L)
        out[s0:e] += seg[:e - s0]
    fade = int(1.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[:int(0.5 * SR)] *= np.linspace(0, 1, int(0.5 * SR))
    out = out / (np.abs(out).max() + 1e-9) * 0.6
    stereo = np.stack([out, out], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype("<i2").tobytes())


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpegでエラー:\n" + r.stderr[-2000:])


async def main(spec_path):
    spec_path = Path(spec_path).resolve()
    out = spec_path.parent
    spec = json.loads(spec_path.read_text())
    scenes = spec["scenes"]
    n = len(scenes)
    work = out / "_reel"
    work.mkdir(exist_ok=True)
    for i, s in enumerate(scenes):
        s.setdefault("caption", wrap_caption(s.get("say", "")))
    html = doc([scene(i + 1, s, spec["series"], n) for i, s in enumerate(scenes)], spec["series"])
    (work / "reel.html").write_text(html)
    imgs = [str(work / f"s{i + 1:02d}.jpg") for i in range(n)]
    warns = await shoot(work / "reel.html", n, imgs)

    # シーンの長さ：声があれば声の長さ＋余白、なければ文字数から
    voice_dir = out / "voice"
    voices = [voice_dir / f"{i + 1:02d}.wav" for i in range(n)]
    has_voice = all(v.exists() for v in voices)
    durs = []
    for i, s in enumerate(scenes):
        if has_voice:
            d = wav_seconds(voices[i]) + 0.45
        else:
            d = max(2.4, len(plain(s.get("say") or s.get("caption", ""))) / 7.0 + 0.6)
        durs.append(round(d + (XF if i < n - 1 else 0), 2))
    total = sum(durs) - XF * (n - 1)

    # 映像：各シーンをゆっくり寄せて、クロスフェードでつなぐ
    clips = []
    for i, (img, d) in enumerate(zip(imgs, durs)):
        c = work / f"c{i + 1:02d}.mp4"
        # 画面は動かさない（拡大の動きは1〜2pxずつ段差が出て「ズレ」に見えるため使わない）。切り替えはクロスフェードだけ
        vf = f"scale=1080:1920,setsar=1,fps={FPS},format=yuv420p"
        run(["ffmpeg", "-y", "-loop", "1", "-t", str(d), "-i", img, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(c)])
        clips.append(c)
    if n == 1:
        video = clips[0]
    else:
        inputs = []
        for c in clips:
            inputs += ["-i", str(c)]
        fc, last, off = [], "0:v", 0.0
        for i in range(1, n):
            off += durs[i - 1] - XF
            lab = f"x{i}"
            fc.append(f"[{last}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{lab}]")
            last = lab
        video = work / "video.mp4"
        run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(video)])

    # 音声：BGM（自作）＋ナレーション
    bgm = work / "bgm.wav"
    seed = sum(map(ord, spec.get("id", "")))
    make_bgm(bgm, total + 0.5, seed)
    audio = work / "audio.wav"
    if has_voice:
        parts, t0 = [], 0.0
        for i, v in enumerate(voices):
            parts.append((v, t0 + 0.2))
            t0 += durs[i] - (XF if i < n - 1 else 0)
        ins, fl = ["-i", str(bgm)], []
        for k, (v, st) in enumerate(parts):
            ins += ["-i", str(v)]
            fl.append(f"[{k + 1}:a]aresample={SR},aformat=channel_layouts=stereo,adelay={int(st * 1000)}|{int(st * 1000)},volume=1.25[v{k}]")
        mix = "".join(f"[v{k}]" for k in range(len(parts)))
        fl.append(f"{mix}amix=inputs={len(parts)}:normalize=0[voice]")
        fl.append("[0:a]volume=0.16[b]")
        fl.append("[b][voice]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
        run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(fl), "-map", "[a]", "-t", f"{total:.2f}", str(audio)])
    else:
        run(["ffmpeg", "-y", "-i", str(bgm), "-af", "volume=0.55", "-t", f"{total:.2f}", str(audio)])

    mp4 = out / "reel.mp4"
    run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "128k", "-ar", str(SR), "-shortest", "-movflags", "+faststart", str(mp4)])
    # 表紙（カバー）は1シーン目
    from PIL import Image
    Image.open(imgs[0]).save(out / "reel_cover.jpg", quality=92)
    contact(imgs, out / "reel_contact.png")

    size = mp4.stat().st_size
    if total < 3 or total > 90:
        warns.append(f"動画の長さが{total:.1f}秒です（目安15〜60秒）")
    if size > 100 * 1024 * 1024:
        warns.append("動画が100MBを超えています")
    poses = [s["pose"] for s in scenes]
    if len(set(poses)) != len(poses):
        warns.append("同じポーズを2回以上使っています")
    rep = {"scenes": n, "seconds": round(total, 1), "voice": has_voice, "bytes": size, "poses": poses, "warnings": warns}
    (out / "reel_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    for c in work.glob("c*.mp4"):
        c.unlink()
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
