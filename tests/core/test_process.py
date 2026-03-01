"""Tests for process runtime helpers."""

import sys
from unittest.mock import patch

import pytest

from django_o11y.utils.process import is_management_command, should_setup_observability


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


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["manage.py", "runserver"], True),
        (["manage.py", "daphne"], True),
        (["manage.py", "migrate"], False),
        (["manage.py", "shell"], False),
        (["pylint", "."], False),
        (["pytest", "tests"], False),
        (["celery", "worker", "-A", "myapp"], True),
        (["gunicorn", "myapp.wsgi"], True),
        (["uvicorn", "myapp.asgi:application"], True),
        (["python3", "-m", "celery", "worker", "-A", "myapp"], True),
        (["python3", "-m", "uvicorn", "myapp.asgi:application"], True),
        (["python3", "-m", "pylint", "."], False),
    ],
)
def test_should_setup_observability(argv, expected):
    with patch.object(sys, "argv", argv):
        assert should_setup_observability() is expected
