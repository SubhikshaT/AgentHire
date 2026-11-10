"""Lazy spaCy loader. If the model is missing, rule-based extraction still works."""
import logging
from functools import lru_cache

logger = logging.getLogger("agenthire.nlp")


@lru_cache
def get_spacy():
    try:
        import spacy

        return spacy.load("en_core_web_sm", disable=["lemmatizer"])
    except Exception as e:  # model not downloaded
        logger.warning("spaCy model en_core_web_sm not available (%s). Name/org detection uses rules only.", e)
        return None
