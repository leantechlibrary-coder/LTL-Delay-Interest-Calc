# デスクトップ版のビルドと Microsoft Store への提出

Windows 上で行います。必要なもの: Python 3.10 以降、Windows SDK（`makeappx.exe`）。

## 1. バージョンを上げる

次の2か所を同じ番号にします。Store は同じ番号のパッケージを受け付けません。

- `main.py` の `APP_VERSION`（例: `"1.1.0"`）
- `AppxManifest.xml` の `Identity` の `Version`（例: `1.1.0.0`。4桁目は常に 0）

## 2. 検証

```bash
python tests/check_engines.py
```

## 3. PyInstaller でビルド

セキュリティ修正を取り込むため、Python と PyQt6 は提出のたびに最新の安定版へ更新します。

```bash
pip install --upgrade -r requirements.txt pyinstaller
```

`dist` と `build` フォルダが残っていれば削除してからビルドします。
MSIX に入れるので必ず `--onedir` を使います（`--onefile` は不可）。
`【EXE名】` は `AppxManifest.xml` の `Executable` に書いたファイル名と一致させます。

```bash
pyinstaller --onedir --windowed --name "【EXE名】" --icon=app_icon.ico main.py
```

`dist\【EXE名】\` に EXE と `_internal` フォルダができます。

## 4. MSIX 用フォルダを用意

```
【作業フォルダ】\
├── AppxManifest.xml
├── Assets\
│   ├── Square150x150Logo.png   150×150
│   ├── Square44x44Logo.png     44×44
│   ├── StoreLogo.png           50×50
│   └── Wide310x150Logo.png     310×150
└── VFS\ProgramFilesX64\【アプリフォルダ】\
    ├── 【EXE名】.exe
    └── _internal\              ← dist の中身を丸ごとコピー
```

`AppxManifest.xml` の `Identity`（`Name`・`Publisher`）と `PublisherDisplayName`、`DisplayName` は
Partner Center の「Product Identity」ページの値と完全に一致させます。
`runFullTrust` 以外の Capability は不要です（このアプリは通信もファイルアクセスも行いません）。

`AppxManifest.xml`・アイコン・`app_icon.ico` はこのリポジトリには含まれていません。

## 5. パッケージ化

OneDrive 同期フォルダと `C:\` 直下は避け、`C:\temp\` などに出力します。

```bash
"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\makeappx.exe" pack /d "【作業フォルダ】" /p "C:\temp\【EXE名】.msix"
```

署名は Store 側で行われるため、自分で署名する必要はありません。

## 6. 提出

1. Partner Center → 対象アプリ → Packages で古いパッケージを Remove し、新しい MSIX をアップロード
2. 計算結果が変わる更新では、Store listing の「What's new」に変更内容を書く
3. Submit for certification

## 7. GitHub に反映

AGPL-3.0 のため、配布したバージョンのソースを公開します。

1. 変更を main に取り込む
2. Releases → 新しいリリースを作成（タグ例: `v1.1.0`）し、変更内容を記載
