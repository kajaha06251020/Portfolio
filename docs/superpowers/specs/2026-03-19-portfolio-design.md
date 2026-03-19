# Portfolio Design Spec
**Date:** 2026-03-19
**Author:** kajaha
**Status:** Approved

---

## Overview

フリーランスエンジニア（Data Science / Backend / Frontend）のポートフォリオサイト。
案件獲得を主目的とし、実績を前面に出した構成。
GSAP + ScrollTrigger + Vanta.js + SplitType を用いたリッチなアニメーションを実装する。

---

## Tech Stack

| 項目 | 選択 |
|---|---|
| フレームワーク | Vite + React 18 + TypeScript (`strict: true`) |
| スタイリング | Tailwind CSS（ダークテーマ固定） |
| アニメーション | GSAP + ScrollTrigger, SplitType |
| 背景エフェクト | Vanta.js (NET) + Three.js (peer dependency) |
| デプロイ | GitHub Pages |
| コンタクトフォーム | EmailJS |

### パッケージバージョン（固定）

Vanta.js は Three.js r134 以降で動作しない既知の問題があるため、バージョンを固定する:

```
vanta: 0.5.24
three: 0.134.0
gsap: 3.x（最新）
@gsap/react: 2.x（最新）
split-type: 0.3.x（最新）
```

### Vanta.js セットアップ注記
- `npm install vanta@0.5.24 three@0.134.0` でバージョン固定インストール
- Vite の ESM 環境では `THREE` グローバルが存在しないため、`useVanta.ts` 内で `import * as THREE from 'three'` し `(window as Window & { THREE: typeof THREE }).THREE = THREE` をセット後に `VANTA.NET({...})` を呼ぶ
- `src/types/window.d.ts` で `interface Window { THREE: typeof import('three') }` を宣言（strict 対応）
- Vanta.js の公式型定義は存在しないため、`src/types/vanta.d.ts` に最小限の型宣言を手書きする

### TypeScript 設定
- `tsconfig.json`: `strict: true`
- Vite の `import.meta.env` 型解決は `vite/client` 型定義で対応（`src/vite-env.d.ts` に `/// <reference types="vite/client" />` を記述）。`@types/node` は不要
- GSAP: `npm install gsap @gsap/react`、型定義は GSAP パッケージに同梱
- SplitType: `npm install split-type`、公式型定義が限定的なため `src/types/splittype.d.ts` で補完

---

## Design Direction

- **テーマ:** Dark × Tech
- **背景色:** `#080b10`
- **テキスト色:** `#f8fafc`
- **アクセントカラー:** Cyan `#06b6d4` / Purple `#a855f7`
- **言語:** 日英バイリンガル（コンテンツ固定、切替UIなし）
- **レスポンシブ:** デスクトップファースト。モバイル対応は Out of Scope

---

## Page Structure

シングルページ縦スクロール（SPA）。ルーティングなし（アンカーリンクのみ）。セクション順：

```
Hero → Works → Skills → About → Contact
```

> **SPA / ルーティング方針:** `react-router-dom` は使用しない。すべてのナビゲーションは `scrollIntoView()` によるページ内スクロール。GitHub Pages で 404 問題は発生しない。

### Hero
- Vanta.js NET 背景（cyan × purple）
- SplitType でタイトルを1文字ずつ stagger アニメーション
- キャッチコピー（日英）: `データ × コード × 設計 / Data × Code × Design`
- CTA ボタン: "See My Work" → Works セクションへスクロール
- ナビゲーション: 上部固定、スクロール50px超で blur + 半透明背景

### Works
- コンテンツ: `src/data/projects.ts` に手書き静的データ（GitHub API 呼び出しなし）
- カテゴリフィルター: All / Data Science / Backend / Frontend
  - フィルター状態は React `useState` で管理
  - カテゴリ値とラベルのマッピング: `'data'` → `"Data Science"`, `'backend'` → `"Backend"`, `'frontend'` → `"Frontend"`
  - 非表示カードは `display: none`（レイアウトスペースごと消す）で切替
  - フィルター変更時アニメーション（ScrollTrigger とは独立した別アニメーション）:
    1. 全カードを GSAP で `opacity: 0` にフェードアウト（0.2s）
    2. 完了後に React state を更新 → `display` 切替でレイアウト変更
    3. 表示対象カードを `opacity: 1` にフェードイン（0.3s, stagger: 0.05）
  - 初回スクロール時の ScrollTrigger アニメーション（`y: 40→0, opacity: 0→1`）は一度のみ発火。フィルター後は上記フェードのみ
- 各カードに: タイトル・説明（日英）・技術タグ・GitHubリンク・デモリンク（任意）・サムネイル画像（任意）
  - `image` が未指定の場合はグラデーションプレースホルダーを表示（カテゴリ色をベースにした抽象パターン）

### Skills
- 3領域（Data Science / Backend / Frontend）を横並びパネル
- 各スキルをバッジ形式 + 経験年数で表示
- ScrollTrigger でパネルが順番にフェードアップ（`y: 40→0, opacity: 0→1`、パネルごとに stagger）
- スキル一覧:
  - Data: Python（3-4年）, SQL/PostgreSQL（1-2年）
  - Backend: Node.js（3-4年）, TypeScript（3-4年）, Java（3-4年）, Docker（1-2年）
  - Frontend: React/Next.js（3-4年）, JavaScript（1-2年）

### About
- 自己紹介文（日英）
- フリーランス開始: 2026年
- 強み: データ解析からサービス実装まで一貫して対応、領域横断による課題解決
- 今後の方向性: モデル実運用、スケーラブルなシステム構築、チーム設計改善

### Contact
- SNSリンクカード: GitHub / X / Email
- コンタクトフォーム（名前・メール・メッセージ、EmailJS送信）
  - バリデーション（クライアント側）: 全フィールド必須、メールは RFC 形式チェック、メッセージは最大1000文字
  - 送信中: ボタンをローディング状態に
  - 送信成功: フォームをサンクスメッセージに切替
  - 送信失敗: エラーメッセージをフォーム下部に表示
- `mailto:` リンクも併設
- EmailJS の設定値は `.env` ファイルで管理（`VITE_EMAILJS_SERVICE_ID`, `VITE_EMAILJS_TEMPLATE_ID`, `VITE_EMAILJS_PUBLIC_KEY`）
- `.env.example` はキー名のみ記載してリポジトリにコミットする。`.env` は `.gitignore` 対象

---

## Project Structure

```
F:/playground/Portfolio/
├── public/
│   ├── favicon.ico
│   └── images/             # プロジェクトサムネイル画像（任意）
├── src/
│   ├── components/
│   │   ├── sections/
│   │   │   ├── Hero.tsx
│   │   │   ├── Works.tsx
│   │   │   ├── Skills.tsx
│   │   │   ├── About.tsx
│   │   │   └── Contact.tsx
│   │   └── ui/
│   │       ├── Navbar.tsx
│   │       ├── ProjectCard.tsx
│   │       ├── SkillBadge.tsx
│   │       └── SectionTitle.tsx
│   ├── hooks/
│   │   ├── useScrollAnimation.ts  # ScrollTrigger ラッパー（名前は @gsap/react の useGSAP と衝突回避）
│   │   └── useVanta.ts
│   ├── data/
│   │   ├── projects.ts
│   │   ├── skills.ts
│   │   └── profile.ts
│   ├── types/
│   │   ├── vanta.d.ts      # Vanta.js 型宣言
│   │   ├── splittype.d.ts  # SplitType 型補完
│   │   └── window.d.ts     # window.THREE 型拡張
│   ├── styles/
│   │   └── globals.css
│   ├── vite-env.d.ts       # /// <reference types="vite/client" />
│   ├── App.tsx
│   └── main.tsx
├── .env                    # VITE_EMAILJS_* (gitignore対象)
├── .env.example            # キー名のみ記載、コミット対象
├── index.html
├── tailwind.config.ts
├── vite.config.ts
└── tsconfig.json
```

---

## Animation Architecture

### 基本方針
- `gsap.registerPlugin(ScrollTrigger)` は `main.tsx` で一度だけ呼ぶ（全コンポーネントのレンダー前）
- Hero の一時系アニメーションは `@gsap/react` の `useGSAP` フックを直接使用
- Works / Skills / About のスクロール連動アニメーションは `useScrollAnimation` カスタムフックに委譲
- コンポーネントアンマウント時に `ctx.revert()` でクリーンアップ（`useGSAP` が自動処理）
- グローバルタイムラインは持たない
- `ScrollTrigger.refresh()` は `App.tsx` の `useEffect`（deps: `[]`）内で全セクションマウント後に一度呼ぶ

### `useScrollAnimation` フック（`src/hooks/useScrollAnimation.ts`）

```ts
// シグネチャ
function useScrollAnimation(
  targetRef: RefObject<Element>,      // アニメーション対象要素
  options?: {
    stagger?: number                  // デフォルト: 0.15
    start?: string                    // デフォルト: "top 80%"
    childSelector?: string            // 子要素セレクター（例: ".card"）
  }
): void
```

内部で `useGSAP` を使い、`ScrollTrigger` を設定して `y: 40→0, opacity: 0→1` アニメーションを適用する。

### `useVanta` フック（`src/hooks/useVanta.ts`）

```ts
// シグネチャ
function useVanta(
  containerRef: RefObject<HTMLDivElement>  // Vanta を描画する div の ref
): { isReady: boolean }                   // 初期化完了フラグを返す
```

Hero コンポーネントは `isReady` を受け取り、完了後に `ScrollTrigger.refresh()` トリガーに使う（App.tsx の refresh と併用）。

### Hero
```
SplitType → chars 分割（useGSAP 内で実行）
GSAP timeline:
  1. chars: from { y: 20, opacity: 0 }, stagger: 0.05
  2. lines（サブテキスト）: タイムライン上でタイトル完了後にフェードイン
  3. CTAボタン: scale + opacity で出現
クリーンアップ:
  useGSAP のコールバック内で split インスタンスを変数に保持し、
  コールバックの return 関数で split.revert() を呼ぶ
  例: return () => { split.revert() }
  ※ ctx.revert() は GSAP アニメーションのみ対象。SplitType の DOM 操作は別途 revert() が必要
```

### Works / Skills / About
```
useScrollAnimation(sectionRef, { childSelector: '.card', stagger: 0.15 }) で呼び出し
ScrollTrigger: trigger=セクション要素, start="top 80%"
アニメ: y: 40→0, opacity: 0→1
```

### Works フィルター変更時（ScrollTrigger とは独立）
```
1. gsap.to(allCards, { opacity: 0, duration: 0.2, onComplete: () => {
2.   setFilter(newCategory)  // React state 更新 → display: none 切替
3.   requestAnimationFrame(() => {
4.     gsap.fromTo(visibleCards, { opacity: 0, y: 20 }, { opacity: 1, y: 0, stagger: 0.05 })
5.   })
6. }})
```

### Navbar
```
実装: window.addEventListener('scroll', handler) を useEffect で登録
  → scrollY > 50 で React state を更新 → クラスで背景を切替
  → CSS で backdrop-blur + bg-opacity をトランジション
※ ScrollTrigger は使用しない（単純なしきい値判定のため不要）
```

### Vanta.js
```
useVanta カスタムフック（src/hooks/useVanta.ts）:
  - import * as THREE from 'three'
  - (window as Window & { THREE: typeof THREE }).THREE = THREE
  - containerRef の div に対して VANTA.NET({ el: containerRef.current, ... }) で初期化
  - color: 0x06b6d4, color2: 0xa855f7  ※16進数整数で渡す
  - points: 8, maxDistance: 22, spacing: 18
  - クリーンアップ: effect.destroy()
  - 初期化完了後に isReady: true を返す
```

### prefers-reduced-motion
```
@media (prefers-reduced-motion: reduce) の場合:
  - Vanta.js を初期化しない（useVanta 内で matchMedia チェック）
  - GSAP アニメーションの duration を 0 に設定（即時完了）
  - 静的な表示状態として機能することを保証する
```

---

## Data Types

```ts
// projects.ts
type Project = {
  id: string
  title: string
  description: { ja: string; en: string }
  tags: string[]
  category: 'data' | 'backend' | 'frontend'
  // カテゴリラベルマッピング: 'data'→"Data Science", 'backend'→"Backend", 'frontend'→"Frontend"
  github: string
  demo?: string
  image?: string  // public/images/ 以下のパス。未指定時はカテゴリ色のグラデーションプレースホルダーを表示
}

// skills.ts
type Skill = {
  name: string
  years: '1-2年' | '3-4年'
  domain: 'data' | 'backend' | 'frontend'
}

// profile.ts
type Profile = {
  name: string
  catchcopy: { ja: string; en: string }
  bio: { ja: string; en: string }
  freelanceFrom: number
  contact: {
    email: string
    github: string
    x?: string
  }
}
```

---

## Deployment

**デプロイ先: GitHub Pages（確定）**

`package.json` に追加:
```json
{
  "scripts": {
    "deploy": "npm run build && gh-pages -d dist"
  },
  "devDependencies": {
    "gh-pages": "^6.x"
  }
}
```

`vite.config.ts`:
```ts
export default defineConfig({
  base: '/Portfolio/',   // GitHubリポジトリ名: kajaha06251020/Portfolio
  // ...
})
```

> 名前が異なる場合は `base` をリポジトリ名に合わせて変更すること。

---

## Out of Scope

- ブログ機能
- CMS連携
- 多言語切替UI（バイリンガルはコンテンツとして固定記載）
- ダーク/ライトモード切替
- GitHub API によるリポジトリ自動取得
- SPA ルーティング（react-router-dom）
- モバイル・レスポンシブ対応（デスクトップ表示のみ保証）
- Vanta.js / GSAP の WebGL 未対応デバイスへのフォールバック（`prefers-reduced-motion` の最低限対応を除く）
- パフォーマンスバジェット計測・最適化（Lighthouse スコア保証なし）
