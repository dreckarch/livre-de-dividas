import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../api.js'
import ActionPlan from '../components/ActionPlan.jsx'

const springSoft = { type: 'spring', stiffness: 220, damping: 26, mass: 0.9 }
const springBouncy = { type: 'spring', stiffness: 320, damping: 18, mass: 0.7 }

function ResultWarnings({ result }) {
  return (
    <>
      {!result.payoff_achieved && (
        <p className="warning">A quitação total não é alcançada dentro do horizonte simulado. Reveja o valor retido.</p>
      )}
      {result.at_risk_debt_ids.length > 0 && (
        <p className="warning">
          O mínimo sozinho não cobre os juros de: {result.at_risk_debt_ids.join(', ')} — sem o valor extra, o saldo cresceria.
        </p>
      )}
      {result.budget_deficit_months.length > 0 && (
        <p className="warning">
          Em {result.budget_deficit_months.length} mês(es) a renda não cobriu nem as parcelas fixas obrigatórias.
        </p>
      )}
    </>
  )
}

function StrategyCard({ title, result, isWinner, index, revolvingById }) {
  const [showPlan, setShowPlan] = useState(false)

  return (
    <motion.div
      className={`strategy-card ${isWinner ? 'winner' : ''}`}
      initial={{ opacity: 0, y: 28, scale: 0.96 }}
      animate={{ opacity: 1, y: isWinner ? -4 : 0, scale: 1 }}
      transition={{ ...springSoft, delay: index * 0.08 }}
    >
      <h3>{title}</h3>
      <ResultWarnings result={result} />
      <ul>
        <li><span>Tempo até quitar tudo</span><strong>{result.months_to_payoff} meses</strong></li>
        <li><span>Juros pagos (rotativo)</span><strong>R$ {result.total_interest_paid.toFixed(2)}</strong></li>
        <li><span>Total pago (tudo incluso)</span><strong>R$ {result.total_paid.toFixed(2)}</strong></li>
      </ul>

      <button className="action-plan-toggle" onClick={() => setShowPlan(!showPlan)}>
        {showPlan ? 'Ocultar ordem de pagamento' : 'Ver o que pagar primeiro, mês a mês'}
      </button>

      <AnimatePresence>
        {showPlan && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={springSoft}
            style={{ overflow: 'hidden' }}
          >
            <ActionPlan result={result} revolvingById={revolvingById} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function Plan() {
  const [reserved, setReserved] = useState('0')
  const [comparison, setComparison] = useState(null)
  const [aiText, setAiText] = useState(null)
  const [loadingPlan, setLoadingPlan] = useState(false)
  const [loadingAi, setLoadingAi] = useState(false)
  const [error, setError] = useState(null)

  const [revolvingDebts, setRevolvingDebts] = useState([])
  const revolvingById = Object.fromEntries(revolvingDebts.map((d) => [d.id, d]))
  const [agreementForm, setAgreementForm] = useState({ target_debt_id: '', agreement_installment_amount: '', agreement_num_installments: '' })
  const [agreementResult, setAgreementResult] = useState(null)
  const [agreementAiText, setAgreementAiText] = useState(null)
  const [loadingAgreement, setLoadingAgreement] = useState(false)
  const [loadingAgreementAi, setLoadingAgreementAi] = useState(false)
  const [agreementError, setAgreementError] = useState(null)

  useEffect(() => {
    api.listDebts().then(all => {
      const rotativas = all.filter(d => d.category === 'rotativo')
      setRevolvingDebts(rotativas)
      if (rotativas.length > 0) {
        setAgreementForm(f => ({ ...f, target_debt_id: rotativas[0].id }))
      }
    }).catch(() => {})
  }, [])

  const runSimulation = async () => {
    setError(null)
    setAiText(null)
    setLoadingPlan(true)
    try {
      const result = await api.simulatePlan({ reserved_amount: parseFloat(reserved) || 0 })
      setComparison(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingPlan(false)
    }
  }

  const runAiAnalysis = async () => {
    setError(null)
    setLoadingAi(true)
    try {
      const result = await api.analyzeWithAi({ reserved_amount: parseFloat(reserved) || 0 })
      setAiText(result.analysis)
    } catch (e) {
      setError(e.message + ' — verifique se o Ollama está instalado e rodando localmente.')
    } finally {
      setLoadingAi(false)
    }
  }

  const runAgreementSimulation = async () => {
    setAgreementError(null)
    setAgreementAiText(null)
    setLoadingAgreement(true)
    try {
      const result = await api.simulateAgreement({
        target_debt_id: agreementForm.target_debt_id,
        agreement_installment_amount: parseFloat(agreementForm.agreement_installment_amount) || 0,
        agreement_num_installments: parseInt(agreementForm.agreement_num_installments, 10) || 0,
        reserved_amount: parseFloat(reserved) || 0,
      })
      setAgreementResult(result)
    } catch (e) {
      setAgreementError(e.message)
    } finally {
      setLoadingAgreement(false)
    }
  }

  const runAgreementAi = async () => {
    setAgreementError(null)
    setLoadingAgreementAi(true)
    try {
      const result = await api.analyzeAgreementWithAi({
        target_debt_id: agreementForm.target_debt_id,
        agreement_installment_amount: parseFloat(agreementForm.agreement_installment_amount) || 0,
        agreement_num_installments: parseInt(agreementForm.agreement_num_installments, 10) || 0,
        reserved_amount: parseFloat(reserved) || 0,
      })
      setAgreementAiText(result.analysis)
    } catch (e) {
      setAgreementError(e.message + ' — verifique se o Ollama está instalado e rodando localmente.')
    } finally {
      setLoadingAgreementAi(false)
    }
  }

  const avalancheWins = comparison && comparison.avalanche.total_interest_paid <= comparison.snowball.total_interest_paid

  return (
    <section>
      <h2>Plano de Quitação</h2>
      <p>
        Informe quanto você quer <strong>reter</strong> por mês — pra despesas fixas ou reserva — antes de
        destinar o resto às dívidas.
      </p>

      <div className="form-inline">
        <input type="number" step="0.01" value={reserved} onChange={(e) => setReserved(e.target.value)} />
        <motion.button whileTap={{ scale: 0.94 }} onClick={runSimulation} disabled={loadingPlan}>
          {loadingPlan ? 'Calculando...' : 'Simular Plano'}
        </motion.button>
      </div>

      <AnimatePresence>
        {error && (
          <motion.p className="error" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }} transition={springSoft}>
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {comparison && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={springSoft}>
            <p className="summary" style={{ marginBottom: '1rem' }}>
              Renda mensal considerada: <strong>R$ {comparison.monthly_income_used.toFixed(2)}</strong>
              {' · '}Retido: <strong>R$ {comparison.reserved_amount_used.toFixed(2)}</strong>
            </p>

            <div className="strategies">
              <StrategyCard title="Avalanche · menor juros total" result={comparison.avalanche} isWinner={avalancheWins} index={0} revolvingById={revolvingById} />
              <StrategyCard title="Snowball · motivacional" result={comparison.snowball} isWinner={!avalancheWins} index={1} revolvingById={revolvingById} />
            </div>

            <motion.p className="summary" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ ...springSoft, delay: 0.2 }}>
              Usar a estratégia Avalanche economiza <strong>R$ {comparison.interest_saved_with_avalanche.toFixed(2)}</strong> em
              juros e <strong>{comparison.months_saved_with_avalanche}</strong> meses em relação à Snowball.
            </motion.p>

            <motion.button whileTap={{ scale: 0.94 }} onClick={runAiAnalysis} disabled={loadingAi} className="ai-button">
              {loadingAi ? 'Consultando IA local...' : 'Pedir análise da IA (Ollama)'}
            </motion.button>
            <AnimatePresence>
              {loadingAi && (
                <motion.p className="ai-hint" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  Isso pode levar até 1 minuto na primeira consulta, enquanto o modelo carrega na memória.
                </motion.p>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {aiText && (
                <motion.div className="ai-analysis" initial={{ opacity: 0, y: 20, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.98 }} transition={springBouncy}>
                  <h3>Análise da IA</h3>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{aiText}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      {revolvingDebts.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ ...springSoft, delay: 0.1 }} style={{ marginTop: '3rem' }}>
          <h2>Simular Acordo / Parcelamento</h2>
          <p>
            Compare manter uma dívida rotativa como está versus convertê-la num acordo de parcelas fixas
            oferecido pelo credor.
          </p>

          <div className="form-grid">
            <select value={agreementForm.target_debt_id}
              onChange={(e) => setAgreementForm({ ...agreementForm, target_debt_id: e.target.value })}>
              {revolvingDebts.map(d => (
                <option key={d.id} value={d.id}>{d.name} (R$ {d.balance?.toFixed(2)})</option>
              ))}
            </select>
            <input type="number" step="0.01" placeholder="Valor da parcela do acordo (R$)"
              value={agreementForm.agreement_installment_amount}
              onChange={(e) => setAgreementForm({ ...agreementForm, agreement_installment_amount: e.target.value })} />
            <input type="number" placeholder="Número de parcelas"
              value={agreementForm.agreement_num_installments}
              onChange={(e) => setAgreementForm({ ...agreementForm, agreement_num_installments: e.target.value })} />
            <motion.button whileTap={{ scale: 0.94 }} onClick={runAgreementSimulation} disabled={loadingAgreement}>
              {loadingAgreement ? 'Comparando...' : 'Comparar Acordo vs. À Vista'}
            </motion.button>
          </div>

          <AnimatePresence>
            {agreementError && (
              <motion.p className="error" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }} transition={springSoft}>
                {agreementError}
              </motion.p>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {agreementResult && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={springSoft}>
                <div className="strategies">
                  <StrategyCard title="À Vista · mantém rotativo" result={agreementResult.a_vista}
                    isWinner={agreementResult.opcao_mais_barata === 'a_vista'} index={0} revolvingById={revolvingById} />
                  <StrategyCard title="Acordo · parcela fixa" result={agreementResult.acordo}
                    isWinner={agreementResult.opcao_mais_barata === 'acordo'} index={1} revolvingById={revolvingById} />
                </div>
                <p className="summary">
                  Custo total do acordo se seguido até o fim: <strong>R$ {agreementResult.custo_total_acordo.toFixed(2)}</strong>.
                  A opção mais barata é <strong>{agreementResult.opcao_mais_barata === 'acordo' ? 'o Acordo' : 'pagar à vista'}</strong> e
                  a mais rápida é <strong>{agreementResult.opcao_mais_rapida === 'acordo' ? 'o Acordo' : 'pagar à vista'}</strong>.
                </p>

                <motion.button whileTap={{ scale: 0.94 }} onClick={runAgreementAi} disabled={loadingAgreementAi} className="ai-button">
                  {loadingAgreementAi ? 'Consultando IA local...' : 'Pedir análise da IA sobre esse acordo'}
                </motion.button>
                <AnimatePresence>
                  {loadingAgreementAi && (
                    <motion.p className="ai-hint" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                      Isso pode levar até 1 minuto na primeira consulta, enquanto o modelo carrega na memória.
                    </motion.p>
                  )}
                </AnimatePresence>

                <AnimatePresence>
                  {agreementAiText && (
                    <motion.div className="ai-analysis" initial={{ opacity: 0, y: 20, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.98 }} transition={springBouncy}>
                      <h3>Análise da IA</h3>
                      <p style={{ whiteSpace: 'pre-wrap' }}>{agreementAiText}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </section>
  )
}
