from core.text_utils import clean_spaced_text


def test_collapses_spaced_out_pdf_artifact():
    assert clean_spaced_text("C o n t a i n e r i z a t i o n") == "Containerization"


def test_leaves_normal_prose_untouched():
    text = "The pump failed at 120 psi during the night shift."
    assert clean_spaced_text(text) == text


def test_short_runs_are_not_collapsed():
    # Fewer than 5 single-char groups: real words, not an extraction artifact.
    assert clean_spaced_text("a b c d") == "a b c d"


def test_repairs_artifact_embedded_in_a_sentence():
    out = clean_spaced_text("See the V a l v e P r e s s u r e limit below.")
    assert "ValvePressure" in out
    assert out.startswith("See the ")
    assert out.endswith("limit below.")


def test_handles_empty_and_none():
    assert clean_spaced_text("") == ""
    assert clean_spaced_text(None) is None
