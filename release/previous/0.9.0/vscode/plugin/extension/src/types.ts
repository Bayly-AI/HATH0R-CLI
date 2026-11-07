export interface Hath0rBot {
  name: string;
  category: string;
  status: "idle" | "running" | "active";
  description: string;
}

export interface DoctorReport {
  status: "healthy" | "degraded" | "failing";
  checks_passed: number;
  checks_total: number;
  details: string[];
}

export interface FinOpsTokenizerReport {
  script_families_audited: number;
  subword_inflation_max: number;
  estimated_cost_reduction_pct: number;
}
