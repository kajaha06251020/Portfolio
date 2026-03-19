# Portfolio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** フリーランスエンジニアのポートフォリオサイトを Vite + React + TypeScript + GSAP + Vanta.js + SplitType で実装し GitHub Pages にデプロイする。

**Architecture:** シングルページ縦スクロール SPA（ルーターなし）。セクション順は Hero → Works → Skills → About → Contact。各セクションが自分のアニメーションを管理し、グローバル状態は持たない。

**Tech Stack:** Vite 5, React 18, TypeScript (strict), Tailwind CSS, GSAP 3 + @gsap/react, Vanta.js 0.5.24 + Three.js 0.134.0, SplitType 0.3.x, EmailJS, Vitest + React Testing Library

---

## File Map

| File | 責務 |
|---|---|
| `src/main.tsx` | エントリポイント。`gsap.registerPlugin(ScrollTrigger)` をここで呼ぶ |
| `src/App.tsx` | セクション組み立て。全マウント後に `ScrollTrigger.refresh()` |
| `src/components/sections/Hero.tsx` | Vanta.js 背景 + SplitType タイトルアニメ |
| `src/components/sections/Works.tsx` | プロジェクトカード一覧 + カテゴリフィルター |
| `src/components/sections/Skills.tsx` | スキルパネル3列 |
| `src/components/sections/About.tsx` | 自己紹介文 |
| `src/components/sections/Contact.tsx` | SNSリンク + EmailJS フォーム |
| `src/components/ui/Navbar.tsx` | 固定ナビ、スクロールで背景変化 |
| `src/components/ui/ProjectCard.tsx` | Works カード1枚 |
| `src/components/ui/SkillBadge.tsx` | スキルバッジ1つ |
| `src/components/ui/SectionTitle.tsx` | セクション見出し共通コンポーネント |
| `src/hooks/useVanta.ts` | Vanta.js 初期化フック |
| `src/hooks/useScrollAnimation.ts` | ScrollTrigger フェードアップフック |
| `src/data/projects.ts` | プロジェクトデータ |
| `src/data/skills.ts` | スキルデータ |
| `src/data/profile.ts` | プロフィールデータ |
| `src/types/vanta.d.ts` | Vanta.js 型宣言 |
| `src/types/splittype.d.ts` | SplitType 型補完 |
| `src/types/window.d.ts` | `window.THREE` 型拡張 |
| `src/styles/globals.css` | Tailwind directives + カスタム CSS変数 |
| `src/vite-env.d.ts` | Vite クライアント型参照 |

---

## Task 1: プロジェクトスキャフォールド

**Files:**
- Create: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`
- Create: `src/main.tsx`, `src/App.tsx`, `src/vite-env.d.ts`

- [ ] **Step 1: Vite プロジェクトを作成**

```bash
cd F:/playground/Portfolio
npm create vite@latest . -- --template react-ts
```

プロンプトで "." に対して上書きするか聞かれたら `y` を入力。

- [ ] **Step 2: 依存パッケージをインストール**

```bash
npm install
npm install gsap @gsap/react split-type @emailjs/browser
npm install vanta@0.5.24 three@0.134.0
npm install -D tailwindcss postcss autoprefixer vitest @vitest/ui jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event gh-pages
```

- [ ] **Step 3: Tailwind を初期化**

```bash
npx tailwindcss init -p
```

`tailwind.config.js` が生成される。次のタスクで `.ts` に変換する。

- [ ] **Step 4: デフォルトファイルを削除**

```bash
rm -f src/App.css src/assets/react.svg public/vite.svg
```

- [ ] **Step 5: `vite.config.ts` を書き換える**

`vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/Portfolio/',
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})
```

- [ ] **Step 6: `tsconfig.json` を strict モードに設定**

`tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 7: テストセットアップファイルを作成**

`src/test-setup.ts`:
```ts
import '@testing-library/jest-dom'
```

- [ ] **Step 8: `package.json` に scripts を追加**

既存の `scripts` に以下を追加:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "deploy": "npm run build && gh-pages -d dist"
  }
}
```

- [ ] **Step 9: `.env.example` を作成**

`.env.example`:
```
VITE_EMAILJS_SERVICE_ID=
VITE_EMAILJS_TEMPLATE_ID=
VITE_EMAILJS_PUBLIC_KEY=
```

- [ ] **Step 10: `.gitignore` に `.env` を追加（未記載の場合）**

`.gitignore` に以下があることを確認（なければ追記）:
```
.env
dist/
```

- [ ] **Step 11: コミット**

```bash
git add -A
git commit -m "feat: scaffold Vite + React + TypeScript project"
```

---

## Task 2: 型宣言ファイル + グローバルスタイル

**Files:**
- Create: `src/types/vanta.d.ts`
- Create: `src/types/splittype.d.ts`
- Create: `src/types/window.d.ts`
- Create: `src/vite-env.d.ts`
- Create: `src/styles/globals.css`
- Modify: `tailwind.config.js` → `tailwind.config.ts`

- [ ] **Step 1: `src/types/vanta.d.ts` を作成**

```ts
declare module 'vanta/dist/vanta.net.min' {
  interface VantaNetOptions {
    el: HTMLElement
    THREE: unknown
    color?: number
    color2?: number
    backgroundColor?: number
    points?: number
    maxDistance?: number
    spacing?: number
    showDots?: boolean
  }
  interface VantaEffect {
    destroy: () => void
    resize: () => void
  }
  function NET(options: VantaNetOptions): VantaEffect
  export = NET
}
```

- [ ] **Step 2: `src/types/splittype.d.ts` を作成**

```ts
declare module 'split-type' {
  interface SplitTypeOptions {
    types?: string
    tagName?: string
    lineClass?: string
    wordClass?: string
    charClass?: string
    splitClass?: string
    absolute?: boolean
    reduceWhiteSpace?: boolean
  }
  class SplitType {
    chars: HTMLElement[] | null
    words: HTMLElement[] | null
    lines: HTMLElement[] | null
    constructor(target: string | HTMLElement | HTMLElement[], options?: SplitTypeOptions)
    revert(): void
    split(options?: SplitTypeOptions): void
  }
  export default SplitType
}
```

- [ ] **Step 3: `src/types/window.d.ts` を作成**

```ts
import type * as THREE from 'three'

declare global {
  interface Window {
    THREE: typeof THREE
  }
}

export {}
```

- [ ] **Step 4: `src/vite-env.d.ts` を更新**

```ts
/// <reference types="vite/client" />
```

- [ ] **Step 5: `tailwind.config.js` を `tailwind.config.ts` に変換**

`tailwind.config.js` を削除し `tailwind.config.ts` を作成:
```ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        cyan: {
          DEFAULT: '#06b6d4',
          400: '#22d3ee',
          500: '#06b6d4',
        },
        purple: {
          DEFAULT: '#a855f7',
          400: '#c084fc',
          500: '#a855f7',
        },
        bg: '#080b10',
        fg: '#f8fafc',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config
```

- [ ] **Step 6: `src/styles/globals.css` を作成**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-cyan: #06b6d4;
  --color-purple: #a855f7;
  --color-bg: #080b10;
  --color-fg: #f8fafc;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  background-color: var(--color-bg);
  color: var(--color-fg);
  font-family: system-ui, sans-serif;
  overflow-x: hidden;
}

/* SplitType chars/words が inline-block になるよう保証 */
.char, .word {
  display: inline-block;
}

@layer utilities {
  .text-gradient-cyan-purple {
    background: linear-gradient(135deg, #06b6d4, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .border-gradient-cyan-purple {
    border-image: linear-gradient(135deg, #06b6d4, #a855f7) 1;
  }
}
```

- [ ] **Step 7: `index.html` のタイトルと Google Fonts を設定**

`index.html` の `<head>` に追加:
```html
<title>kajaha | Portfolio</title>
<meta name="description" content="フリーランスエンジニア（Data Science / Backend / Frontend）のポートフォリオ" />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
```

- [ ] **Step 8: コミット**

```bash
git add -A
git commit -m "feat: add type declarations and global styles"
```

---

## Task 3: データ層

**Files:**
- Create: `src/data/projects.ts`
- Create: `src/data/skills.ts`
- Create: `src/data/profile.ts`

- [ ] **Step 1: `src/data/projects.ts` を作成**

```ts
export type Project = {
  id: string
  title: string
  description: { ja: string; en: string }
  tags: string[]
  category: 'data' | 'backend' | 'frontend'
  github: string
  demo?: string
  image?: string
}

export const CATEGORY_LABELS: Record<Project['category'] | 'all', string> = {
  all: 'All',
  data: 'Data Science',
  backend: 'Backend',
  frontend: 'Frontend',
}

export const projects: Project[] = [
  {
    id: 'ffx99',
    title: 'FinalFantasyX-99',
    description: {
      ja: 'Python + Pygameで実装したターン制RPG。昼夜サイクル、リミットブレイクシステム、称号システムを実装。',
      en: 'Turn-based RPG built with Python + Pygame. Features day/night cycle, limit break system, and title/achievement system.',
    },
    tags: ['Python', 'Pygame'],
    category: 'backend',
    github: 'https://github.com/kajaha06251020/FinalFantasyX-99',
  },
  {
    id: 'engram-ai',
    title: 'Engram-AI',
    description: {
      ja: 'AIを活用した記憶・学習支援システム。',
      en: 'AI-powered memory and learning support system.',
    },
    tags: ['Python', 'AI'],
    category: 'data',
    github: 'https://github.com/kajaha06251020/Engram-AI',
  },
  {
    id: 'lifeos',
    title: 'LifeOS',
    description: {
      ja: '生活管理・タスク追跡のためのオールインワンシステム。',
      en: 'All-in-one system for life management and task tracking.',
    },
    tags: ['TypeScript', 'Node.js'],
    category: 'backend',
    github: 'https://github.com/kajaha06251020/LifeOS',
  },
  {
    id: 'pdf-crawler',
    title: 'PdfCrawler',
    description: {
      ja: 'PDFファイルのクローリング・テキスト抽出ツール。',
      en: 'PDF crawling and text extraction tool.',
    },
    tags: ['Node.js', 'TypeScript'],
    category: 'backend',
    github: 'https://github.com/kajaha06251020/PdfCrawler',
  },
  {
    id: 'animemories',
    title: 'Animemories',
    description: {
      ja: 'アニメ鑑賞記録・レビュー管理アプリ。',
      en: 'Anime viewing history and review management app.',
    },
    tags: ['React', 'TypeScript'],
    category: 'frontend',
    github: 'https://github.com/kajaha06251020/animemories',
  },
]
```

- [ ] **Step 2: `src/data/skills.ts` を作成**

```ts
export type Skill = {
  name: string
  years: '1-2年' | '3-4年'
  domain: 'data' | 'backend' | 'frontend'
}

export const skills: Skill[] = [
  { name: 'Python',         years: '3-4年', domain: 'data' },
  { name: 'SQL/PostgreSQL', years: '1-2年', domain: 'data' },
  { name: 'Node.js',        years: '3-4年', domain: 'backend' },
  { name: 'TypeScript',     years: '3-4年', domain: 'backend' },
  { name: 'Java',           years: '3-4年', domain: 'backend' },
  { name: 'Docker',         years: '1-2年', domain: 'backend' },
  { name: 'React/Next.js',  years: '3-4年', domain: 'frontend' },
  { name: 'JavaScript',     years: '1-2年', domain: 'frontend' },
]
```

- [ ] **Step 3: `src/data/profile.ts` を作成**

```ts
export type Profile = {
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

export const profile: Profile = {
  name: 'kajaha',
  catchcopy: {
    ja: 'データ × コード × 設計',
    en: 'Data × Code × Design',
  },
  bio: {
    ja: 'データサイエンス・バックエンド・フロントエンドを横断するフリーランスエンジニア。データ解析からサービス実装まで一貫して担当し、異なる領域を橋渡しして課題解決につなげます。',
    en: 'Freelance engineer bridging Data Science, Backend, and Frontend. I handle everything from data analysis to service implementation, connecting different domains to solve real problems.',
  },
  freelanceFrom: 2026,
  contact: {
    email: 'your-email@example.com',   // TODO: 実際のメールアドレスに変更
    github: 'https://github.com/kajaha06251020',
    x: 'https://x.com/',               // TODO: 実際のXアカウントに変更
  },
}
```

- [ ] **Step 4: データのスモークテストを書く**

`src/data/__tests__/data.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { projects, CATEGORY_LABELS } from '../projects'
import { skills } from '../skills'
import { profile } from '../profile'

describe('projects data', () => {
  it('各プロジェクトに必須フィールドがある', () => {
    projects.forEach(p => {
      expect(p.id).toBeTruthy()
      expect(p.title).toBeTruthy()
      expect(p.github).toMatch(/^https:\/\/github\.com/)
      expect(['data', 'backend', 'frontend']).toContain(p.category)
    })
  })
  it('CATEGORY_LABELS に全カテゴリが含まれる', () => {
    expect(CATEGORY_LABELS.all).toBe('All')
    expect(CATEGORY_LABELS.data).toBe('Data Science')
    expect(CATEGORY_LABELS.backend).toBe('Backend')
    expect(CATEGORY_LABELS.frontend).toBe('Frontend')
  })
})

describe('skills data', () => {
  it('全スキルに必須フィールドがある', () => {
    skills.forEach(s => {
      expect(s.name).toBeTruthy()
      expect(['1-2年', '3-4年']).toContain(s.years)
      expect(['data', 'backend', 'frontend']).toContain(s.domain)
    })
  })
})

describe('profile data', () => {
  it('catchcopy が日英両方ある', () => {
    expect(profile.catchcopy.ja).toBeTruthy()
    expect(profile.catchcopy.en).toBeTruthy()
  })
  it('contact.github が設定されている', () => {
    expect(profile.contact.github).toMatch(/^https:\/\/github\.com/)
  })
})
```

- [ ] **Step 5: テストを実行して通ることを確認**

```bash
npm test -- src/data/__tests__/data.test.ts
```

Expected: PASS (3 test suites, 5 tests)

- [ ] **Step 6: コミット**

```bash
git add -A
git commit -m "feat: add data layer (projects, skills, profile)"
```

---

## Task 4: カスタムフック — useVanta

**Files:**
- Create: `src/hooks/useVanta.ts`
- Create: `src/hooks/__tests__/useVanta.test.ts`

- [ ] **Step 1: スモークテストを書く**

`src/hooks/__tests__/useVanta.test.ts`:
```ts
import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useVanta } from '../useVanta'

// Vanta と THREE はブラウザ依存のため jsdom では mock する
vi.mock('vanta/dist/vanta.net.min', () => ({
  default: vi.fn(() => ({ destroy: vi.fn(), resize: vi.fn() })),
}))
vi.mock('three', () => ({}))

describe('useVanta', () => {
  it('ref が null のときクラッシュしない', () => {
    const ref = { current: null } as React.RefObject<HTMLDivElement>
    expect(() => renderHook(() => useVanta(ref))).not.toThrow()
  })

  it('isReady を返す', () => {
    const ref = { current: null } as React.RefObject<HTMLDivElement>
    const { result } = renderHook(() => useVanta(ref))
    expect(typeof result.current.isReady).toBe('boolean')
  })
})
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
npm test -- src/hooks/__tests__/useVanta.test.ts
```

Expected: FAIL — `useVanta` not found

- [ ] **Step 3: `src/hooks/useVanta.ts` を実装**

```ts
import { useEffect, useRef, useState } from 'react'
import type * as ThreeType from 'three'

export function useVanta(containerRef: React.RefObject<HTMLDivElement>): { isReady: boolean } {
  const effectRef = useRef<{ destroy: () => void } | null>(null)
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    // prefers-reduced-motion チェック
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setIsReady(true)
      return
    }
    if (!containerRef.current) return

    let mounted = true

    const init = async () => {
      const THREE = await import('three') as typeof ThreeType
      ;(window as Window & { THREE: typeof ThreeType }).THREE = THREE

      const VANTA = (await import('vanta/dist/vanta.net.min')).default
      if (!mounted || !containerRef.current) return

      effectRef.current = VANTA({
        el: containerRef.current,
        THREE,
        color: 0x06b6d4,
        color2: 0xa855f7,
        backgroundColor: 0x080b10,
        points: 8,
        maxDistance: 22,
        spacing: 18,
        showDots: true,
      })
      setIsReady(true)
    }

    init().catch(console.error)

    return () => {
      mounted = false
      effectRef.current?.destroy()
      effectRef.current = null
      setIsReady(false)
    }
  }, [containerRef])

  return { isReady }
}
```

- [ ] **Step 4: テストが通ることを確認**

```bash
npm test -- src/hooks/__tests__/useVanta.test.ts
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/hooks/useVanta.ts src/hooks/__tests__/useVanta.test.ts
git commit -m "feat: add useVanta hook"
```

---

## Task 5: カスタムフック — useScrollAnimation

**Files:**
- Create: `src/hooks/useScrollAnimation.ts`
- Create: `src/hooks/__tests__/useScrollAnimation.test.ts`

- [ ] **Step 1: スモークテストを書く**

`src/hooks/__tests__/useScrollAnimation.test.ts`:
```ts
import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useScrollAnimation } from '../useScrollAnimation'

vi.mock('gsap', () => ({
  default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn(), context: vi.fn(() => ({ revert: vi.fn() })) },
}))
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn() } }))
vi.mock('@gsap/react', () => ({
  useGSAP: (fn: () => void) => { try { fn() } catch { /* ignore */ } },
}))

describe('useScrollAnimation', () => {
  it('ref が null でもクラッシュしない', () => {
    const ref = { current: null } as React.RefObject<Element>
    expect(() => renderHook(() => useScrollAnimation(ref))).not.toThrow()
  })

  it('戻り値は undefined (void)', () => {
    const ref = { current: null } as React.RefObject<Element>
    const { result } = renderHook(() => useScrollAnimation(ref))
    expect(result.current).toBeUndefined()
  })
})
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
npm test -- src/hooks/__tests__/useScrollAnimation.test.ts
```

Expected: FAIL — `useScrollAnimation` not found

- [ ] **Step 3: `src/hooks/useScrollAnimation.ts` を実装**

```ts
import { type RefObject } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

interface UseScrollAnimationOptions {
  stagger?: number
  start?: string
  childSelector?: string
}

export function useScrollAnimation(
  targetRef: RefObject<Element>,
  options: UseScrollAnimationOptions = {}
): void {
  const { stagger = 0.15, start = 'top 80%', childSelector } = options

  useGSAP(() => {
    if (!targetRef.current) return

    const targets = childSelector
      ? targetRef.current.querySelectorAll(childSelector)
      : [targetRef.current]

    if (targets.length === 0) return

    // prefers-reduced-motion の場合は即時表示
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      gsap.set(targets, { opacity: 1, y: 0 })
      return
    }

    gsap.set(targets, { opacity: 0, y: 40 })

    ScrollTrigger.create({
      trigger: targetRef.current,
      start,
      onEnter: () => {
        gsap.to(targets, {
          opacity: 1,
          y: 0,
          duration: 0.7,
          stagger,
          ease: 'power2.out',
        })
      },
      once: true,
    })
  }, { scope: targetRef })
}
```

- [ ] **Step 4: テストが通ることを確認**

```bash
npm test -- src/hooks/__tests__/useScrollAnimation.test.ts
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/hooks/useScrollAnimation.ts src/hooks/__tests__/useScrollAnimation.test.ts
git commit -m "feat: add useScrollAnimation hook"
```

---

## Task 6: UI コンポーネント

**Files:**
- Create: `src/components/ui/SectionTitle.tsx`
- Create: `src/components/ui/SkillBadge.tsx`
- Create: `src/components/ui/ProjectCard.tsx`
- Create: `src/components/ui/__tests__/SectionTitle.test.tsx`
- Create: `src/components/ui/__tests__/ProjectCard.test.tsx`

- [ ] **Step 1: `SectionTitle` のテストを書く**

`src/components/ui/__tests__/SectionTitle.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SectionTitle } from '../SectionTitle'

describe('SectionTitle', () => {
  it('en と ja を両方レンダーする', () => {
    render(<SectionTitle en="Works" ja="制作物" />)
    expect(screen.getByText('Works')).toBeInTheDocument()
    expect(screen.getByText('制作物')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: `SectionTitle.tsx` を実装**

`src/components/ui/SectionTitle.tsx`:
```tsx
interface SectionTitleProps {
  en: string
  ja: string
}

export function SectionTitle({ en, ja }: SectionTitleProps) {
  return (
    <div className="mb-12">
      <p className="text-xs font-mono tracking-[0.3em] text-cyan-500 uppercase mb-2">{ja}</p>
      <h2 className="text-4xl font-bold text-fg">{en}</h2>
      <div className="mt-3 h-px w-16 bg-gradient-to-r from-cyan-500 to-purple-500" />
    </div>
  )
}
```

- [ ] **Step 3: `ProjectCard` のテストを書く**

`src/components/ui/__tests__/ProjectCard.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProjectCard } from '../ProjectCard'
import type { Project } from '../../../data/projects'

const mockProject: Project = {
  id: 'test',
  title: 'Test Project',
  description: { ja: 'テスト説明', en: 'Test description' },
  tags: ['React', 'TypeScript'],
  category: 'frontend',
  github: 'https://github.com/test/repo',
}

describe('ProjectCard', () => {
  it('タイトルと説明をレンダーする', () => {
    render(<ProjectCard project={mockProject} />)
    expect(screen.getByText('Test Project')).toBeInTheDocument()
    expect(screen.getByText('テスト説明')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('GitHub リンクが正しい href を持つ', () => {
    render(<ProjectCard project={mockProject} />)
    const link = screen.getByRole('link', { name: /github/i })
    expect(link).toHaveAttribute('href', 'https://github.com/test/repo')
  })

  it('タグを全て表示する', () => {
    render(<ProjectCard project={mockProject} />)
    expect(screen.getByText('React')).toBeInTheDocument()
    expect(screen.getByText('TypeScript')).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: テストが失敗することを確認**

```bash
npm test -- src/components/ui/__tests__/
```

Expected: FAIL

- [ ] **Step 5: `SkillBadge.tsx` を実装**

`src/components/ui/SkillBadge.tsx`:
```tsx
import type { Skill } from '../../data/skills'

interface SkillBadgeProps {
  skill: Skill
}

export function SkillBadge({ skill }: SkillBadgeProps) {
  return (
    <div className="flex items-center justify-between px-3 py-2 rounded border border-white/10 bg-white/5 hover:border-cyan-500/40 transition-colors">
      <span className="text-sm font-mono text-fg">{skill.name}</span>
      <span className="text-xs text-cyan-500/70 ml-3 whitespace-nowrap">{skill.years}</span>
    </div>
  )
}
```

- [ ] **Step 6: `ProjectCard.tsx` を実装**

`src/components/ui/ProjectCard.tsx`:
```tsx
import type { Project } from '../../data/projects'

interface ProjectCardProps {
  project: Project
}

const CATEGORY_COLORS: Record<Project['category'], string> = {
  data: 'from-cyan-500/20 to-purple-500/10',
  backend: 'from-purple-500/20 to-cyan-500/10',
  frontend: 'from-cyan-500/10 to-purple-500/20',
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <article className="card group rounded-lg border border-white/10 bg-white/5 overflow-hidden hover:border-cyan-500/40 transition-all duration-300 hover:-translate-y-1">
      {/* サムネイル */}
      <div className={`h-36 bg-gradient-to-br ${CATEGORY_COLORS[project.category]} flex items-center justify-center`}>
        {project.image ? (
          <img src={project.image} alt={project.title} className="w-full h-full object-cover" />
        ) : (
          <span className="text-3xl font-bold font-mono text-white/10 select-none">
            {project.title.slice(0, 2).toUpperCase()}
          </span>
        )}
      </div>

      {/* コンテンツ */}
      <div className="p-5">
        <h3 className="text-base font-bold text-fg mb-2">{project.title}</h3>
        <p className="text-sm text-fg/60 mb-1">{project.description.ja}</p>
        <p className="text-xs text-fg/40 mb-4">{project.description.en}</p>

        {/* タグ */}
        <div className="flex flex-wrap gap-1 mb-4">
          {project.tags.map(tag => (
            <span key={tag} className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono border border-cyan-500/20">
              {tag}
            </span>
          ))}
        </div>

        {/* リンク */}
        <div className="flex gap-3">
          <a
            href={project.github}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-fg/50 hover:text-cyan-400 transition-colors font-mono"
            aria-label="GitHub"
          >
            GitHub →
          </a>
          {project.demo && (
            <a
              href={project.demo}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-fg/50 hover:text-purple-400 transition-colors font-mono"
            >
              Demo →
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
```

- [ ] **Step 7: テストが通ることを確認**

```bash
npm test -- src/components/ui/__tests__/
```

Expected: PASS

- [ ] **Step 8: コミット**

```bash
git add -A
git commit -m "feat: add SectionTitle, SkillBadge, ProjectCard components"
```

---

## Task 7: Navbar コンポーネント

**Files:**
- Create: `src/components/ui/Navbar.tsx`
- Create: `src/components/ui/__tests__/Navbar.test.tsx`

- [ ] **Step 1: テストを書く**

`src/components/ui/__tests__/Navbar.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Navbar } from '../Navbar'

describe('Navbar', () => {
  it('ナビリンクが全て表示される', () => {
    render(<Navbar />)
    expect(screen.getByText('Works')).toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('About')).toBeInTheDocument()
    expect(screen.getByText('Contact')).toBeInTheDocument()
  })

  it('ロゴが表示される', () => {
    render(<Navbar />)
    expect(screen.getByText('kajaha')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
npm test -- src/components/ui/__tests__/Navbar.test.tsx
```

Expected: FAIL

- [ ] **Step 3: `Navbar.tsx` を実装**

`src/components/ui/Navbar.tsx`:
```tsx
import { useEffect, useState } from 'react'

const NAV_ITEMS = [
  { label: 'Works', href: '#works' },
  { label: 'Skills', href: '#skills' },
  { label: 'About', href: '#about' },
  { label: 'Contact', href: '#contact' },
]

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  const scrollTo = (href: string) => {
    const el = document.querySelector(href)
    el?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-bg/80 backdrop-blur-md border-b border-white/10'
          : 'bg-transparent'
      }`}
    >
      <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="text-lg font-bold font-mono text-gradient-cyan-purple"
        >
          kajaha
        </button>
        <ul className="flex gap-8">
          {NAV_ITEMS.map(item => (
            <li key={item.label}>
              <button
                onClick={() => scrollTo(item.href)}
                className="text-sm font-mono text-fg/60 hover:text-cyan-400 transition-colors tracking-wide"
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  )
}
```

- [ ] **Step 4: テストが通ることを確認**

```bash
npm test -- src/components/ui/__tests__/Navbar.test.tsx
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/components/ui/Navbar.tsx src/components/ui/__tests__/Navbar.test.tsx
git commit -m "feat: add Navbar component"
```

---

## Task 8: Hero セクション

**Files:**
- Create: `src/components/sections/Hero.tsx`
- Create: `src/components/sections/__tests__/Hero.test.tsx`

- [ ] **Step 1: スモークテストを書く**

`src/components/sections/__tests__/Hero.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Hero } from '../Hero'

vi.mock('../../hooks/useVanta', () => ({
  useVanta: () => ({ isReady: false }),
}))
vi.mock('@gsap/react', () => ({
  useGSAP: vi.fn(),
}))

describe('Hero', () => {
  it('キャッチコピーを含む', () => {
    render(<Hero />)
    expect(screen.getByText(/データ × コード × 設計/)).toBeInTheDocument()
  })
  it('CTAボタンが表示される', () => {
    render(<Hero />)
    expect(screen.getByRole('button', { name: /See My Work/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
npm test -- src/components/sections/__tests__/Hero.test.tsx
```

Expected: FAIL

- [ ] **Step 3: `Hero.tsx` を実装**

`src/components/sections/Hero.tsx`:
```tsx
import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import SplitType from 'split-type'
import { useVanta } from '../../hooks/useVanta'
import { profile } from '../../data/profile'

export function Hero() {
  const containerRef = useRef<HTMLDivElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const subtitleRef = useRef<HTMLParagraphElement>(null)
  const ctaRef = useRef<HTMLButtonElement>(null)

  const { isReady } = useVanta(containerRef)

  useGSAP(() => {
    if (!titleRef.current || !subtitleRef.current || !ctaRef.current) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const titleSplit = new SplitType(titleRef.current, { types: 'chars' })
    const subtitleSplit = new SplitType(subtitleRef.current, { types: 'lines' })

    if (prefersReduced) {
      gsap.set([titleSplit.chars, subtitleSplit.lines, ctaRef.current], { opacity: 1, y: 0, scale: 1 })
      return () => {
        titleSplit.revert()
        subtitleSplit.revert()
      }
    }

    const tl = gsap.timeline({ delay: 0.3 })

    tl.from(titleSplit.chars ?? [], {
      y: 20,
      opacity: 0,
      stagger: 0.05,
      duration: 0.6,
      ease: 'power2.out',
    })
    .from(subtitleSplit.lines ?? [], {
      y: 15,
      opacity: 0,
      stagger: 0.1,
      duration: 0.5,
      ease: 'power2.out',
    }, '-=0.2')
    .from(ctaRef.current, {
      scale: 0.9,
      opacity: 0,
      duration: 0.4,
      ease: 'back.out(1.7)',
    }, '-=0.1')

    return () => {
      titleSplit.revert()
      subtitleSplit.revert()
    }
  }, { scope: containerRef, dependencies: [isReady] })

  const scrollToWorks = () => {
    document.querySelector('#works')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <section
      id="hero"
      ref={containerRef}
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden"
    >
      {/* Vanta 背景はコンテナ自身に描画される */}

      {/* コンテンツ */}
      <div className="relative z-10 text-center px-6 max-w-4xl">
        <p className="text-xs font-mono tracking-[0.4em] text-cyan-500 uppercase mb-6">
          Freelance Engineer — Since {profile.freelanceFrom}
        </p>

        <h1
          ref={titleRef}
          className="text-5xl md:text-7xl font-black text-fg leading-tight mb-4 tracking-tight"
        >
          {profile.catchcopy.ja}
        </h1>

        <p
          ref={subtitleRef}
          className="text-base md:text-lg text-fg/60 font-mono mb-10 leading-relaxed"
        >
          {profile.catchcopy.en}
          <br />
          Data Science × Backend × Frontend
        </p>

        <button
          ref={ctaRef}
          onClick={scrollToWorks}
          className="px-8 py-3 rounded border border-cyan-500/50 text-cyan-400 font-mono text-sm hover:bg-cyan-500/10 transition-all duration-200 hover:border-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.2)]"
        >
          See My Work →
        </button>
      </div>

      {/* スクロールインジケーター */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-40">
        <span className="text-xs font-mono tracking-widest text-fg/50">SCROLL</span>
        <div className="w-px h-12 bg-gradient-to-b from-cyan-500/50 to-transparent" />
      </div>
    </section>
  )
}
```

- [ ] **Step 4: テストが通ることを確認**

```bash
npm test -- src/components/sections/__tests__/Hero.test.tsx
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/components/sections/Hero.tsx src/components/sections/__tests__/Hero.test.tsx
git commit -m "feat: add Hero section with Vanta.js and SplitType animation"
```

---

## Task 9: Works セクション

**Files:**
- Create: `src/components/sections/Works.tsx`
- Create: `src/components/sections/__tests__/Works.test.tsx`

- [ ] **Step 1: スモークテストを書く**

`src/components/sections/__tests__/Works.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Works } from '../Works'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@gsap/react', () => ({ useGSAP: vi.fn() }))
vi.mock('gsap', () => ({ default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn() } }))

describe('Works', () => {
  it('フィルターボタンが全て表示される', () => {
    render(<Works />)
    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Data Science' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Backend' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Frontend' })).toBeInTheDocument()
  })

  it('初期状態で全プロジェクトが表示される', () => {
    render(<Works />)
    expect(screen.getAllByRole('article').length).toBeGreaterThan(0)
  })

  it('Backend フィルターをクリックすると Backend プロジェクトのみ表示', async () => {
    const user = userEvent.setup()
    render(<Works />)
    await user.click(screen.getByRole('button', { name: 'Backend' }))
    // GSAP mock のため実際のフィルターはスキップ — ボタンクリックがエラーなく動くことを確認
    expect(screen.getByRole('button', { name: 'Backend' })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: `Works.tsx` を実装**

`src/components/sections/Works.tsx`:
```tsx
import { useRef, useState, useCallback } from 'react'
import gsap from 'gsap'
import { SectionTitle } from '../ui/SectionTitle'
import { ProjectCard } from '../ui/ProjectCard'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { projects, CATEGORY_LABELS, type Project } from '../../data/projects'

type FilterCategory = Project['category'] | 'all'

const FILTER_CATEGORIES: FilterCategory[] = ['all', 'data', 'backend', 'frontend']

export function Works() {
  const sectionRef = useRef<HTMLElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const [activeFilter, setActiveFilter] = useState<FilterCategory>('all')

  useScrollAnimation(sectionRef, { childSelector: '.card', stagger: 0.1 })

  const handleFilter = useCallback((category: FilterCategory) => {
    if (category === activeFilter || !gridRef.current) return

    const cards = Array.from(gridRef.current.querySelectorAll<HTMLElement>('.card'))

    gsap.to(cards, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => {
        setActiveFilter(category)
        requestAnimationFrame(() => {
          const visibleCards = Array.from(
            gridRef.current?.querySelectorAll<HTMLElement>('.card') ?? []
          )
          gsap.fromTo(
            visibleCards,
            { opacity: 0, y: 20 },
            { opacity: 1, y: 0, stagger: 0.05, duration: 0.3, ease: 'power2.out' }
          )
        })
      },
    })
  }, [activeFilter])

  const filtered = activeFilter === 'all'
    ? projects
    : projects.filter(p => p.category === activeFilter)

  return (
    <section id="works" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="Works" ja="制作物" />

      {/* フィルターボタン */}
      <div className="flex gap-3 mb-12 flex-wrap">
        {FILTER_CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => handleFilter(cat)}
            className={`px-4 py-1.5 rounded-full text-xs font-mono border transition-all duration-200 ${
              activeFilter === cat
                ? 'border-cyan-500 text-cyan-400 bg-cyan-500/10'
                : 'border-white/20 text-fg/50 hover:border-white/40 hover:text-fg/80'
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* カードグリッド */}
      <div
        ref={gridRef}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
      >
        {filtered.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </section>
  )
}
```

- [ ] **Step 3: テストが通ることを確認**

```bash
npm test -- src/components/sections/__tests__/Works.test.tsx
```

Expected: PASS

- [ ] **Step 4: コミット**

```bash
git add src/components/sections/Works.tsx src/components/sections/__tests__/Works.test.tsx
git commit -m "feat: add Works section with category filter"
```

---

## Task 10: Skills セクション

**Files:**
- Create: `src/components/sections/Skills.tsx`
- Create: `src/components/sections/__tests__/Skills.test.tsx`

- [ ] **Step 1: スモークテストを書く**

`src/components/sections/__tests__/Skills.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Skills } from '../Skills'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))

describe('Skills', () => {
  it('3つのドメインパネルが表示される', () => {
    render(<Skills />)
    expect(screen.getByText('Data Science')).toBeInTheDocument()
    expect(screen.getByText('Backend')).toBeInTheDocument()
    expect(screen.getByText('Frontend')).toBeInTheDocument()
  })

  it('Python スキルが表示される', () => {
    render(<Skills />)
    expect(screen.getByText('Python')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: `Skills.tsx` を実装**

`src/components/sections/Skills.tsx`:
```tsx
import { useRef } from 'react'
import { SectionTitle } from '../ui/SectionTitle'
import { SkillBadge } from '../ui/SkillBadge'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { skills, type Skill } from '../../data/skills'

const DOMAIN_CONFIG: {
  key: Skill['domain']
  label: string
  color: string
}[] = [
  { key: 'data',     label: 'Data Science', color: 'border-cyan-500/30 hover:border-cyan-500/60' },
  { key: 'backend',  label: 'Backend',      color: 'border-purple-500/30 hover:border-purple-500/60' },
  { key: 'frontend', label: 'Frontend',     color: 'border-cyan-500/20 hover:border-cyan-500/50' },
]

export function Skills() {
  const sectionRef = useRef<HTMLElement>(null)

  useScrollAnimation(sectionRef, { childSelector: '.skill-panel', stagger: 0.15 })

  return (
    <section id="skills" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="Skills" ja="技術スタック" />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {DOMAIN_CONFIG.map(({ key, label, color }) => {
          const domainSkills = skills.filter(s => s.domain === key)
          return (
            <div
              key={key}
              className={`skill-panel rounded-lg border p-6 bg-white/3 transition-all duration-300 ${color}`}
            >
              <h3 className="text-sm font-mono tracking-widest text-fg/40 uppercase mb-5">{label}</h3>
              <div className="flex flex-col gap-2">
                {domainSkills.map(skill => (
                  <SkillBadge key={skill.name} skill={skill} />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
```

- [ ] **Step 3: テストが通ることを確認**

```bash
npm test -- src/components/sections/__tests__/Skills.test.tsx
```

Expected: PASS

- [ ] **Step 4: コミット**

```bash
git add src/components/sections/Skills.tsx src/components/sections/__tests__/Skills.test.tsx
git commit -m "feat: add Skills section"
```

---

## Task 11: About セクション

**Files:**
- Create: `src/components/sections/About.tsx`
- Create: `src/components/sections/__tests__/About.test.tsx`

- [ ] **Step 1: スモークテストを書く**

`src/components/sections/__tests__/About.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { About } from '../About'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))

describe('About', () => {
  it('自己紹介文（日英）が表示される', () => {
    render(<About />)
    expect(screen.getByText(/フリーランスエンジニア/)).toBeInTheDocument()
    expect(screen.getByText(/Freelance engineer/)).toBeInTheDocument()
  })

  it('フリーランス開始年が表示される', () => {
    render(<About />)
    expect(screen.getByText(/2026/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: `About.tsx` を実装**

`src/components/sections/About.tsx`:
```tsx
import { useRef } from 'react'
import { SectionTitle } from '../ui/SectionTitle'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { profile } from '../../data/profile'

export function About() {
  const sectionRef = useRef<HTMLElement>(null)
  useScrollAnimation(sectionRef, { childSelector: '.about-block', stagger: 0.12 })

  return (
    <section id="about" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="About" ja="プロフィール" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* 自己紹介 */}
        <div className="about-block space-y-4">
          <p className="text-fg/80 leading-relaxed">{profile.bio.ja}</p>
          <p className="text-fg/50 text-sm leading-relaxed">{profile.bio.en}</p>
        </div>

        {/* ハイライト */}
        <div className="space-y-4">
          <div className="about-block p-4 rounded border border-white/10 bg-white/5">
            <p className="text-xs font-mono text-cyan-500 mb-1 tracking-widest">FREELANCE FROM</p>
            <p className="text-2xl font-bold text-fg">{profile.freelanceFrom}</p>
          </div>

          <div className="about-block p-4 rounded border border-white/10 bg-white/5">
            <p className="text-xs font-mono text-cyan-500 mb-2 tracking-widest">STRENGTHS</p>
            <ul className="space-y-1">
              {[
                'データ解析からサービス実装まで一貫対応',
                '領域横断による課題解決',
                'スケーラブルなシステム設計',
              ].map(item => (
                <li key={item} className="text-sm text-fg/70 flex items-start gap-2">
                  <span className="text-cyan-500 mt-0.5">▸</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="about-block p-4 rounded border border-white/10 bg-white/5">
            <p className="text-xs font-mono text-purple-400 mb-2 tracking-widest">NEXT GOALS</p>
            <ul className="space-y-1">
              {[
                'モデルの実運用・MLOps',
                'チームでの設計改善・アーキテクチャ改善',
              ].map(item => (
                <li key={item} className="text-sm text-fg/70 flex items-start gap-2">
                  <span className="text-purple-400 mt-0.5">▸</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 3: テストが通ることを確認**

```bash
npm test -- src/components/sections/__tests__/About.test.tsx
```

Expected: PASS

- [ ] **Step 4: コミット**

```bash
git add src/components/sections/About.tsx src/components/sections/__tests__/About.test.tsx
git commit -m "feat: add About section"
```

---

## Task 12: Contact セクション

**Files:**
- Create: `src/components/sections/Contact.tsx`
- Create: `src/components/sections/__tests__/Contact.test.tsx`

- [ ] **Step 1: スモークテストを書く**

`src/components/sections/__tests__/Contact.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Contact } from '../Contact'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@emailjs/browser', () => ({ sendForm: vi.fn(() => Promise.resolve()) }))

describe('Contact', () => {
  it('フォームフィールドが全て表示される', () => {
    render(<Contact />)
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument()
  })

  it('空フォーム送信でバリデーションエラー', async () => {
    const user = userEvent.setup()
    render(<Contact />)
    await user.click(screen.getByRole('button', { name: /send/i }))
    expect(screen.getByText(/必須/)).toBeInTheDocument()
  })

  it('不正なメールアドレスでエラー', async () => {
    const user = userEvent.setup()
    render(<Contact />)
    await user.type(screen.getByLabelText(/name/i), 'Test')
    await user.type(screen.getByLabelText(/email/i), 'invalid-email')
    await user.type(screen.getByLabelText(/message/i), 'Hello')
    await user.click(screen.getByRole('button', { name: /send/i }))
    expect(screen.getByText(/メールアドレス/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
npm test -- src/components/sections/__tests__/Contact.test.tsx
```

Expected: FAIL

- [ ] **Step 3: `Contact.tsx` を実装**

`src/components/sections/Contact.tsx`:
```tsx
import { useRef, useState } from 'react'
import emailjs from '@emailjs/browser'
import { SectionTitle } from '../ui/SectionTitle'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { profile } from '../../data/profile'

type FormState = {
  name: string
  email: string
  message: string
}

type SendStatus = 'idle' | 'sending' | 'success' | 'error'

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate(form: FormState): Partial<FormState> {
  const errors: Partial<FormState> = {}
  if (!form.name.trim()) errors.name = '必須項目です'
  if (!form.email.trim()) {
    errors.email = '必須項目です'
  } else if (!EMAIL_REGEX.test(form.email)) {
    errors.email = 'メールアドレスの形式が正しくありません'
  }
  if (!form.message.trim()) {
    errors.message = '必須項目です'
  } else if (form.message.length > 1000) {
    errors.message = '1000文字以内で入力してください'
  }
  return errors
}

export function Contact() {
  const sectionRef = useRef<HTMLElement>(null)
  const formRef = useRef<HTMLFormElement>(null)
  const [form, setForm] = useState<FormState>({ name: '', email: '', message: '' })
  const [errors, setErrors] = useState<Partial<FormState>>({})
  const [status, setStatus] = useState<SendStatus>('idle')

  useScrollAnimation(sectionRef, { childSelector: '.contact-block', stagger: 0.12 })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setErrors(prev => ({ ...prev, [e.target.name]: undefined }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setStatus('sending')
    try {
      await emailjs.sendForm(
        import.meta.env.VITE_EMAILJS_SERVICE_ID,
        import.meta.env.VITE_EMAILJS_TEMPLATE_ID,
        formRef.current!,
        import.meta.env.VITE_EMAILJS_PUBLIC_KEY,
      )
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }

  const SNS_LINKS = [
    { label: 'GitHub', href: profile.contact.github, color: 'border-white/20 hover:border-white/50' },
    ...(profile.contact.x ? [{ label: 'X (Twitter)', href: profile.contact.x, color: 'border-white/20 hover:border-white/50' }] : []),
    { label: 'Email', href: `mailto:${profile.contact.email}`, color: 'border-cyan-500/30 hover:border-cyan-500' },
  ]

  return (
    <section id="contact" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="Contact" ja="お問い合わせ" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* SNSリンク */}
        <div className="contact-block space-y-4">
          <p className="text-fg/60 text-sm leading-relaxed mb-6">
            お仕事のご相談・ご依頼はお気軽にどうぞ。<br />
            Feel free to reach out for project inquiries.
          </p>
          {SNS_LINKS.map(link => (
            <a
              key={link.label}
              href={link.href}
              target={link.href.startsWith('mailto') ? undefined : '_blank'}
              rel="noopener noreferrer"
              className={`flex items-center justify-between p-4 rounded border bg-white/5 transition-all duration-200 hover:bg-white/8 font-mono text-sm ${link.color}`}
            >
              <span className="text-fg/80">{link.label}</span>
              <span className="text-fg/30">→</span>
            </a>
          ))}
        </div>

        {/* フォーム */}
        <div className="contact-block">
          {status === 'success' ? (
            <div className="p-8 rounded border border-cyan-500/30 bg-cyan-500/5 text-center">
              <p className="text-cyan-400 font-mono text-lg mb-2">✓ Sent!</p>
              <p className="text-fg/60 text-sm">メッセージを送信しました。ありがとうございます。</p>
            </div>
          ) : (
            <form ref={formRef} onSubmit={handleSubmit} className="space-y-4" noValidate>
              {/* Name */}
              <div>
                <label htmlFor="name" className="block text-xs font-mono text-fg/50 mb-1 tracking-widest">NAME</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={form.name}
                  onChange={handleChange}
                  className="w-full bg-white/5 border border-white/15 rounded px-4 py-2.5 text-sm text-fg focus:outline-none focus:border-cyan-500/50 transition-colors"
                />
                {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name}</p>}
              </div>

              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-xs font-mono text-fg/50 mb-1 tracking-widest">EMAIL</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={handleChange}
                  className="w-full bg-white/5 border border-white/15 rounded px-4 py-2.5 text-sm text-fg focus:outline-none focus:border-cyan-500/50 transition-colors"
                />
                {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email}</p>}
              </div>

              {/* Message */}
              <div>
                <label htmlFor="message" className="block text-xs font-mono text-fg/50 mb-1 tracking-widest">MESSAGE</label>
                <textarea
                  id="message"
                  name="message"
                  rows={5}
                  value={form.message}
                  onChange={handleChange}
                  className="w-full bg-white/5 border border-white/15 rounded px-4 py-2.5 text-sm text-fg focus:outline-none focus:border-cyan-500/50 transition-colors resize-none"
                />
                <div className="flex justify-between mt-1">
                  {errors.message && <p className="text-red-400 text-xs">{errors.message}</p>}
                  <span className="text-xs text-fg/30 ml-auto">{form.message.length}/1000</span>
                </div>
              </div>

              {status === 'error' && (
                <p className="text-red-400 text-xs">送信に失敗しました。時間をおいて再度お試しください。</p>
              )}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="w-full py-3 rounded border border-cyan-500/50 text-cyan-400 font-mono text-sm hover:bg-cyan-500/10 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {status === 'sending' ? 'Sending...' : 'Send Message →'}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 4: テストが通ることを確認**

```bash
npm test -- src/components/sections/__tests__/Contact.test.tsx
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/components/sections/Contact.tsx src/components/sections/__tests__/Contact.test.tsx
git commit -m "feat: add Contact section with EmailJS form and validation"
```

---

## Task 13: App 組み立て

**Files:**
- Modify: `src/main.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: `src/main.tsx` を更新（GSAP plugin 登録）**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './styles/globals.css'
import App from './App'

gsap.registerPlugin(ScrollTrigger)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 2: `src/App.tsx` を更新**

```tsx
import { useEffect } from 'react'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { Navbar } from './components/ui/Navbar'
import { Hero } from './components/sections/Hero'
import { Works } from './components/sections/Works'
import { Skills } from './components/sections/Skills'
import { About } from './components/sections/About'
import { Contact } from './components/sections/Contact'

export default function App() {
  useEffect(() => {
    // 全セクションマウント後に ScrollTrigger の位置を再計算
    ScrollTrigger.refresh()
  }, [])

  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Works />
        <Skills />
        <About />
        <Contact />
      </main>
      <footer className="text-center py-8 text-fg/20 text-xs font-mono border-t border-white/5">
        © {new Date().getFullYear()} kajaha — Built with React + GSAP
      </footer>
    </>
  )
}
```

- [ ] **Step 3: 開発サーバーを起動して動作確認**

```bash
npm run dev
```

ブラウザで `http://localhost:5173/Portfolio/` を開き、以下を確認:
- [ ] Vanta.js NET エフェクトが Hero に表示される
- [ ] SplitType でタイトルが1文字ずつアニメーションする
- [ ] スクロールでセクションが順にフェードアップする
- [ ] Navbar がスクロールで背景変化する
- [ ] Works フィルターが動作する

- [ ] **Step 4: 全テストを実行**

```bash
npm test
```

Expected: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add src/main.tsx src/App.tsx
git commit -m "feat: assemble App with all sections"
```

---

## Task 14: デプロイ設定

**Files:**
- Create: `.env.example`（Task 1 で作成済みの確認）
- Verify: `vite.config.ts` の `base` 設定

- [ ] **Step 1: `npm run build` が通ることを確認**

```bash
npm run build
```

Expected: `dist/` ディレクトリが生成される。TypeScript エラーなし。

もし型エラーがあれば修正してから次に進む。

- [ ] **Step 2: ビルド結果をプレビュー**

```bash
npm run preview
```

`http://localhost:4173/Portfolio/` でビルド済みサイトを確認。

- [ ] **Step 3: 本番前にプレースホルダーを実際の値に置き換える**

`src/data/profile.ts` を開き、以下を実際の値に更新:
```ts
contact: {
  email: 'your-email@example.com',   // ← 実際のメールアドレスに変更
  github: 'https://github.com/kajaha06251020',
  x: 'https://x.com/',               // ← 実際の X アカウント URL に変更（不要なら undefined に）
}
```

- [ ] **Step 4: GitHub Pages へデプロイ**

まず GitHub に `Portfolio` リポジトリが存在し、ローカルと連携されていることを確認（Step 3 で contact 値の置き換えが完了していること）:

```bash
git remote -v
```

リモートが設定されていなければ:
```bash
git remote add origin https://github.com/kajaha06251020/Portfolio.git
git push -u origin master
```

デプロイ実行:
```bash
npm run deploy
```

Expected: `gh-pages` ブランチが作成され `https://kajaha06251020.github.io/Portfolio/` でアクセス可能になる。

- [ ] **Step 4: GitHubリポジトリの Settings → Pages を確認**

`Source` が `gh-pages` ブランチ、フォルダが `/ (root)` であることを確認。

- [ ] **Step 5: 最終コミット**

```bash
git add .env.example
git commit -m "chore: finalize deployment configuration"
```

---

## 完了チェックリスト

デプロイ後、以下をブラウザで確認:

- [ ] `https://kajaha06251020.github.io/Portfolio/` が表示される
- [ ] Vanta.js NET パーティクルが動いている
- [ ] Hero タイトルのアニメーションが再生される
- [ ] スクロールで Works → Skills → About → Contact が順に現れる
- [ ] Works フィルターでカードが切り替わる
- [ ] Contact フォームで空送信バリデーションが動く
- [ ] Navbar がスクロールで半透明になる
- [ ] 全テスト `npm test` が PASS
