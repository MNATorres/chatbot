"""Configuración centralizada de logging con loguru.

Reemplaza los ``print()`` desperdigados por logs con niveles, timestamps, colores
y UTF-8. Además intercepta el logging estándar (uvicorn, httpx, discord.py) para
que TODO salga con un único formato unificado.

Se configura una sola vez al importar `main.py`.
"""

import logging
import sys

from loguru import logger

from chatbot.config import settings


class InterceptHandler(logging.Handler):
    """Redirige los registros del `logging` estándar hacia loguru.

    Así los logs de uvicorn/httpx/discord.py aparecen con el mismo formato que los
    nuestros, en vez de dos estilos distintos mezclados.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Traduce el nivel del logging estándar al de loguru (o usa el número).
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Busca el frame que originó el log para reportar bien el origen.
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> None:
    """Deja a loguru como único sink y enruta el logging estándar hacia él."""
    # En Windows la consola puede venir en cp1252 y romper al imprimir emojis.
    # Forzamos UTF-8 para que los logs con 💬/⚠️/✅ nunca tiren UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    log_level = "DEBUG" if settings.DEBUG else "INFO"

    # 1. Sink de loguru: reemplaza el default por uno con formato propio.
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        enqueue=True,  # thread/async-safe: seguro con BackgroundTasks y concurrencia
        backtrace=False,
        diagnose=settings.DEBUG,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        ),
    )

    # 2. Enruta el logging estándar (uvicorn, httpx, discord.py) hacia loguru.
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "discord"):
        std_logger = logging.getLogger(name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False
