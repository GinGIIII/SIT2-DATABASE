from __future__ import annotations

from datetime import datetime
from typing import Any

from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment


def _getpath(obj: Any, path: str, default: str = "—") -> Any:

    if obj is None:
        return default

    cur = obj
    for part in path.split("."):
        if cur is None:
            return default

        # dict / mapping
        if isinstance(cur, dict):
            cur = cur.get(part, None)
            continue

        # Django QuerySet values() может отдавать dict-like
        if hasattr(cur, "get") and callable(getattr(cur, "get")) and not hasattr(cur, part):
            try:
                cur = cur.get(part)
                continue
            except Exception:
                pass

        # обычный объект / ORM
        if hasattr(cur, part):
            cur = getattr(cur, part)
        else:
            return default

    return default if cur is None else cur


def _dt(value: Any, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime(fmt)
    return str(value)


def environment(**options):
    env = Environment(**options)

    # globals (чтобы можно было static/url)
    env.globals.update(
        static=static,
        url=reverse,
    )

    # filters
    env.filters["getpath"] = _getpath
    env.filters["dt"] = _dt
    return env