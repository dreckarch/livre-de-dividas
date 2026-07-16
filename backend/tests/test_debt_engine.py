import pytest
from app.engine.debt_engine import (
    RevolvingDebt, InstallmentDebt, DebtCategory, Strategy,
    simulate_cash_flow_payoff, compare_strategies, compare_agreement_vs_cash,
    simulate_agreement, identify_at_risk_debts,
)


def test_no_debts_returns_zero():
    result = simulate_cash_flow_payoff([], [], monthly_income=3000, reserved_amount=0)
    assert result.months_to_payoff == 0


def test_revolving_only_is_paid_off():
    debt = RevolvingDebt(id="d1", name="Cartão", balance=1000, annual_interest_rate=24, minimum_payment=100)
    result = simulate_cash_flow_payoff([debt], [], monthly_income=3000, reserved_amount=0, strategy=Strategy.AVALANCHE)
    assert result.payoff_achieved is True
    assert result.payoff_order == ["d1"]


def test_installment_debt_is_deducted_automatically_and_not_in_avalanche_queue():
    installment = InstallmentDebt(
        id="financ", name="Financiamento", installment_amount=500,
        installments_remaining=6, installments_overdue=0,
    )
    result = simulate_cash_flow_payoff([], [installment], monthly_income=3000, reserved_amount=0, strategy=Strategy.AVALANCHE)
    assert result.months_to_payoff == 6
    assert result.total_paid == pytest.approx(3000.0)
    assert result.total_interest_paid == 0.0  # parcelado fixo não gera "juros" no sentido do motor
    assert "financ" in result.payoff_order


def test_overdue_installments_get_maximum_priority():
    installment = InstallmentDebt(
        id="financ", name="Financiamento", installment_amount=300,
        installments_remaining=5, installments_overdue=2,  # atraso de 600
    )
    revolving = RevolvingDebt(id="cartao", name="Cartão", balance=2000, annual_interest_rate=100, minimum_payment=100)
    result = simulate_cash_flow_payoff(
        [revolving], [installment], monthly_income=3000, reserved_amount=0, strategy=Strategy.AVALANCHE
    )
    # o atraso some do rastro antes da dívida rotativa terminar
    atraso_month = next(s.month for s in result.schedule if s.kind == "atraso" and s.balance_end <= 0.01)
    cartao_final_month = max(s.month for s in result.schedule if s.debt_id == "cartao" and s.balance_end <= 0.01)
    assert atraso_month <= cartao_final_month


def test_reserved_amount_reduces_available_for_debt_payoff():
    debt = RevolvingDebt(id="d1", name="Cartão", balance=3000, annual_interest_rate=60, minimum_payment=100)
    result_no_reserve = simulate_cash_flow_payoff([debt], [], monthly_income=2000, reserved_amount=0, strategy=Strategy.AVALANCHE)
    result_with_reserve = simulate_cash_flow_payoff([debt], [], monthly_income=2000, reserved_amount=800, strategy=Strategy.AVALANCHE)
    # reter dinheiro deve atrasar (ou no mínimo não acelerar) a quitação
    assert result_with_reserve.months_to_payoff >= result_no_reserve.months_to_payoff


def test_negative_reserved_amount_raises_error():
    debt = RevolvingDebt(id="d1", name="Cartão", balance=1000, annual_interest_rate=24, minimum_payment=100)
    with pytest.raises(ValueError):
        simulate_cash_flow_payoff([debt], [], monthly_income=3000, reserved_amount=-100)


def test_budget_deficit_is_flagged_when_income_does_not_cover_fixed_installments():
    installment = InstallmentDebt(id="financ", name="Financiamento", installment_amount=2000, installments_remaining=3)
    result = simulate_cash_flow_payoff([], [installment], monthly_income=1500, reserved_amount=0, strategy=Strategy.AVALANCHE)
    assert len(result.budget_deficit_months) > 0


def test_simulate_agreement_creates_installment_debt():
    revolving = RevolvingDebt(id="cartao", name="Cartão", balance=4000, annual_interest_rate=140, minimum_payment=200)
    agreement = simulate_agreement(revolving, installment_amount=450, num_installments=12)
    assert agreement.category == DebtCategory.ACORDO_ATIVO
    assert agreement.installments_remaining == 12
    assert agreement.installment_amount == 450


def test_compare_agreement_vs_cash_flags_cheaper_option():
    cartao = RevolvingDebt(id="cartao", name="Cartão", balance=4000, annual_interest_rate=140, minimum_payment=200)
    comparison = compare_agreement_vs_cash(
        revolving_debts=[cartao],
        installment_debts=[],
        target_debt_id="cartao",
        agreement_installment_amount=450,
        agreement_num_installments=12,
        monthly_income=4000,
        reserved_amount=400,
    )
    assert comparison["opcao_mais_barata"] in ("acordo", "a_vista")
    assert comparison["custo_total_acordo"] == 5400.0
    # com renda alta e saldo relativamente baixo, pagar à vista deve ser mais barato
    assert comparison["opcao_mais_barata"] == "a_vista"


def test_identifies_interest_trap_debt():
    trap = RevolvingDebt(id="trap", name="Armadilha", balance=10000, annual_interest_rate=150, minimum_payment=50)
    healthy = RevolvingDebt(id="ok", name="Saudável", balance=1000, annual_interest_rate=10, minimum_payment=100)
    at_risk = identify_at_risk_debts([trap, healthy])
    assert "trap" in at_risk and "ok" not in at_risk
