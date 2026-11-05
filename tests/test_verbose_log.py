import logging

from er_save_manager import own_writes
from er_save_manager.ui import verbose_log
from er_save_manager.ui.settings import Settings


def test_verbose_log_records_writes_only_while_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(Settings, "get_data_dir", staticmethod(lambda: tmp_path))
    save = tmp_path / "ER0000.sl2"
    log = tmp_path / verbose_log.LOG_NAME
    try:
        verbose_log.set_enabled(True)
        own_writes.atomic_write(save, b"abc")
        text = log.read_text(encoding="utf-8")
        assert "Verbose logging on" in text
        assert f"Wrote {save} (3 bytes)" in text
    finally:
        verbose_log.set_enabled(False)

    own_writes.atomic_write(save, b"abcd")
    assert "4 bytes" not in log.read_text(encoding="utf-8")
    assert logging.getLogger("er_save_manager").level == logging.NOTSET
