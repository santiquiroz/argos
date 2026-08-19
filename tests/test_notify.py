from argos.notify import NotificationPolicy, format_message, parse_kinds


def test_parse_kinds():
    assert parse_kinds("behavior, new_person ,") == {"behavior", "new_person"}


def test_policy_filters_by_kind():
    policy = NotificationPolicy({"behavior"}, cooldown_s=60)

    assert policy.should_notify({"kind": "behavior", "camera": "front"}, now=100.0) is True
    assert policy.should_notify({"kind": "recognized", "camera": "front"}, now=100.0) is False


def test_policy_cooldown_suppresses_same_subject():
    policy = NotificationPolicy({"behavior"}, cooldown_s=300)
    event = {"kind": "behavior", "person_id": "p1"}

    assert policy.should_notify(event, now=1000.0) is True   # first fires
    assert policy.should_notify(event, now=1100.0) is False  # within cooldown → suppressed
    assert policy.should_notify(event, now=1400.0) is True   # after cooldown → fires again


def test_policy_cooldown_is_per_subject():
    policy = NotificationPolicy({"behavior"}, cooldown_s=300)

    assert policy.should_notify({"kind": "behavior", "person_id": "a"}, now=0.0) is True
    # A different subject is not suppressed by A's recent alert.
    assert policy.should_notify({"kind": "behavior", "person_id": "b"}, now=1.0) is True


def test_format_message_behavior():
    title, body = format_message({"kind": "behavior", "label": "falling", "camera": "yard", "score": 0.91})

    assert "falling" in title
    assert "91%" in body
    assert "yard" in body
