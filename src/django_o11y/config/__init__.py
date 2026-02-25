"""Configuration APIs."""

from django_o11y.config.setup import get_config, get_o11y_config
from django_o11y.config.utils import validate_config

__all__ = ["get_config", "get_o11y_config", "validate_config"]
