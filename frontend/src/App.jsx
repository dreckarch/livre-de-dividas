import { Routes, Route, NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import Income from './pages/Income.jsx'
import Debts from './pages/Debts.jsx'
import Plan from './pages/Plan.jsx'

export default function App() {
  return (
    <div className="app">
      <motion.header
        className="topbar"
        initial={{ y: -24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 28, mass: 0.9 }}
      >
        <h1>Livre de Dívidas</h1>
        <nav>
          <NavLink to="/" end>Rendas</NavLink>
          <NavLink to="/dividas">Dívidas</NavLink>
          <NavLink to="/plano">Plano de Quitação</NavLink>
        </nav>
      </motion.header>
      <main>
        <Routes>
          <Route path="/" element={<Income />} />
          <Route path="/dividas" element={<Debts />} />
          <Route path="/plano" element={<Plan />} />
        </Routes>
      </main>
    </div>
  )
}
