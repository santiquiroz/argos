from argos.config import Settings
from argos.settings_store import SettingsStore, apply_overrides


def test_update_persists_only_editable_fields(tmp_path):
    store = SettingsStore(tmp_path / "s.json")

    store.update({"notify_on": "zone", "device": "cpu", "api_key": "hax", "notify_cooldown_s": 60})

    saved = store.read()
    assert saved == {"notify_on": "zone", "notify_cooldown_s": 60}  # device/api_key rejected


def test_apply_overrides_mutates_only_editable():
    settings = Settings()

    apply_overrides(settings, {"notify_cooldown_s": 42, "device": "cpu"})

    assert settings.notify_cooldown_s == 42
    assert settings.device == "dml:0"  # not editable → unchanged


def test_update_ignores_none_values(tmp_path):
    store = SettingsStore(tmp_path / "s.json")

    store.update({"notify_on": "zone", "notify_webhook_url": None})

    assert store.read() == {"notify_on": "zone"}
