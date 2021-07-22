# import pytest
#
#
# @pytest.fixture(autouse=True)
# def clear_loggers():
#     # https://github.com/pytest-dev/pytest/issues/5502#issuecomment-647157873
#     """Remove handlers from all loggers"""
#     import logging
#     loggers = [logging.getLogger()] + list(
#         logging.Logger.manager.loggerDict.values())
#     for logger in loggers:
#         handlers = getattr(logger, 'handlers', [])
#         for handler in handlers:
#             logger.removeHandler(handler)
