# myxldscripts

私が macOS で音楽CDをリッピングをする時に使っているスクリプト郡です。

他の人がそのまま使えるということはないと思いますが、少しでもあなたのリッピングフローの参考になれば幸いです。

## 前提

* あなたに Python と macOS の知識がそれなりにあること
* XLD を使って ALAC m4a にリッピングをする
* 最終的に Music.app (わかりやすさのために今後は iTunes と言及します) に取り込む

## リッピングの流れ

### リッピングをするまでにやっておくこと (CDを手に入れる前でもできる)

* 事前に XLD と MusicBrainz Picard をインストールする
  * XLD: https://tmkk.undo.jp/xld/
  * MusicBrainz Picard: https://picard.musicbrainz.org/downloads/#mac
* 事前に XLD を設定する https://github.com/rinsuki/dotfiles/blob/master/mac/defaults.sh#:~:text=defaults%20write%20jp.tmkk.XLD
  * ファイル名の書式はスクリプトが想定しているので特に重要です
* 事前に MusicBrianz Picard の設定をする
  * オプション → メタデータ 内の 「トラックの関連性を利用する」「リリースの関連性を利用する」にチェックを入れます
    * これがないと iTunes 上で作曲者情報が見られない**ことが**あります
* 事前にいろんな人がリッピングしてそうなリリースのCDを入れてXLDでリッピングし、AccurateRipのオフセット情報を取得する?
  * TODO: これこの方法でいいんだっけ？
* このリポジトリの依存関係をインストールしておく
  * uv でなんか
* リッピングする予定のCDに対応するデジタルリリースがある場合は、事前にそれらを MusicBrainz に登録し、ISRCの紐付けまで済ませておく
  * (後述の `open-magicisrc-batch.sh` を実行する前まででよい、最悪やらなくても良い)
* `~/Desktop/xld-out/!done/zipdisc` をフォルダとして作っておく
  * (zsh だと ! をエスケープする必要があるので注意)

### CDを手に入れ、実際にリッピングをする時にやること

* XLD を起動した状態でCDをセット
* MusicBrainz に Disc ID が紐付けられていない旨のエラーが出た場合は MusicBrainz に Disc ID を登録 (リリースがなかった場合は作成)
  * TODO: リリース登録時にCDに書かれたISRCからrecordingをマッチする方法を探す & 書く
* XLD で MusicBrainz のリリースページを開き、手元のCDと同じリリースかどうかを確認
  * 通常版と限定版の2つがあり、自分が持っていない片方にだけ Disc ID が登録されている (=このままリッピングすると違うリリースがタグに付けられる)、という場合があります
  * 違うリリースだった場合は MusicBrainz Picard の「CDを検索…」から Disc ID を MusicBrainz に登録します
* XLD でリッピング
  * TODO: AccurateRip 通らなかった時の話を書く
* ディスクをイジェクトし、手持ちディスクを全てリッピングし終わるまで「XLD を起動した状態でCDをセット」に戻って繰り返す
* `python3 add-isrc-and-accuraterip-title.py` を実行する
  * このスクリプトはリッピングがうまく行っていないとエラーを投げるので、CDがまだ手元にある状態で流すことを推奨します
  * (ボロボロのマイナーなCDなどでどうしてもエラーを回避できない場合は、エラーをraiseしている部分を適時コメントアウト・`pass` に置き換えるなどしてください)

### リッピング後にやること (タグ付けなど)

* `./open-magicisrc-batch.sh` を実行する
  * MusicBrainz 上に紐付いていない ISRC を持ったトラックがある場合、MagicISRC がブラウザで開かれ MusicBrainz へのISRCの登録を促します
  * recordingに既に既存のISRCがある場合 (MagicISRC 上でテキストボックスの上下に他のISRCが表示される場合)、本当に同じバージョンか確認し、MusicBrainz の recording を分離すべきほど違うバージョンの場合は MusicBrainz 側で新規recordingを作成してください
    * TODO: この場合のタグ上の recording ID 更新ってどうなるんだっけ？
  * 登録(あるいはタブを閉じてキャンセル)後 Enter キーを押すとスクリプトを続行します
* `~/Desktop/xld-out` にできている `yなんとか_アルバム名_discN_idなんとか_mcnなんとか_` のフォルダを MusicBrainz Picard にドラッグ&ドロップする
* MusicBrainz Picard でアルバム単位でのタグの差分を確認する
  * 作曲者などの情報が乗っていない場合は MusicBrainz の Web 側で登録してから Picard でアルバムを右クリック→「更新」をしておくと良いでしょう
    * iTunes に一旦取り込むと m4a 側のタグを編集しても即時反映はされないので、iTunes に入れる前にちゃんとしたタグを入れておくことを推奨します
  * Picard 上で ISRC の差分 (追加のみでも) が出ている場合、反映しない (ISRCの行で右クリック→「元の値を使う」) ことを推奨します
    * これが起きている場合、ISRC の 1 recording = MusicBrainz の 1 recording ではないため、ISRC 上でどの recording だったかを記録しておくことはデータを失わないという観点から重要です
  * XLD の不具合？仕様のズレ？により、以下のフィールドでは Picard 上で差分が出がちですが、これはそのまま Picard 側の差分を反映するべきです
    * 作曲者
    * アーティスト (複数、ソート名)
    * (主に複数アーティストが登録できる部分やアーティストクレジットがアーティスト名と異なる場合に、PicardとXLDでどのように保存するかがブレるようです)
  * **タイトルに差分が出ている場合、内容を見て、AccurateRip のprefixが付いている場合は上書きしない (タイトルの行で右クリック→「元の値を使う」) ことを推奨します**
    * AccurateRip に fail しているという情報が失われてしまうため
* 再度確認したあと MusicBrainz Picard で保存をする
* Finder上でタイムスタンプが更新されたことを確認し、iTunes の「最近追加した項目」にフォルダごとドラッグ&ドロップする
* iTunes 上でファイルが全てコピーされたことを確認し、`~/Desktop/xld-out/!done` フォルダに先程D&Dしたフォルダを移動する
  * Finder のサイドバーに `!done` フォルダを登録しておくと便利です
* TODO: zipdisc のスクリプトを公開する