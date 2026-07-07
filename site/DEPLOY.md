# 遅延損害金計算機（PWA版）デプロイ手順

## 構成

```
site/
├── index.html            画面本体（CSS込み）
├── calc.js               計算エンジン（Python版と数値完全一致を検証済み）
├── app.js                UI ロジック
├── sw.js                 Service Worker（ネットワーク優先＋オフライン対応）
├── manifest.webmanifest  PWAマニフェスト
└── icons/                アイコン一式
```

サーバー処理なし・ビルド不要の静的サイト。計算はすべて端末内で完結し、
データの送信・保存は一切行わない。

## Cloudflare Pages へのデプロイ

### 方法A: GitHub連携（推奨・push即反映）

1. このフォルダの中身をリポジトリに置く
   （例: 既存リポジトリに `pwa/` ディレクトリを切る、または専用リポジトリ）
2. Cloudflare ダッシュボード → Workers & Pages → Create → Pages →
   Connect to Git → リポジトリを選択
3. ビルド設定:
   - Framework preset: **None**
   - Build command: **（空欄）**
   - Build output directory: **`pwa/site`**（このフォルダの場所に合わせる）
4. Deploy。`https://＜プロジェクト名＞.pages.dev` が発行される
   （カスタムドメインも Pages の設定から追加可能）

以後は `git push` するだけで自動デプロイ。

### 方法B: 直接アップロード（Git不要）

Workers & Pages → Create → Pages → **Upload assets** → このフォルダをドラッグ。

## 更新時のチェックリスト（重要）

計算ロジック・画面を変更したら、**必ず両方のバージョンを上げる**:

1. `app.js` の `APP_VERSION = "1.0.0"` → 新バージョンへ
2. `sw.js` の `CACHE_VERSION = "entai-calc-v1.0.0"` → 同じ番号へ

CACHE_VERSION を上げ忘れても、Service Worker はネットワーク優先方式のため
オンライン利用者には新版が届くが、番号を揃えておくことで旧キャッシュが
確実に破棄される。**法定利率など計算に関わる変更では特に厳守。**

## AGPL-3.0 について

ネットワーク経由で提供するため AGPL §13 が適用される。
画面フッターと情報ダイアログに GitHub リポジトリへのリンクを設置済みなので、
**公開リポジトリにこの PWA 版のソースも含めること**（site/ をそのまま置けば足りる）。

## 検証済み事項（2026-07-07）

- 計算エンジン: Python 原本（calc_engine.py）と 3,128 ケースで
  全項目（年数・平年日数・閏年日数・総日数・遅延損害金・合計額）完全一致
  - 2/29 起算の応当日処理、閏年跨ぎ、超長期、両端数処理方式を含む
- UI: 和暦/西暦入力、プリセット、設定切替、バリデーション、
  クリア、コピー活性制御を headless テストで確認
- sw.js の ASSETS 全ファイル実在、manifest アイコン実在、バージョン整合
