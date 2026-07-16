import { motion } from 'framer-motion'

const KIND_LABELS = {
  rotativo: 'Rotativo',
  parcelado_fixo: 'Parcelado Fixo',
  acordo_ativo: 'Acordo Ativo',
  atraso: 'Atraso urgente',
}

const springSoft = { type: 'spring', stiffness: 220, damping: 26, mass: 0.9 }

/**
 * Agrupa o cronograma mês a mês (já calculado pelo backend) por dívida e
 * deriva, pra cada uma, quando ela deve receber o dinheiro extra e quando
 * é projetada pra ser quitada — ou seja, transforma números crus em ação.
 */
function buildActionPlan(result, revolvingById) {
  const groups = {}
  for (const s of result.schedule) {
    const key = s.kind === 'atraso' ? `${s.debt_id}-atraso` : s.debt_id
    if (!groups[key]) {
      groups[key] = { key, debt_id: s.debt_id, kind: s.kind, name: s.debt_name, entries: [] }
    }
    groups[key].entries.push(s)
  }

  const orderIndex = {}
  result.payoff_order.forEach((id, idx) => { orderIndex[id] = idx })

  const items = Object.values(groups).map((g) => {
    const entries = g.entries.sort((a, b) => a.month - b.month)
    const first = entries[0]
    const last = entries[entries.length - 1]
    const payoffMonth = last.balance_end <= 0.01 ? last.month : null
    const debtInfo = revolvingById[g.debt_id]

    let extraStartsMonth = null
    let currentAmount = first.payment_made
    if (g.kind === 'rotativo' && debtInfo) {
      const withExtra = entries.find((e) => e.payment_made > debtInfo.minimum_payment + 0.01)
      extraStartsMonth = withExtra ? withExtra.month : null
      currentAmount = debtInfo.minimum_payment
    }

    return { ...g, entries, payoffMonth, currentAmount, extraStartsMonth, minimum: debtInfo?.minimum_payment }
  })

  items.sort((a, b) => {
    const ao = orderIndex[a.key] ?? Infinity
    const bo = orderIndex[b.key] ?? Infinity
    return ao - bo
  })

  return items
}

function describeItem(item) {
  if (item.kind === 'atraso') {
    return item.payoffMonth
      ? `Prioridade máxima: quite o atraso o quanto antes. Projeção: quitado no mês ${item.payoffMonth}.`
      : 'Prioridade máxima: quite o atraso o quanto antes.'
  }
  if (item.kind === 'parcelado_fixo' || item.kind === 'acordo_ativo') {
    return (
      `Parcela fixa de R$ ${item.currentAmount.toFixed(2)}/mês, deduzida automaticamente da sua renda.` +
      (item.payoffMonth ? ` Última parcela projetada pro mês ${item.payoffMonth}.` : '')
    )
  }
  // rotativo
  if (item.extraStartsMonth && item.extraStartsMonth > 1) {
    return (
      `Pague só o mínimo (R$ ${item.minimum?.toFixed(2)}) até o mês ${item.extraStartsMonth - 1}. ` +
      `A partir do mês ${item.extraStartsMonth}, direcione o dinheiro extra pra cá.` +
      (item.payoffMonth ? ` Quitação projetada pro mês ${item.payoffMonth}.` : '')
    )
  }
  return (
    `Direcione o extra pra cá desde já (mínimo de R$ ${item.minimum?.toFixed(2)} + o que sobrar).` +
    (item.payoffMonth ? ` Quitação projetada pro mês ${item.payoffMonth}.` : '')
  )
}

export default function ActionPlan({ result, revolvingById }) {
  const items = buildActionPlan(result, revolvingById || {})

  if (items.length === 0) return null

  return (
    <div className="action-plan">
      {items.map((item, idx) => (
        <motion.div
          key={item.key}
          className="action-plan-item"
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ ...springSoft, delay: idx * 0.05 }}
        >
          <span className="action-plan-rank">{idx + 1}º</span>
          <div className="action-plan-body">
            <div className="action-plan-title">
              <strong>{item.name}</strong>
              <span className="action-plan-badge">{KIND_LABELS[item.kind] || item.kind}</span>
            </div>
            <p>{describeItem(item)}</p>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
