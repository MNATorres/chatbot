"""Test mínimo de la configuración de logging: que corre sin error y que el
InterceptHandler traduce un registro estándar a loguru."""
import logging

from chatbot.logging_config import configure_logging, InterceptHandler


def test_configure_logging_no_falla():
    # Debe poder configurarse (y reconfigurarse) sin lanzar.
    configure_logging()
    configure_logging()


def test_intercept_handler_maneja_un_registro():
    handler = InterceptHandler()
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="arrancando en %s",
        args=("127.0.0.1",),
        exc_info=None,
    )
    # No debe lanzar al reenviar el registro a loguru.
    handler.emit(record)
