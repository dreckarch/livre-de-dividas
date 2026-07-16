import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '../api.js'

const TYPES = [
  { value: 'salario', label: 'Salário' },
  { value: 'vt', label: 'Vale Transporte' },
  { value: 'va', label: 'Vale Alimentação' },
  { value: 'comissao', label: 'Comissão' },
  { value: 'outro', label: 'Outro' },
]

const springSoft = { type: 'spring', stiffness: 220, damping: 26, mass: 0.9 }

export default function Income() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState({ name: '', type: 'salario', amount: '', frequency: 'mensal' })
  const [error, setError] = useState(null)

  const load = () => api.listIncome().then(setItems).catch((e) => setError(e.message))

  useEffect(() => { load() }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await api.createIncome({ ...form, amount: parseFloat(form.amount) })
      setForm({ name: '', type: 'salario', amount: '', frequency: 'mensal' })
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const total = items.filter(i => i.frequency === 'mensal').reduce((s, i) => s + i.amount, 0)

  return (
    <motion.section initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={springSoft}>
      <h2>Fontes de Renda</h2>
      <p>Cadastre tudo que entra por mês: salário, vale transporte, vale alimentação, comissões.</p>
      {error && <p className="error">{error} — verifique se o backend está rodando.</p>}

      <form onSubmit={handleSubmit} className="form-inline">
        <input placeholder="Nome (ex: Salário CLT)" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <input type="number" step="0.01" placeholder="Valor (R$)" value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
        <select value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })}>
          <option value="mensal">Mensal</option>
          <option value="quinzenal">Quinzenal</option>
          <option value="variavel">Variável</option>
        </select>
        <motion.button whileTap={{ scale: 0.94 }} type="submit">Adicionar</motion.button>
      </form>

      <table>
        <thead>
          <tr><th>Nome</th><th>Tipo</th><th>Valor</th><th>Frequência</th><th></th></tr>
        </thead>
        <tbody>
          {items.map(i => (
            <motion.tr key={i.id} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={springSoft}>
              <td>{i.name}</td>
              <td>{TYPES.find(t => t.value === i.type)?.label || i.type}</td>
              <td>R$ {i.amount.toFixed(2)}</td>
              <td>{i.frequency}</td>
              <td><button onClick={() => api.deleteIncome(i.id).then(load)}>Remover</button></td>
            </motion.tr>
          ))}
        </tbody>
      </table>
      <p className="total">Total mensal: <strong>R$ {total.toFixed(2)}</strong></p>
    </motion.section>
  )
}
