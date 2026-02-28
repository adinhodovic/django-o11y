"""Tests for process runtime helpers."""

import sys
from unittest.mock import patch

import pytest

from django_o11y.utils.process import is_management_command


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["manage.py", "migrate"], True),
        (["manage.py", "shell"], True),
        (["manage.py", "runserver"], False),
        (["manage.py", "runserver_plus"], False),
        (["manage.py", "celery", "worker"], False),
        (["manage.py", "gunicorn"], False),
        (["manage.py", "run_gunicorn"], False),
        (["manage.py", "daphne"], False),
        (["manage.py", "uvicorn"], False),
        (["celery", "worker", "-A", "myapp"], False),
        (["gunicorn", "myapp.wsgi"], False),
        (["-c"], False),
    ],
)
def test_is_management_command(argv, expected):
    with patch.object(sys, "argv", argv):
        assert is_management_command() is expected
