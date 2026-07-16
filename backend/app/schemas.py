from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


# ---------- Renda ----------
class IncomeBase(BaseModel):
    name: str
    type: str = Field(description="salario | vt | va | comissao | outro")
    amount: float
    frequency: str = "mensal"


class IncomeCreate(IncomeBase):
    pass


class IncomeOut(IncomeBase):
    id: str

    class Config:
        from_attributes = True


# ---------- Dívida ----------
class DebtBase(BaseModel):
    name: str
    category: str = Field(default="rotativo", description="rotativo | parcelado_fixo | acordo_ativo")
    debt_type: str = "outro"
    active: bool = True

    # Rotativo
    balance: Optional[float] = None
    annual_interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None

    # Parcelado fixo / Acordo ativo
    installment_amount: Optional[float] = None
    installments_total: Optional[int] = None
    installments_paid: Optional[int] = 0
    installments_overdue: Optional[int] = 0

    due_day: Optional[str] = None

    @model_validator(mode="after")
    def validate_by_category(self):
        if self.category == "rotativo":
            missing = [
                f for f, v in [
                    ("balance", self.balance),
                    ("annual_interest_rate", self.annual_interest_rate),
                    ("minimum_payment", self.minimum_payment),
                ] if v is None
            ]
            if missing:
                raise ValueError(f"Dívida rotativa exige os campos: {', '.join(missing)}")
        elif self.category in ("parcelado_fixo", "acordo_ativo"):
            missing = [
                f for f, v in [
                    ("installment_amount", self.installment_amount),
                    ("installments_total", self.installments_total),
                ] if v is None
            ]
            if missing:
                raise ValueError(f"Dívida {self.category} exige os campos: {', '.join(missing)}")
            if self.installments_paid is not None and self.installments_total is not None:
                if self.installments_paid > self.installments_total:
                    raise ValueError("installments_paid não pode ser maior que installments_total")
        else:
            raise ValueError("category deve ser 'rotativo', 'parcelado_fixo' ou 'acordo_ativo'")
        return self


class DebtCreate(DebtBase):
    pass


class DebtOut(DebtBase):
    id: str
    converted_from_debt_id: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Plano de quitação ----------
class PlanRequest(BaseModel):
    reserved_amount: float = Field(
        default=0.0, description="Quanto reter por mês para despesas fixas/reserva, antes de destinar o resto às dívidas"
    )
    strategy: Optional[str] = Field(default=None, description="avalanche | snowball | None para comparar as duas")


class MonthSnapshotOut(BaseModel):
    month: int
    debt_id: str
    debt_name: str
    kind: str
    balance_start: float
    interest_charged: float
    payment_made: float
    balance_end: float


class PayoffResultOut(BaseModel):
    strategy: str
    months_to_payoff: int
    total_interest_paid: float
    total_paid: float
    payoff_achieved: bool
    payoff_order: List[str]
    at_risk_debt_ids: List[str]
    budget_deficit_months: List[int]
    schedule: List[MonthSnapshotOut]


class PlanComparisonOut(BaseModel):
    avalanche: PayoffResultOut
    snowball: PayoffResultOut
    interest_saved_with_avalanche: float
    months_saved_with_avalanche: int
    monthly_income_used: float
    reserved_amount_used: float


# ---------- Simulação de Acordo ----------
class AgreementSimulationRequest(BaseModel):
    target_debt_id: str = Field(description="id de uma dívida ROTATIVO existente")
    agreement_installment_amount: float
    agreement_num_installments: int
    reserved_amount: float = 0.0
    strategy: Optional[str] = Field(default="avalanche", description="avalanche | snowball")


class AgreementComparisonOut(BaseModel):
    a_vista: PayoffResultOut
    acordo: PayoffResultOut
    custo_total_acordo: float
    diferenca_custo_total_plano: float
    diferenca_meses_plano: int
    opcao_mais_barata: str
    opcao_mais_rapida: str


# ---------- IA ----------
class AiAnalysisRequest(BaseModel):
    reserved_amount: float = 0.0
    model: Optional[str] = None


class AiAnalysisResponse(BaseModel):
    analysis: str
    model_used: str


class AiAgreementAnalysisRequest(AgreementSimulationRequest):
    model: Optional[str] = None


class AiAgreementAnalysisResponse(BaseModel):
    analysis: str
    model_used: str
