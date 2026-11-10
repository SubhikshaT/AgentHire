"""Interview answer rubric: dimensions, weights and aggregation (shared by evaluator and reports)."""
RUBRIC_VERSION = "rubric-1.0"

DEFAULT_RUBRIC_WEIGHTS = {
    "technical_correctness": 35.0,
    "conceptual_understanding": 25.0,
    "problem_solving": 20.0,
    "clarity": 10.0,
    "relevance": 10.0,
}

DIMENSION_DESCRIPTIONS = {
    "technical_correctness": "Are the technical statements correct? Wrong facts lower this a lot.",
    "conceptual_understanding": "Does the answer show understanding of why, not just what?",
    "problem_solving": "Is there a sensible approach, trade-offs, steps or an example?",
    "clarity": "Is the explanation clear and well organized? Length alone does not count.",
    "relevance": "Does the answer address the question that was asked?",
}

VERDICTS = ["correct", "partially_correct", "incorrect", "insufficient"]


def validate_rubric_weights(w: dict) -> dict:
    if set(w) != set(DEFAULT_RUBRIC_WEIGHTS):
        raise ValueError(f"Rubric weights must have exactly these keys: {sorted(DEFAULT_RUBRIC_WEIGHTS)}")
    vals = {k: float(v) for k, v in w.items()}
    if any(v < 0 or v > 100 for v in vals.values()):
        raise ValueError("Each weight must be between 0 and 100.")
    if abs(sum(vals.values()) - 100) > 0.01:
        raise ValueError(f"Rubric weights must add up to 100 (they add up to {sum(vals.values()):g}).")
    return vals


def weighted_answer_score(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Dimension scores are 0-10. Returns 0-100."""
    total_w = sum(weights.values())
    return round(sum(weights[k] * scores[k] for k in weights) / total_w * 10, 1)
