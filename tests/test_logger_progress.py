import logging
from installer.core.logger import get_logger
from installer.core.progress import StepProgress, STEPS


def test_get_logger_returns_logger():
    logger = get_logger("test_installer")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_installer"


def test_logger_has_handler():
    logger = get_logger("test_installer2")
    assert len(logger.handlers) > 0


def test_logger_idempotent():
    a = get_logger("test_idem")
    b = get_logger("test_idem")
    assert a is b
    assert len(a.handlers) == 1  # not doubled


def test_logger_with_file(tmp_path):
    log_file = str(tmp_path / "sub" / "installer.log")
    logger = get_logger("test_file_logger", log_file=log_file)
    logger.info("hello from test")
    # file handler was added
    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1
    import os
    assert os.path.exists(log_file)


def test_steps_count():
    assert len(STEPS) == 5


def test_steps_numbered_1_to_5():
    numbers = [s[0] for s in STEPS]
    assert numbers == [1, 2, 3, 4, 5]


def test_step_progress_advance_no_crash():
    sp = StepProgress()
    sp.start()
    for i in range(1, 6):
        with sp.step(i):
            pass
    sp.finish(success=True)


def test_step_progress_failure_no_crash():
    sp = StepProgress()
    sp.start()
    sp.advance(1)
    sp.finish(success=False)
