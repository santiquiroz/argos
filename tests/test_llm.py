from argos.llm import _extract_text, build_digest_prompt, deterministic_digest


def test_deterministic_digest_empty():
    assert "No activity" in deterministic_digest([], {})


def test_deterministic_digest_summarizes_events():
    events = [
        {"kind": "behavior", "label": "falling", "camera": "yard", "ts": 1.0},
        {"kind": "zone", "label": "gate", "camera": "front", "ts": 1.0},
        {"kind": "new_person", "camera": "front", "ts": 1.0},
    ]

    digest = deterministic_digest(events, {"persons": 3, "enrolled": 1})

    assert "3 events" in digest
    assert "2 camera(s)" in digest
    assert "falling" in digest
    assert "gate" in digest
    assert "3 distinct persons" in digest


def test_extract_text_anthropic_shape():
    assert _extract_text({"content": [{"type": "text", "text": "hi"}]}) == "hi"
    assert _extract_text({"content": []}) is None
    assert _extract_text({}) is None


def test_build_digest_prompt_embeds_summary():
    assert "SUMMARY_TOKEN" in build_digest_prompt("SUMMARY_TOKEN")
