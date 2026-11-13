# 遅延損害金計算機（PWA版）デプロイ手順

## 構成

```
site/
├── index.html            画面本体（CSS込み）
├── calc.js               計算エンジン（Python版と数値完全一致を検証済み）
├── app.js                UI ロジック
├── sw.js                 Service Worker（ネットワーク優先＋オフライン対応）
├── manifest.webmanifest  PWAマニフェスト
├── _headers              Cloudflare Pages 用のセキュリティヘッダ
└── icons/                アイコン一式
```

サーバー処理なし・ビルド不要の静的サイト。計算はすべて端末内で完結し、
データの送信・保存は一切行わない。

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

計算ロジック・画面を変更したら、**必ず両方のバージョンを上げる**:

1. `app.js` の `APP_VERSION = "1.3.2"` → 新バージョンへ
2. `sw.js` の `CACHE_VERSION = "entai-calc-v1.3.2"` → 同じ番号へ

CACHE_VERSION を上げ忘れても、Service Worker はネットワーク優先方式のため
オンライン利用者には新版が届くが、番号を揃えておくことで旧キャッシュが
確実に破棄される。**法定利率など計算に関わる変更では特に厳守。**

## AGPL-3.0 について

ネットワーク経由で提供するため AGPL §13 が適用される。
画面フッターと情報ダイアログに GitHub リポジトリへのリンクを設置済みなので、
**公開リポジトリにこの PWA 版のソースも含めること**（site/ をそのまま置けば足りる）。

## 検証済み事項（2026-11-13・v1.3.2）

- 計算エンジン: Python 版（calc_engine.py）と calc.js が 199,872 ケースで
  全項目（年数・平年日数・閏年日数・総日数・遅延損害金・合計額）完全一致。
  年数・日数は、1日ずつ数える別実装とも全ケース一致
  - 応当日とその前日の支払、2/29 開始、閏年跨ぎ、長期、両端数処理方式を含む
- UI: ブラウザで計算・和暦/西暦入力・利率の入力チェック・情報ダイアログ・
  Service Worker 登録・オフライン再読込を確認（CSP 違反・コンソールエラーなし）
- 検証スクリプトはリポジトリに含めていない
