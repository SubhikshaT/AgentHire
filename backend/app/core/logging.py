"""Logging setup. Never log passwords, tokens or full resume text."""
import logging


def setup_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # SQL echo is noisy and may print data; keep it off.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    for noisy in ("httpx", "httpx2", "httpcore", "httpcore2", "urllib3", "filelock", "huggingface_hub",
                  "sentence_transformers", "asyncio", "multipart", "fontTools"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
