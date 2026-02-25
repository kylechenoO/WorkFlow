"""
System Context Processors

Injects application version and copyright into every template context.
"""

## import buildin pkgs
import re

## import django pkgs
from django.conf import settings


## read once at startup — pyproject.toml never changes at runtime
def _load_meta():
    meta = {'version': '0.0.3', 'author': 'Kyle', 'year': '2026'}
    try:
        toml_path = settings.PROJ_PATH / 'pyproject.toml'
        content = toml_path.read_text(encoding='utf-8')

        m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if m:
            meta['version'] = m.group(1).strip()

        m = re.search(r'authors\s*=\s*\[.*?name\s*=\s*["\']([^"\']*)["\']', content, re.DOTALL)
        if m:
            meta['author'] = m.group(1).strip()

    except Exception:
        pass
    return meta


_META = _load_meta()


def app_info(request):
    """
    Add app_version and app_copyright to every template context.

    Usage in templates:
        {{ app_version }}
        {{ app_copyright }}
    """

    return {
        'app_version': _META['version'],
        'app_copyright': 'Copyright © 2026 %s' % _META['author'],
    }
