from dataclasses import dataclass
from domain.scoring.factors import Factor

UMBRAL_HIGH_RISK = 70
UMBRAL_REVIEW_REQUIRED = 30

@dataclass(frozen=True)
class ResultadoEvaluacion:
    score_total: int
    decision: str
    critical_blocks: list[str]
    factores: list[Factor]

def evaluar(factores: list[Factor]) -> ResultadoEvaluacion:
    score_total = sum(f.points for f in factores)
    critical_blocks = [f.factor_code for f in factores if f.is_critical_block]
    if critical_blocks:
        decision = "high_risk"
    elif score_total >= UMBRAL_HIGH_RISK:
        decision = "high_risk"
    elif score_total >= UMBRAL_REVIEW_REQUIRED:
        decision = "review_required"
    else:
        decision = "safe"
    return ResultadoEvaluacion(score_total, decision, critical_blocks, factores)
