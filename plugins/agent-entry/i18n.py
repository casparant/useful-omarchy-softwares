# Modified 2026-10-19: Chinese/English locale and preference selection.
# Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
"""Small, side-effect-free language helpers for the standalone plugin."""

from __future__ import annotations

import os
import re
from typing import Mapping

PREFERENCES = ("auto", "en", "zh")


def locale_language(environ: Mapping[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    locale = next((values.get(key, "") for key in ("LC_ALL", "LC_MESSAGES", "LANG") if values.get(key)), "")
    # zh_CN, zh_TW, zh-Hans and the bare language tag all select Chinese.
    return "zh" if re.split(r"[-_.@]", locale.lower(), maxsplit=1)[0] == "zh" else "en"


def resolve_language(preference: str = "auto", environ: Mapping[str, str] | None = None) -> str:
    return preference if preference in ("en", "zh") else locale_language(environ)


def translate(zh: str, en: str, language: str) -> str:
    return zh if language == "zh" else en
