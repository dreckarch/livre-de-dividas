import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../api.js'

const CATEGORIES = [
  { value: 'rotativo', label: 'Rotativo (cartão, cheque especial)' },
  { value: 'parcelado_fixo', label: 'Parcelado Fixo (financiamento, empréstimo)' },
]

const TIPOS_ROTATIVO = [
  { value: 'cartao', label: 'Cartão de Crédito' },
  { value: 'cheque_especial', label: 'Cheque Especial' },
  { value: 'outro', label: 'Outro' },
]

const TIPOS_PARCELADO = [
  { value: 'emprestimo', label: 'Empréstimo Pessoal' },
  { value: 'financiamento', label: 'Financiamento' },
  { value: 'consignado', label: 'Consignado' },
  { value: 'outro', label: 'Outro' },
]

const springSoft = { type: 'spring', stiffness: 220, damping: 26, mass: 0.9 }

const emptyForm = {
  name: '', category: 'rotativo', debt_type: 'cartao',
  balance: '', annual_interest_rate: '', minimum_payment: '',
  installment_amount: '', installments_total: '', installments_paid: '0', installments_overdue: '0',
  due_day: '',
}

function categoryLabel(cat) {
  if (cat === 'rotativo') return 'Rotativo'
  if (cat === 'parcelado_fixo') return 'Parcelado Fixo'
  if (cat === 'acordo_ativo') return 'Acordo Ativo'
  return cat
}

export default function Debts() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState(null)

  const load = () => api.listDebts().then(setItems).catch((e) => setError(e.message))

  useEffect(() => { load() }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      const payload = { name: form.name, category: form.category, debt_type: form.debt_type, due_day: form.due_day || null }
      if (form.category === 'rotativo') {
        payload.balance = parseFloat(form.balance)
        payload.annual_interest_rate = parseFloat(form.annual_interest_rate)
        payload.minimum_payment = parseFloat(form.minimum_payment)
      } else {
        payload.installment_amount = parseFloat(form.installment_amount)
        payload.installments_total = parseInt(form.installments_total, 10)
        payload.installments_paid = parseInt(form.installments_paid || '0', 10)
        payload.installments_overdue = parseInt(form.installments_overdue || '0', 10)
      }
      await api.createDebt(payload)
      setForm({ ...emptyForm, category: form.category, debt_type: form.category === 'rotativo' ? 'cartao' : 'emprestimo' })
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const tiposDisponiveis = form.category === 'rotativo' ? TIPOS_ROTATIVO : TIPOS_PARCELADO

  const totalRotativo = items.filter(d => d.category === 'rotativo').reduce((s, d) => s + (d.balance || 0), 0)
  const totalParcelado = items
    .filter(d => d.category !== 'rotativo')
    .reduce((s, d) => s + (d.installment_amount || 0) * Math.max((d.installments_total || 0) - (d.installments_paid || 0), 0), 0)

  return (
    <motion.section initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={springSoft}>
      <h2>Minhas Dívidas</h2>
      <p>
        Dívidas <strong>rotativas</strong> (cartão, cheque especial) entram na fila do Avalanche/Snowball.
        Dívidas <strong>parceladas</strong> (financiamento, empréstimo) têm parcela fixa deduzida
        automaticamente do seu fluxo de caixa todo mês.
      </p>
      {error && <p className="error">{error} — verifique se o backend está rodando.</p>}

      <form onSubmit={handleSubmit} className="form-grid">
        <input placeholder="Nome (ex: Cartão Nubank)" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} required />

        <select value={form.category} onChange={(e) => {
          const category = e.target.value
          setForm({ ...form, category, debt_type: category === 'rotativo' ? 'cartao' : 'emprestimo' })
        }}>
          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>

        <select value={form.debt_type} onChange={(e) => setForm({ ...form, debt_type: e.target.value })}>
          {tiposDisponiveis.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>

        {form.category === 'rotativo' ? (
          <>
            <label className="field-label">
              Saldo devedor (R$)
              <input type="number" step="0.01" value={form.balance}
                onChange={(e) => setForm({ ...form, balance: e.target.value })} required />
            </label>
            <label className="field-label">
              Juros % ao ano
              <input type="number" step="0.01" value={form.annual_interest_rate}
                onChange={(e) => setForm({ ...form, annual_interest_rate: e.target.value })} required />
            </label>
            <label className="field-label">
              Pagamento mínimo (R$)
              <input type="number" step="0.01" value={form.minimum_payment}
                onChange={(e) => setForm({ ...form, minimum_payment: e.target.value })} required />
            </label>
          </>
        ) : (
          <>
            <label className="field-label">
              Valor da parcela (R$)
              <input type="number" step="0.01" value={form.installment_amount}
                onChange={(e) => setForm({ ...form, installment_amount: e.target.value })} required />
            </label>
            <label className="field-label">
              Total de parcelas
              <input type="number" value={form.installments_total}
                onChange={(e) => setForm({ ...form, installments_total: e.target.value })} required />
            </label>
            <label className="field-label">
              Parcelas já pagas
              <input type="number" value={form.installments_paid}
                onChange={(e) => setForm({ ...form, installments_paid: e.target.value })} />
            </label>
            <label className="field-label">
              Parcelas em atraso
              <input type="number" value={form.installments_overdue}
                onChange={(e) => setForm({ ...form, installments_overdue: e.target.value })} />
            </label>
          </>
        )}

        <label className="field-label">
          Dia de vencimento
          <input placeholder="ex: 10" value={form.due_day}
            onChange={(e) => setForm({ ...form, due_day: e.target.value })} />
        </label>

        <motion.button whileTap={{ scale: 0.94 }} type="submit">Adicionar Dívida</motion.button>
      </form>

      <table>
        <thead>
          <tr><th>Nome</th><th>Categoria</th><th>Situação</th><th></th></tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {items.map(d => (
              <motion.tr key={d.id}
                initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 12 }}
                transition={springSoft}>
                <td>{d.name}</td>
                <td>{categoryLabel(d.category)}</td>
                <td>
                  {d.category === 'rotativo'
                    ? `R$ ${d.balance?.toFixed(2)} · ${d.annual_interest_rate}% a.a. · mín. R$ ${d.minimum_payment?.toFixed(2)}`
                    : `${Math.max((d.installments_total || 0) - (d.installments_paid || 0), 0)}x de R$ ${d.installment_amount?.toFixed(2)}`
                      + (d.installments_overdue ? ` · ${d.installments_overdue} em atraso` : '')
                  }
                </td>
                <td><button onClick={() => api.deleteDebt(d.id).then(load)}>Remover</button></td>
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>
      <p className="total">
        Saldo rotativo: <strong>R$ {totalRotativo.toFixed(2)}</strong>
        {' · '}
        Restante parcelado: <strong>R$ {totalParcelado.toFixed(2)}</strong>
      </p>
    </motion.section>
  )
}
