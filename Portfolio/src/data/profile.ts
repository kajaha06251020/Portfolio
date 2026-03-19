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
    email: 'shotacoding@gmail.com',
    github: 'https://github.com/kajaha06251020',
    x: 'https://x.com/Shota__Okabe',
  },
}
