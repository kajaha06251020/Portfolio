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
