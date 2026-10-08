# post.json の形式

```json
{
  "id": "IG-NEWS-20261020",
  "series": "news",            // accounting / news / diagnosis / listed / failure
  "title": "管理用のタイトル",
  "slides": [ ... ]            // 2〜10枚
}
```

本文中の強調は `<span class="em">強調</span>`（茶色）、改行は `<br>`。

## スライドの種類

### cover（表紙）
```json
{"type":"cover","label":"2026年度","pose":"pose_A",
 "title":[{"html":"最低賃金","size":150,"mt":0},
          {"html":"全国平均 <span class=\"em\">1,177</span>円","size":84,"mt":18},
          {"html":"社長が今やる<span class=\"em\">3</span>つ","size":96,"mt":22}]}
```
- 3行構成。size は文字の大きさ（目安 84〜170）、mt は上の余白
- シリーズのタグ（#〜で検索）、名前（熱血会計おじさん フジヤマ）、「保存してあとで見る」は自動で入る

### bubble（吹き出し）
```json
{"type":"bubble","pose":"p27","bubble":"うちは月給制だから、<br>最低賃金は<span class=\"em\">関係ない</span>よ。",
 "body":"……本当に<br>そうでしょうか？","body_size":46,"next":"まずはニュースから →"}
```

### card（見出し＋カード＋本文）
```json
{"type":"card","pose":"p49","small":"ニュース","heading":"最低賃金が<br>全国平均<span class=\"em\">56円</span>アップ",
 "rows":[["全国加重平均","1,121円 → <span class=\"em\">1,177円</span>"],["発効日","10月1日〜12月2日に順次"]],
 "body":"引上げ額は、<br>都道府県ごとに<br><span class=\"em\">54円〜65円</span>。",
 "src":"出典：厚生労働省「…」"}
```
- rows の代わりに card_html（自由な文章）も使える。card_note はカード上部の小さな注記
- card_size で文字サイズ（既定40）、heading_size で見出しサイズ（既定76）

### table（左に表、右に人物）
rows と total（最後の太字行）を持つ。行数が多い図解向け。
```json
{"type":"table","pose":"p34","pose_right":20,"small":"…","heading":"…","heading_size":64,
 "rows":[["前期の営業利益","1,177億円"],["粗利の増加","＋115億円"]],"total":["当期の営業利益","1,255億円"]}
```

### list（番号つきまとめ）
```json
{"type":"list","pose":"p03","small":"まとめ","heading":"今月中に<br><span class=\"em\">この3つ</span>を確認",
 "items":["…","…","…"],"marker":"✓"}
```
marker を省略すると 1,2,3。

### final（最後のページ）
```json
{"type":"final","pose":"p04","heading":"あなたの会社の<br><span class=\"em\">発効日</span>はいつ？",
 "sub":"都道府県名をコメントで教えてください","card_html":"…","button":"保存して<br>給与計算前に見返す","note":"※…"}
```

## 共通オプション
- pose：`kit/poses.json` のキー（必須）
- pose_h：人物の高さ（px）。省略時は自動
- pose_right：右端からの距離（既定80）
- flip：true で人物を左右反転
- src：左下の出典・注記

# meta.json の形式（承認メールと管理シートに使う）
```json
{"id":"IG-NEWS-20261020","date":"2026-10-20","time":"20:00","series":"最新お金ニュース",
 "category":"時事・融資・税制・金融ニュース","title":"…","angle":"…","sources":"一次資料（1行1件・URLつき）",
 "poses":"pose_A,p27,…","n":10,"caption":"…","hashtags":"#フジヤマの最新お金ニュース #…",
 "check":"確認したこと","threads":"(任意) 同じ日のThreadsとの連動メモ","memo":"(任意)"}
```
