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
