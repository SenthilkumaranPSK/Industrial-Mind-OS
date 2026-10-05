"""Heuristic answer scoring for the verifier node.

Pure function, no LLM call and no storage imports, so the scoring rules can be
unit-tested without booting Qdrant or the graph.
"""

BAD_SIGNALS = (
    "i apologize", "no context", "no information", "cannot find",
    "i don't have", "not provided", "no provided", "error connecting",
    "system:", "no web information found",
)


def score_answer(answer: str, has_context: bool) -> float:
    """
    Grade a synthesized answer from 0-100 on refusal signals, length,
    citation density and markdown structure.

    `has_context` is whether the memory builder produced any fused context.
    """
    answer = answer or ""

    if any(sig in answer.lower() for sig in BAD_SIGNALS):
        # Low quality signals detected
        return max(40.0, 55.0 - (len(answer) % 15))

    if len(answer) < 80:
        # Answer too short to be useful
        return 60.0 + (len(answer) / 10)

    if not has_context:
        # Context is strangely missing but the answer passed normally
        return 75.0

    score = 84.0
    # 1. Reward richness and length (up to +6 points)
    score += min(6.0, len(answer) / 250)
    # 2. Reward proper citations (up to +5 points)
    score += min(5.0, answer.count("[Source:") * 1.25)
    # 3. Reward structured markdown (up to +3 points)
    if "- " in answer or "1. " in answer or "**" in answer:
        score += 2.0
    if "[ARTIFACT:" in answer:
        score += 1.5

    return round(min(98.5, score), 1)
