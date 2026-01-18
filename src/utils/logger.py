"""Logging sistemi"""
import logging
import sys
from pathlib import Path

# Windows iÃ§in encoding dÃ¼zeltmesi (emoji vs.)
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        # BazÄ± ortamlarda sys.stdout.buffer olmayabiliyor, sessiz geÃ§
        pass

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def setup_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """Logger'Ä± kur (console + file). AynÄ± logger'a tekrar tekrar handler eklemez."""
    # Log dizinleri
    Path('logs').mkdir(exist_ok=True)
    Path('logs/trades').mkdir(exist_ok=True)
    Path('logs/errors').mkdir(exist_ok=True)

    logger = logging.getLogger(name)

    # Daha Ã¶nce kurulmuÅŸsa tekrar kurma (duplicate log probleminden de kurtarÄ±r)
    if getattr(logger, "_greentrades_configured", False):
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False  # root'a akÄ±tÄ±p iki kez yazdÄ±rmasÄ±n

    # Formatter
    if HAS_COLORLOG:
        formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(f'logs/{name}.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s'
    ))

    logger.addHandler(console)
    logger.addHandler(file_handler)

    # iÅŸaret koy: bu logger artÄ±k kurulu
    logger._greentrades_configured = True  # type: ignore[attr-defined]
    return logger


def get_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """Mevcut logger'Ä± al; handler yoksa otomatik kur."""
    logger = logging.getLogger(name)
    if not logger.handlers or not getattr(logger, "_greentrades_configured", False):
        return setup_logger(name, level=level)
    # seviyesi gÃ¼ncellenmek istenirse:
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger



