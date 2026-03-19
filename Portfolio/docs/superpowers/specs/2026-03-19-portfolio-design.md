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
| フレームワーク | Vite + React 18 + TypeScript |
| スタイリング | Tailwind CSS（ダークテーマ固定） |
| アニメーション | GSAP + ScrollTrigger, SplitType |
| 背景エフェクト | Vanta.js (NET) |
| デプロイ | GitHub Pages または Vercel |
| コンタクトフォーム | EmailJS |

---

## Design Direction

- **テーマ:** Dark × Tech
- **背景色:** `#080b10`
- **テキスト色:** `#f8fafc`
- **アクセントカラー:** Cyan `#06b6d4` / Purple `#a855f7`
- **言語:** 日英バイリンガル

---

## Page Structure

シングルページ縦スクロール（SPA）。セクション順：

```
Hero → Works → Skills → About → Contact
```

### Hero
- Vanta.js NET 背景（cyan × purple）
- SplitType でタイトルを1文字ずつ stagger アニメーション
- キャッチコピー（日英）: `データ × コード × 設計 / Data × Code × Design`
- CTA ボタン: "See My Work" → Works セクションへスクロール
- ナビゲーション: 上部固定、スクロール50px超で blur + 半透明背景

### Works
- GitHubリポジトリをベースにしたプロジェクトカード一覧
- カテゴリフィルター: All / Data Science / Backend / Frontend
- ScrollTrigger でカードがスタッガーで下からフェードイン
- 各カードに: タイトル・説明（日英）・技術タグ・GitHubリンク・デモリンク（任意）

### Skills
- 3領域（Data Science / Backend / Frontend）を横並びパネル
- 各スキルをバッジ形式 + 経験年数で表示
- ScrollTrigger でパネルが順番にスライドイン
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
- `mailto:` リンクも併設

---

## Project Structure

```
F:/playground/Portfolio/
├── public/
│   └── favicon.ico
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
│   │   ├── useGSAP.ts
│   │   └── useVanta.ts
│   ├── data/
│   │   ├── projects.ts
│   │   ├── skills.ts
│   │   └── profile.ts
│   ├── styles/
│   │   └── globals.css
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── tailwind.config.ts
├── vite.config.ts
└── tsconfig.json
```

---

## Animation Architecture

### 基本方針
- 各セクションが自分のアニメーションを `useGSAP` フック内で管理
- コンポーネントアンマウント時に `ctx.revert()` でクリーンアップ
- グローバルタイムラインは持たない

### Hero
```
SplitType → chars 分割
GSAP: from { y: 20, opacity: 0 }, stagger: 0.05
サブテキスト: lines 分割, タイトル完了後フェードイン
CTAボタン: scale + opacity で出現
```

### Works / Skills / About
```
ScrollTrigger:
  trigger: セクション要素
  start: "top 80%"
  animation: y: 40→0, opacity: 0→1, stagger: 0.15
```

### Navbar
```
ScrollTrigger (scrub不要):
  スクロール > 50px → backdrop-blur + bg-opacity追加
```

### Vanta.js
```
useVanta カスタムフック:
  - canvas ref を受け取り useEffect で初期化
  - color: #06b6d4, color2: #a855f7
  - points: 8, maxDistance: 22, spacing: 18
  - クリーンアップ: effect.destroy()
  - ScrollTrigger.refresh() を初期化後に呼ぶ
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
  github: string
  demo?: string
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

```bash
# GitHub Pages
npm run build
npx gh-pages -d dist
```

`vite.config.ts` に `base: '/Portfolio/'` を設定。

---

## Out of Scope

- ブログ機能
- CMS連携
- 多言語切替UI（バイリンガルはコンテンツとして固定記載）
- ダーク/ライトモード切替
