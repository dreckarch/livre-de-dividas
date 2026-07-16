// Em modo "tudo em um" (backend servindo o frontend buildado), o caminho
// relativo "/api" já funciona, pois está na mesma origem.
// Em modo desenvolvimento (Vite dev server em outra porta), aponta pro backend local.
const BASE_URL = import.meta.env.DEV ? "http://localhost:8000/api" : "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro na requisição: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Renda
  listIncome: () => request("/income/"),
  createIncome: (data) => request("/income/", { method: "POST", body: JSON.stringify(data) }),
  deleteIncome: (id) => request(`/income/${id}`, { method: "DELETE" }),

  // Dívidas
  listDebts: () => request("/debts/"),
  createDebt: (data) => request("/debts/", { method: "POST", body: JSON.stringify(data) }),
  updateDebt: (id, data) => request(`/debts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteDebt: (id) => request(`/debts/${id}`, { method: "DELETE" }),

  // Plano
  simulatePlan: (data) => request("/plan/simulate", { method: "POST", body: JSON.stringify(data) }),
  simulateAgreement: (data) => request("/plan/simulate-agreement", { method: "POST", body: JSON.stringify(data) }),

  // IA
  analyzeWithAi: (data) => request("/ai/analyze", { method: "POST", body: JSON.stringify(data) }),
  analyzeAgreementWithAi: (data) => request("/ai/analyze-agreement", { method: "POST", body: JSON.stringify(data) }),
};
