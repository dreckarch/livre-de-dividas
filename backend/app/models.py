import uuid
from sqlalchemy import Column, String, Float, Boolean, Integer
from app.database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class IncomeSource(Base):
    __tablename__ = "income_sources"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)  # ex: "Salário CLT", "Vale Transporte", "Comissão"
    type = Column(String, nullable=False)  # salario | vt | va | comissao | outro
    amount = Column(Float, nullable=False)
    frequency = Column(String, nullable=False, default="mensal")  # mensal | quinzenal | variavel


class DebtRecord(Base):
    """
    Uma dívida pode ser de três categorias (coluna `category`):

    - "rotativo": cartão de crédito, cheque especial.
      Usa: balance, annual_interest_rate, minimum_payment.

    - "parcelado_fixo": financiamento, empréstimo pessoal, consignado.
      Usa: installment_amount, installments_total, installments_paid,
      installments_overdue. `balance` e `annual_interest_rate` ficam nulos
      (o custo já está embutido no valor da parcela).

    - "acordo_ativo": nasce da conversão de uma dívida rotativa via
      simulação de acordo. Usa os mesmos campos de parcelado_fixo, mais
      `converted_from_debt_id` apontando pra dívida rotativa original
      (guardado só como referência histórica).
    """
    __tablename__ = "debts"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="rotativo")  # rotativo | parcelado_fixo | acordo_ativo
    debt_type = Column(String, nullable=False, default="outro")  # cartao | emprestimo | financiamento | cheque_especial | outro
    active = Column(Boolean, default=True)

    # --- Campos de ROTATIVO ---
    balance = Column(Float, nullable=True)
    annual_interest_rate = Column(Float, nullable=True)
    minimum_payment = Column(Float, nullable=True)

    # --- Campos de PARCELADO_FIXO / ACORDO_ATIVO ---
    installment_amount = Column(Float, nullable=True)       # valor_parcela_regular
    installments_total = Column(Integer, nullable=True)      # total_parcelas
    installments_paid = Column(Integer, nullable=True)       # parcela_atual (quantas já foram pagas)
    installments_overdue = Column(Integer, nullable=True, default=0)  # parcelas_em_atraso

    converted_from_debt_id = Column(String, nullable=True)  # referência, se nasceu de um acordo

    due_day = Column(String, nullable=True)
