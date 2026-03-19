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
