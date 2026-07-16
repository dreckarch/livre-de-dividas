from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


class DebtCategory(str, Enum):
    ROTATIVO = "rotativo"
    PARCELADO_FIXO = "parcelado_fixo"
    ACORDO_ATIVO = "acordo_ativo"


class Strategy(str, Enum):
    AVALANCHE = "avalanche"
    SNOWBALL = "snowball"


@dataclass
class RevolvingDebt:
    """Dívida ROTATIVO: cartão de crédito, cheque especial."""
    id: str
    name: str
    balance: float
    annual_interest_rate: float
    minimum_payment: float

    def monthly_rate(self) -> float:
        return (self.annual_interest_rate / 100) / 12


@dataclass
class InstallmentDebt:
    """Dívida PARCELADO_FIXO ou ACORDO_ATIVO: parcela fixa, já negociada/contratada."""
    id: str
    name: str
    installment_amount: float
    installments_remaining: int            # parcelas futuras ainda não vencidas
    installments_overdue: int = 0          # parcelas já vencidas e não pagas
    category: DebtCategory = DebtCategory.PARCELADO_FIXO

    @property
    def overdue_balance(self) -> float:
        return round(self.installment_amount * self.installments_overdue, 2)


@dataclass
class MonthSnapshot:
    month: int
    debt_id: str
    debt_name: str
    kind: str  # "rotativo" | "parcelado_fixo" | "acordo_ativo" | "atraso"
    balance_start: float
    interest_charged: float
    payment_made: float
    balance_end: float


@dataclass
class PayoffResult:
    strategy: Strategy
    months_to_payoff: int
    total_interest_paid: float             # apenas juros das dívidas rotativas
    total_paid: float                      # tudo: rotativo + parcelas fixas + atraso
    payoff_achieved: bool = True
    payoff_order: List[str] = field(default_factory=list)
    schedule: List[MonthSnapshot] = field(default_factory=list)
    at_risk_debt_ids: List[str] = field(default_factory=list)
    budget_deficit_months: List[int] = field(default_factory=list)  # meses em que renda não cobriu nem os fixos


def identify_at_risk_debts(revolving_debts: List[RevolvingDebt]) -> List[str]:
    """Dívidas rotativas cujo mínimo nem cobre os juros do mês (armadilha de juros)."""
    at_risk = []
    for d in revolving_debts:
        monthly_interest = d.balance * d.monthly_rate()
        if d.minimum_payment < monthly_interest:
            at_risk.append(d.id)
    return at_risk


def _order_targets(revolving_debts: List[RevolvingDebt], strategy: Strategy) -> List[str]:
    if strategy == Strategy.AVALANCHE:
        ordered = sorted(revolving_debts, key=lambda d: d.annual_interest_rate, reverse=True)
    else:
        ordered = sorted(revolving_debts, key=lambda d: d.balance)
    return [d.id for d in ordered]


def simulate_cash_flow_payoff(
    revolving_debts: List[RevolvingDebt],
    installment_debts: List[InstallmentDebt],
    monthly_income: float,
    reserved_amount: float = 0.0,
    strategy: Strategy = Strategy.AVALANCHE,
    max_months: int = 480,
) -> PayoffResult:
    """
    Simula mês a mês o fluxo de caixa completo: renda menos o valor retido
    pelo usuário, menos as parcelas fixas obrigatórias, com o restante indo
    primeiro para atrasos e depois para a estratégia Avalanche/Snowball.
    """
    if reserved_amount < 0:
        raise ValueError("reserved_amount não pode ser negativo")
    if monthly_income < 0:
        raise ValueError("monthly_income não pode ser negativo")

    if not revolving_debts and not installment_debts:
        return PayoffResult(strategy=strategy, months_to_payoff=0, total_interest_paid=0.0, total_paid=0.0)

    rev_balances = {d.id: d.balance for d in revolving_debts}
    rev_by_id = {d.id: d for d in revolving_debts}
    target_order = _order_targets(revolving_debts, strategy)

    inst_remaining = {d.id: d.installments_remaining for d in installment_debts}
    inst_overdue_balance = {d.id: d.overdue_balance for d in installment_debts}
    inst_by_id = {d.id: d for d in installment_debts}

    at_risk = identify_at_risk_debts(revolving_debts)

    schedule: List[MonthSnapshot] = []
    payoff_order: List[str] = []
    budget_deficit_months: List[int] = []
    total_interest_paid = 0.0
    total_paid = 0.0
    month = 0

    def everything_done() -> bool:
        rev_done = all(v <= 0.01 for v in rev_balances.values())
        inst_done = all(v <= 0 for v in inst_remaining.values())
        overdue_done = all(v <= 0.01 for v in inst_overdue_balance.values())
        return rev_done and inst_done and overdue_done

    while not everything_done() and month < max_months:
        month += 1

        # 1. Parcelas fixas regulares — obrigatórias, saem da renda antes de tudo
        fixed_due = sum(
            inst_by_id[d_id].installment_amount
            for d_id, remaining in inst_remaining.items() if remaining > 0
        )

        available = monthly_income - reserved_amount - fixed_due
        if available < 0:
            budget_deficit_months.append(month)
            available = 0.0

        for d_id, remaining in list(inst_remaining.items()):
            if remaining <= 0:
                continue
            d = inst_by_id[d_id]
            schedule.append(MonthSnapshot(
                month=month, debt_id=d_id, debt_name=d.name, kind=d.category.value,
                balance_start=round(remaining * d.installment_amount, 2),
                interest_charged=0.0,
                payment_made=d.installment_amount,
                balance_end=round((remaining - 1) * d.installment_amount, 2),
            ))
            inst_remaining[d_id] = remaining - 1
            total_paid += d.installment_amount
            if inst_remaining[d_id] == 0 and d_id not in payoff_order:
                payoff_order.append(d_id)

        # 2. Prioridade máxima: quitar atraso de parcelas vencidas
        overdue_ids_sorted = sorted(
            (d_id for d_id, bal in inst_overdue_balance.items() if bal > 0.01),
            key=lambda d_id: -inst_overdue_balance[d_id],
        )
        for d_id in overdue_ids_sorted:
            if available <= 0:
                break
            bal = inst_overdue_balance[d_id]
            payment = min(bal, available)
            inst_overdue_balance[d_id] = round(bal - payment, 2)
            available -= payment
            total_paid += payment
            d = inst_by_id[d_id]
            schedule.append(MonthSnapshot(
                month=month, debt_id=d_id, debt_name=f"{d.name} (atraso)", kind="atraso",
                balance_start=bal, interest_charged=0.0,
                payment_made=round(payment, 2), balance_end=inst_overdue_balance[d_id],
            ))
            if inst_overdue_balance[d_id] <= 0.01:
                payoff_order.append(f"{d_id}-atraso")

        # 3. Avalanche/Snowball nas dívidas rotativas com o que sobrar
        freed_up = sum(
            rev_by_id[d_id].minimum_payment for d_id in rev_balances if rev_balances[d_id] <= 0.01
        )
        available_extra = available + freed_up
        current_target = next((d_id for d_id in target_order if rev_balances[d_id] > 0.01), None)

        for d_id, debt in rev_by_id.items():
            start_balance = rev_balances[d_id]
            if start_balance <= 0.01:
                continue

            interest = start_balance * debt.monthly_rate()
            balance_with_interest = start_balance + interest

            payment = min(debt.minimum_payment, balance_with_interest)
            if d_id == current_target:
                payment = min(balance_with_interest, payment + available_extra)

            end_balance = round(balance_with_interest - payment, 2)
            if end_balance < 0:
                payment += end_balance
                end_balance = 0.0

            rev_balances[d_id] = end_balance
            total_interest_paid += interest
            total_paid += payment

            schedule.append(MonthSnapshot(
                month=month, debt_id=d_id, debt_name=debt.name, kind="rotativo",
                balance_start=round(start_balance, 2), interest_charged=round(interest, 2),
                payment_made=round(payment, 2), balance_end=end_balance,
            ))

            if end_balance <= 0.01 and d_id not in payoff_order:
                payoff_order.append(d_id)

    return PayoffResult(
        strategy=strategy,
        months_to_payoff=month,
        total_interest_paid=round(total_interest_paid, 2),
        total_paid=round(total_paid, 2),
        payoff_achieved=everything_done(),
        payoff_order=payoff_order,
        schedule=schedule,
        at_risk_debt_ids=at_risk,
        budget_deficit_months=budget_deficit_months,
    )


def compare_strategies(
    revolving_debts: List[RevolvingDebt],
    installment_debts: List[InstallmentDebt],
    monthly_income: float,
    reserved_amount: float = 0.0,
) -> dict:
    avalanche = simulate_cash_flow_payoff(
        revolving_debts, installment_debts, monthly_income, reserved_amount, Strategy.AVALANCHE
    )
    snowball = simulate_cash_flow_payoff(
        revolving_debts, installment_debts, monthly_income, reserved_amount, Strategy.SNOWBALL
    )
    return {
        "avalanche": avalanche,
        "snowball": snowball,
        "interest_saved_with_avalanche": round(snowball.total_interest_paid - avalanche.total_interest_paid, 2),
        "months_saved_with_avalanche": snowball.months_to_payoff - avalanche.months_to_payoff,
    }


def simulate_agreement(
    revolving_debt: RevolvingDebt, installment_amount: float, num_installments: int
) -> InstallmentDebt:
    """Converte uma dívida ROTATIVO num acordo de parcelamento (ACORDO_ATIVO)."""
    if installment_amount <= 0 or num_installments <= 0:
        raise ValueError("installment_amount e num_installments devem ser positivos")
    return InstallmentDebt(
        id=f"{revolving_debt.id}-acordo",
        name=f"Acordo: {revolving_debt.name}",
        installment_amount=installment_amount,
        installments_remaining=num_installments,
        installments_overdue=0,
        category=DebtCategory.ACORDO_ATIVO,
    )


def compare_agreement_vs_cash(
    revolving_debts: List[RevolvingDebt],
    installment_debts: List[InstallmentDebt],
    target_debt_id: str,
    agreement_installment_amount: float,
    agreement_num_installments: int,
    monthly_income: float,
    reserved_amount: float = 0.0,
    strategy: Strategy = Strategy.AVALANCHE,
) -> dict:
    """
    Compara o PLANO INTEIRO (não só a dívida isolada) em dois cenários:
      - "a_vista": a dívida-alvo continua ROTATIVO, amortizada normalmente
        dentro da estratégia escolhida.
      - "acordo": a dívida-alvo sai da fila rotativa e vira um ACORDO_ATIVO
        com parcela fixa, competindo por espaço no fluxo de caixa com as
        parcelas fixas já existentes.

    A comparação é do plano inteiro (não isolada) porque o acordo muda o
    fluxo de caixa disponível para TODAS as outras dívidas — retirar uma
    dívida da fila do Avalanche libera dinheiro pras demais mais cedo, mas
    trava uma parcela fixa obrigatória por N meses.
    """
    target = next((d for d in revolving_debts if d.id == target_debt_id), None)
    if target is None:
        raise ValueError(f"Dívida rotativa '{target_debt_id}' não encontrada")

    cash_result = simulate_cash_flow_payoff(
        revolving_debts, installment_debts, monthly_income, reserved_amount, strategy
    )

    remaining_revolving = [d for d in revolving_debts if d.id != target_debt_id]
    agreement_debt = simulate_agreement(target, agreement_installment_amount, agreement_num_installments)
    agreement_result = simulate_cash_flow_payoff(
        remaining_revolving, installment_debts + [agreement_debt], monthly_income, reserved_amount, strategy
    )

    total_agreement_cost = round(agreement_installment_amount * agreement_num_installments, 2)
    cheaper = "acordo" if agreement_result.total_paid < cash_result.total_paid else "a_vista"
    faster = "acordo" if agreement_result.months_to_payoff < cash_result.months_to_payoff else "a_vista"

    return {
        "a_vista": cash_result,
        "acordo": agreement_result,
        "custo_total_acordo": total_agreement_cost,
        "diferenca_custo_total_plano": round(agreement_result.total_paid - cash_result.total_paid, 2),
        "diferenca_meses_plano": agreement_result.months_to_payoff - cash_result.months_to_payoff,
        "opcao_mais_barata": cheaper,
        "opcao_mais_rapida": faster,
    }
