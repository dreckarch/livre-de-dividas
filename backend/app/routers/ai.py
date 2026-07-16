from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.engine import debt_engine
from app.ai import ollama_client
from app.routers.plan import _split_debts, _monthly_income

router = APIRouter(prefix="/ai", tags=["ai"])


def _format_income_summary(monthly_income: float, reserved_amount: float) -> str:
    return (
        f"Renda mensal total: R$ {monthly_income:.2f}\n"
        f"Valor retido pelo usuário (não usar em dívidas): R$ {reserved_amount:.2f}\n"
        f"Disponível para obrigações + dívidas: R$ {monthly_income - reserved_amount:.2f}"
    )


def _format_result(label: str, r: debt_engine.PayoffResult) -> str:
    lines = [
        f"[{label}] quitação total em {r.months_to_payoff} meses "
        f"(concluída: {'sim' if r.payoff_achieved else 'NÃO — valores insuficientes'})",
        f"  juros pagos em dívidas rotativas: R$ {r.total_interest_paid:.2f}",
        f"  total pago (rotativo + parcelas fixas + atrasos): R$ {r.total_paid:.2f}",
        f"  ordem de quitação: {', '.join(r.payoff_order) if r.payoff_order else 'nenhuma dívida quitada ainda'}",
    ]
    if r.at_risk_debt_ids:
        lines.append(f"  ATENÇÃO — dívida(s) cujo mínimo sozinho não cobre os juros: {', '.join(r.at_risk_debt_ids)}")
    if r.budget_deficit_months:
        lines.append(
            f"  ATENÇÃO — em {len(r.budget_deficit_months)} mês(es) a renda não cobriu nem as obrigações fixas"
        )
    return "\n".join(lines)


@router.post("/analyze", response_model=schemas.AiAnalysisResponse)
def analyze_plan(payload: schemas.AiAnalysisRequest, db: Session = Depends(get_db)):
    revolving, installments = _split_debts(db)
    monthly_income = _monthly_income(db)
    comparison = debt_engine.compare_strategies(revolving, installments, monthly_income, payload.reserved_amount)

    income_summary = _format_income_summary(monthly_income, payload.reserved_amount)
    plan_summary = "\n\n".join([
        _format_result("AVALANCHE", comparison["avalanche"]),
        _format_result("SNOWBALL", comparison["snowball"]),
        f"Economia de juros usando avalanche em vez de snowball: R$ {comparison['interest_saved_with_avalanche']:.2f}",
    ])
    context = ollama_client.build_context(income_summary, plan_summary)

    try:
        analysis = ollama_client.generate_analysis(context, model=payload.model)
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return schemas.AiAnalysisResponse(analysis=analysis, model_used=payload.model or ollama_client.DEFAULT_MODEL)


@router.post("/analyze-agreement", response_model=schemas.AiAgreementAnalysisResponse)
def analyze_agreement(payload: schemas.AiAgreementAnalysisRequest, db: Session = Depends(get_db)):
    revolving, installments = _split_debts(db)
    monthly_income = _monthly_income(db)
    strategy = debt_engine.Strategy(payload.strategy or "avalanche")

    try:
        comparison = debt_engine.compare_agreement_vs_cash(
            revolving_debts=revolving,
            installment_debts=installments,
            target_debt_id=payload.target_debt_id,
            agreement_installment_amount=payload.agreement_installment_amount,
            agreement_num_installments=payload.agreement_num_installments,
            monthly_income=monthly_income,
            reserved_amount=payload.reserved_amount,
            strategy=strategy,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    income_summary = _format_income_summary(monthly_income, payload.reserved_amount)
    plan_summary = "\n\n".join([
        _format_result("À VISTA (mantendo rotativo)", comparison["a_vista"]),
        _format_result("ACORDO (convertendo em parcela fixa)", comparison["acordo"]),
        f"Custo total do acordo se seguido até o fim: R$ {comparison['custo_total_acordo']:.2f}",
        f"Diferença de custo total do plano inteiro (acordo - à vista): R$ {comparison['diferenca_custo_total_plano']:.2f}",
        f"Diferença de meses até quitar tudo (acordo - à vista): {comparison['diferenca_meses_plano']}",
        f"Opção mais barata (calculado, não é opinião): {comparison['opcao_mais_barata']}",
        f"Opção mais rápida (calculado, não é opinião): {comparison['opcao_mais_rapida']}",
    ])
    context = ollama_client.build_context(
        income_summary,
        plan_summary + "\n\nExplique ao usuário qual opção faz mais sentido pro caso dele, considerando "
        "não só o número frio mas também o alívio no fluxo de caixa mensal e o risco de cada cenário.",
    )

    try:
        analysis = ollama_client.generate_analysis(context, model=payload.model)
    except ollama_client.OllamaUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return schemas.AiAgreementAnalysisResponse(analysis=analysis, model_used=payload.model or ollama_client.DEFAULT_MODEL)
