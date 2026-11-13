# 遅延損害金計算機（PWA版）デプロイ手順

## 構成

```
site/
├── index.html            画面本体（CSS込み）
├── calc.js               計算エンジン（calc_engine.py と同じ結果・同じ明細文）
├── app.js                UI ロジック
├── sw.js                 Service Worker（ネットワーク優先＋オフライン対応）
├── manifest.webmanifest  PWAマニフェスト
├── _headers              Cloudflare Pages 用のセキュリティヘッダ
└── icons/                アイコン一式
```

サーバー処理なし・ビルド不要の静的サイト。計算はすべて端末内で完結し、
データの送信・保存は一切行わない。

`_headers` は Cloudflare Pages 専用。他のホスティングでは効かないので、
同じヘッダ（X-Content-Type-Options、X-Frame-Options など）をそのサービスの方法で設定する。
Content-Security-Policy は index.html に書いてあるため、どのホスティングでも有効。

## Cloudflare Pages へのデプロイ

### 方法A: GitHub連携（推奨・push即反映）

1. このフォルダ（`site/`）をリポジトリに置く（本リポジトリでは直下の `site/`）
2. Cloudflare ダッシュボード → Workers & Pages → Create → Pages →
   Connect to Git → リポジトリを選択
3. ビルド設定:
   - Framework preset: **None**
   - Build command: **（空欄）**
   - Build output directory: **`site`**（このフォルダの場所に合わせる）
4. Deploy。`https://＜プロジェクト名＞.pages.dev` が発行される
   （カスタムドメインも Pages の設定から追加可能）

以後は `git push` するだけで自動デプロイ。

### 方法B: 直接アップロード（Git不要）

Workers & Pages → Create → Pages → **Upload assets** → このフォルダをドラッグ。

## 更新時のチェックリスト（重要）

計算ロジックを変更したら、`calc_engine.py`（デスクトップ版）にも同じ変更を入れ、
リポジトリ直下で `python tests/check_engines.py` を実行して一致を確認する。

計算ロジック・画面を変更したら、**必ず両方のバージョンを上げる**:

1. `app.js` の `APP_VERSION = "1.4.0"` → 新バージョンへ
2. `sw.js` の `CACHE_VERSION = "entai-calc-v1.4.0"` → 同じ番号へ

CACHE_VERSION を上げ忘れても、Service Worker はネットワーク優先方式のため
オンライン利用者には新版が届くが、番号を揃えておくことで旧キャッシュが
確実に破棄される。**法定利率など計算に関わる変更では特に厳守。**

## AGPL-3.0 について

ネットワーク経由で提供するため AGPL §13 が適用される。
画面フッターと情報ダイアログに GitHub リポジトリへのリンクを設置済みなので、
**公開リポジトリにこの PWA 版のソースも含めること**（site/ をそのまま置けば足りる）。

## 検証済み事項（2026-11-13・v1.4.0）

- 計算エンジン: `python tests/check_engines.py` で
  - 手計算の代表例 9 件と一致
  - 年数・日数が、1日ずつ数える別実装と 200,448 ケースで一致
  - calc.js と calc_engine.py が 200,448 ケースで全項目・明細文まで一致
- UI: ブラウザで計算・和暦/西暦入力と切替時の年換算・元号の範囲チェック・
  元本と利率の上限・起算日当日の支払・クリア・Service Worker を確認
  （CSP 違反・コンソールエラーなし）
