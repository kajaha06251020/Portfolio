export type Project = {
  id: string
  title: string
  description: { ja: string; en: string }
  tags: string[]
  category: 'data' | 'backend' | 'frontend'
  github?: string
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
  },
]
