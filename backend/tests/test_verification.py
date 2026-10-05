from agents.verification import score_answer

# Long enough to clear the "too short" branch, no refusal phrases.
GOOD = (
    "Root Cause Analysis: the seal failed because the vibration exceeded the rated limit "
    "for the bearing housing over a sustained period of operation under load conditions."
)


def test_refusal_signals_score_low():
    assert score_answer("I apologize, but I cannot find that in the documents.", True) < 60


def test_short_answers_score_low():
    assert score_answer("Yes.", True) < 70


def test_grounded_structured_answer_scores_high():
    answer = GOOD + "\n- point one\n- point two [Source: manual.pdf]"
    assert score_answer(answer, True) > 85


def test_citations_raise_the_score():
    plain = score_answer(GOOD, True)
    cited = score_answer(GOOD + " [Source: a.pdf] [Source: b.pdf]", True)
    assert cited > plain


def test_missing_context_falls_back_to_fixed_score():
    assert score_answer(GOOD, False) == 75.0


def test_score_is_capped():
    answer = GOOD * 20 + "[ARTIFACT: X]" + "[Source: a.pdf]" * 20 + "\n- bullet"
    assert score_answer(answer, True) <= 98.5


def test_low_confidence_answers_trigger_the_retry_threshold():
    # The orchestrator loops back to the planner below 60.
    assert score_answer("I don't have that information.", True) < 60
