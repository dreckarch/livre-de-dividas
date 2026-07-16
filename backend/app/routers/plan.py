from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.engine import debt_engine

router = APIRouter(prefix="/plan", tags=["plan"])


def _split_debts(db: Session) -> tuple[list[debt_engine.RevolvingDebt], list[debt_engine.InstallmentDebt]]:
    records = db.query(models.DebtRecord).filter(models.DebtRecord.active == True).all()  # noqa: E712
    if not records:
        raise HTTPException(status_code=400, detail="Cadastre pelo menos uma dívida antes de simular um plano")

    revolving = []
    installments = []
    for r in records:
        if r.category == "rotativo":
            revolving.append(debt_engine.RevolvingDebt(
                id=r.id, name=r.name, balance=r.balance,
                annual_interest_rate=r.annual_interest_rate, minimum_payment=r.minimum_payment,
            ))
        else:
            remaining = max((r.installments_total or 0) - (r.installments_paid or 0), 0)
            installments.append(debt_engine.InstallmentDebt(
                id=r.id, name=r.name, installment_amount=r.installment_amount,
                installments_remaining=remaining, installments_overdue=r.installments_overdue or 0,
                category=debt_engine.DebtCategory(r.category),
            ))
    return revolving, installments


def _monthly_income(db: Session) -> float:
    incomes = db.query(models.IncomeSource).filter(models.IncomeSource.frequency == "mensal").all()
    return sum(i.amount for i in incomes)


def _result_to_out(result: debt_engine.PayoffResult) -> schemas.PayoffResultOut:
    return schemas.PayoffResultOut(
        strategy=result.strategy.value,
        months_to_payoff=result.months_to_payoff,
        total_interest_paid=result.total_interest_paid,
        total_paid=result.total_paid,
        payoff_achieved=result.payoff_achieved,
        payoff_order=result.payoff_order,
        at_risk_debt_ids=result.at_risk_debt_ids,
        budget_deficit_months=result.budget_deficit_months,
        schedule=[schemas.MonthSnapshotOut(**vars(s)) for s in result.schedule],
    )


@router.post("/simulate", response_model=schemas.PlanComparisonOut)
def simulate_plan(payload: schemas.PlanRequest, db: Session = Depends(get_db)):
    revolving, installments = _split_debts(db)
    monthly_income = _monthly_income(db)

    comparison = debt_engine.compare_strategies(
        revolving, installments, monthly_income, payload.reserved_amount
    )
    return schemas.PlanComparisonOut(
        avalanche=_result_to_out(comparison["avalanche"]),
        snowball=_result_to_out(comparison["snowball"]),
        interest_saved_with_avalanche=comparison["interest_saved_with_avalanche"],
        months_saved_with_avalanche=comparison["months_saved_with_avalanche"],
        monthly_income_used=monthly_income,
        reserved_amount_used=payload.reserved_amount,
    )


@router.post("/simulate-agreement", response_model=schemas.AgreementComparisonOut)
def simulate_agreement_endpoint(payload: schemas.AgreementSimulationRequest, db: Session = Depends(get_db)):
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

    return schemas.AgreementComparisonOut(
        a_vista=_result_to_out(comparison["a_vista"]),
        acordo=_result_to_out(comparison["acordo"]),
        custo_total_acordo=comparison["custo_total_acordo"],
        diferenca_custo_total_plano=comparison["diferenca_custo_total_plano"],
        diferenca_meses_plano=comparison["diferenca_meses_plano"],
        opcao_mais_barata=comparison["opcao_mais_barata"],
        opcao_mais_rapida=comparison["opcao_mais_rapida"],
    )
