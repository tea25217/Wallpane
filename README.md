# Wallpane

[Releases](https://github.com/tea25217/Wallpane/releases)

LMDE 7（Cinnamon 6.4）向けの、**ディスプレイごとに別々の壁紙**を設定するツールです。

Cinnamon は壁紙 URI を1つしか持たないため、各ディスプレイ用の画像を仮想デスクトップサイズの1枚に合成し、`picture-options=spanned` で適用します。

## 必須要件への対応

| 要件 | 実装 |
| --- | --- |
| LMDE 最新版 | LMDE 7 / Cinnamon 6.4（X11）を対象。`gsettings` の `org.cinnamon.desktop.background` を使用 |
| マルチディスプレイ | `xrandr` の実ピクセル配置で合成。各ディスプレイに別画像を割り当て可能 |
| アジャスト方法 | カバー（短辺合わせ・切り取り）、フィット（長辺合わせ・余白）、引き延ばし、中央（実寸） |

カバー / フィット / 中央は縦横比を維持します。引き延ばしだけが例外です。

## ほしいものへの対応

- GUI（Qt / PySide6）。Cinnamon のロケールが日本語なら UI も日本語
- 各ディスプレイ枠へのドラッグ＆ドロップ、クリックでのファイル選択
- AppImage で配布（Linux 上で `scripts/build-appimage.sh`）

## 使い方（ソースから）

Python 3.11 以降。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m wallpane
```

CLI:

```bash
python -m wallpane list
python -m wallpane apply 'HDMI-1=~/Pictures/left.jpg:cover' 'DP-1=~/Pictures/right.png:contain'
```

アジャストの指定（`PATH:mode`）:

- `cover` — 短辺に合わせ、はみ出した部分を中央基準で切り取る
- `contain` — 長辺に合わせ、足りない辺は余白色
- `stretch` — ディスプレイサイズへ引き延ばす（縦横比は維持しない）
- `center` — 拡大せず中央に置く

## AppImage

[Releases](https://github.com/tea25217/Wallpane/releases) から `Wallpane-*-x86_64.AppImage` を入手できます。LMDE では:

```bash
chmod +x Wallpane-*-x86_64.AppImage
./Wallpane-*-x86_64.AppImage
```

自分でビルドする場合は **Linux 上**（glibc が LMDE 7 以下なら Ubuntu 22.04 が無難）で:

```bash
bash scripts/build-appimage.sh
```

FUSE が使えない場合は AppImage を `--appimage-extract` して中の `AppRun` を実行してください。

## 壁紙の適用方法

1. 接続ディスプレイの配置（座標と解像度）を取得する
2. その外接矩形のキャンバスを作る
3. 各ディスプレイ矩形へ、選んだアジャスト方法で画像を描く
4. `~/.local/share/wallpane/composed-<timestamp>.png` に保存する
5. 次を設定する
   - `org.cinnamon.desktop.background picture-uri`
   - `picture-uri-dark`（ダークテーマ用、存在すれば）
   - `picture-options` = `spanned`

未割り当てのディスプレイと、フィット時の余白は「余白・未設定の色」で塗ります。

設定（最後に使った画像とモード）は `~/.config/wallpane/config.json` に保存します。

## 開発

```bash
python -m pytest -q
```

GUI の見た目は Windows 上でも確認できます。壁紙の適用そのものは Linux / Cinnamon セッションでのみ行います。

対象は LMDE 7 の既定である **Cinnamon + X11** です。Cinnamon の実験的 Wayland は、ディスプレイ検出が Qt 経由のベストエフォートになります。
