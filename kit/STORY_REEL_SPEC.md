# ストーリーズ・リールの形式（2026-10-13 追加）

どちらも縦型 1080×1920。Instagramの表示と重ならないよう、文字は上250px・下340px・右140pxを避けて自動で配置される。
色・書体・人物はカルーセルと共通（kit/vertical.py）。アンケート・リンク・場所のスタンプはAPIで付けられないので使わない。

## ストーリーズ（posts/<投稿ID>/story.json）

フィード投稿の直後（同じ20時台）に、n8n「IG自動投稿_5」が3枚続けて投稿する。

```json
{"id":"IG-ACC-20261019","series":"accounting","frames":[
 {"type":"ask","label":"今日の投稿","pose":"p10",
  "title":"あと<span class=\"em\">いくら</span>売れば<br>黒字になる？","sub":"答えは<span class=\"em\">損益分岐点</span>で出せます"},
 {"type":"points","pose":"pose_D","heading":"出し方は<br><span class=\"em\">3ステップ</span>",
  "items":["費用を変動費と固定費に分ける","限界利益率を出す","固定費 ÷ 限界利益率"]},
 {"type":"cta","pose":"p48","heading":"計算例は<br><span class=\"em\">最新の投稿</span>で",
  "lines":["保存して計画づくりに","相談はプロフィールのLINEから"],"button":"プロフィールから<br>最新投稿をチェック"}
]}
```

- ask：1枚目。今日の投稿の問いかけ（表紙の見出しを言い換える。答えは書きすぎない）
- points：2枚目。要点3つ（1行18文字以内）
- cta：3枚目。投稿への誘導と保存・LINEの案内（CTA文言は管理シート「設定」の「CTA文言」と一致させる）
- 3枚とも別のポーズ。その日のカルーセルと同じポーズは避ける
- リールの日は2枚：1枚目 `{"type":"reel","heading":"新しいリール<br>…秒で解説","sub":"フジヤマが声で話しています"}`（ポーズ不要。reel_cover.jpg を自動で使う）、2枚目は cta
- `python3 kit/render_story.py posts/<ID>/story.json` → story_1.jpg〜story_3.jpg・story_contact.png・story_report.json（warnings は空にする）

## リール（posts/IG-REEL-<YYYYMMDD>/reel.json）

毎週 水・日 20:00。水曜は月曜「会計のはなし」、日曜は木曜「決算書診断」のカルーセルを、35〜50秒の動画にしたもの（カルーセルへの入口）。全シーンで文字・字幕・人物の位置は固定（描画スクリプトが自動で揃える）。

```json
{"id":"IG-REEL-20261021","series":"accounting","title":"…","scenes":[
 {"small":"社長、答えられますか？","text":"あと<span class=\"em\">いくら</span>売れば<br>黒字になる？","pose":"p10",
  "say":"社長、来月あといくら売れば黒字になるか、すぐ答えられますか？"},
 …
]}
```

- 6〜8シーン。text は2行まで・1行10文字前後。say はそのシーンのナレーション（1文、全角40文字以内）。字幕にも say が出る（caption で別の字幕を指定してもよい）
- 1シーン目で問いかけ、最後のシーンで「詳しくはプロフィールの投稿で」と誘導する
- 数字は読み上げやすく書く（「40%」→ say では「40パーセント」）。英字略語は読み方をカタカナで
- ナレーション：n8n「IG自動投稿_9_リール音声」（フジヤマさんの登録音声 TAISEI Voice）で作る。手順は PRODUCTION.md「8」
- `python3 kit/render_reel.py posts/<ID>/reel.json` → reel.mp4・reel_cover.jpg・reel_contact.png・reel_report.json
  - voice/01.wav… があれば声つき、なければBGMと字幕だけ（BGMは毎回スクリプトが作る自作の音で、著作権の心配はない）
- meta.json は `"kind":"reel"` を入れ、caption・hashtags・sources・poses・title・date・time・series を書く（n は自動で1）
