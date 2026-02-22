"""
Module Introspection Library

Scans the mod/ directory and uses importlib + inspect to extract
class names, method signatures, and docstring-parsed parameter
schemas from workflow procedure modules. Returns structured data
compatible with the module_registry.js format used by the Visual Editor.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import os
import re
import sys
import json
import inspect
import importlib
import importlib.util
import traceback


## category display metadata
CATEGORY_META = {
    'common': {
        'label': 'Common',
        'icon': 'bi-gear',
        'color': '#0d6efd',
    },
    'mysql': {
        'label': 'MySQL',
        'icon': 'bi-database',
        'color': '#00758f',
    },
    'elasticsearchclient': {
        'label': 'Elasticsearch',
        'icon': 'bi-search',
        'color': '#f0bf2a',
    },
    'prometheus': {
        'label': 'Prometheus',
        'icon': 'bi-graph-up',
        'color': '#e6522c',
    },
}

## type mapping from python type hints/docstrings to JS types
TYPE_MAP = {
    'str': 'string',
    'string': 'string',
    'int': 'number',
    'float': 'number',
    'number': 'number',
    'bool': 'boolean',
    'boolean': 'boolean',
    'dict': 'json',
    'list': 'json',
    'object': 'json',
    'ref': 'ref',
}

## per-module display metadata (icon, color)
## new modules not listed here inherit from CATEGORY_META
MODULE_META = {
    ('common', 'Kt'):               {'icon': 'bi-chat-dots',        'color': '#6c757d'},
    ('common', 'Filter'):            {'icon': 'bi-funnel',           'color': '#0d6efd'},
    ('common', 'Http'):              {'icon': 'bi-globe',            'color': '#198754'},
    ('common', 'FileIO'):            {'icon': 'bi-file-earmark',     'color': '#6f42c1'},
    ('common', 'Notify'):            {'icon': 'bi-bell',             'color': '#ffc107'},
    ('common', 'Ssh'):               {'icon': 'bi-terminal',         'color': '#20c997'},
    ('common', 'MultiProcess'):      {'icon': 'bi-layers',           'color': '#e83e8c'},
    ('common', 'DataTransformer'):   {'icon': 'bi-arrow-left-right', 'color': '#6c757d'},
    ('mysql', 'MySQL'):              {'icon': 'bi-database',         'color': '#fd7e14'},
    ('elasticsearchclient', 'ElasticSearch'): {'icon': 'bi-search',        'color': '#00bfb3'},
    ('prometheus', 'Prometheus'):     {'icon': 'bi-graph-up',         'color': '#dc3545'},
}


class ModuleInspector(object):
    """
    Introspects workflow modules to extract metadata.

    Scans the mod/ directory for Python module files, loads each
    module via importlib, inspects the class methods, and parses
    Google-style docstrings to build a complete parameter registry.

    Responsibilities:
        - Scan mod/ directories for module files
        - Dynamically load and introspect modules
        - Parse docstrings for parameter schemas
        - Return structured JSON for the Visual Editor
    """

    def __init__(self, mod_path: str) -> None:
        """
        Initialize the ModuleInspector.

        Args:
            mod_path (str): Absolute path to the mod/ directory
        """

        self.mod_path = mod_path

        ## ensure mod/ is on sys.path for importlib
        if self.mod_path not in sys.path:
            sys.path.insert(0, self.mod_path)

    def scan_all(self) -> dict:
        """
        Scan all modules and return full registry data.

        Returns:
            dict: Registry in module_registry.js format:
                {
                    'common': {
                        'label': 'Common',
                        'icon': 'bi-gear',
                        'color': '#0d6efd',
                        'modules': {
                            'Http': { 'label': 'Http', 'methods': {...} },
                            ...
                        }
                    },
                    ...
                }
        """

        registry = {}

        try:
            ## scan for category directories
            for entry in sorted(os.listdir(self.mod_path)):
                cat_path = os.path.join(self.mod_path, entry)
                if not os.path.isdir(cat_path):
                    continue
                if entry.startswith('_') or entry.startswith('.'):
                    continue

                ## get category metadata
                meta = CATEGORY_META.get(entry, {
                    'label': entry.capitalize(),
                    'icon': 'bi-puzzle',
                    'color': '#6c757d',
                })

                modules = {}

                ## scan for .py files in category
                for filename in sorted(os.listdir(cat_path)):
                    if not filename.endswith('.py'):
                        continue
                    if filename.startswith('_'):
                        continue
                    ## skip backup files like "Filter 2.py"
                    if ' ' in filename:
                        continue

                    module_name = filename[:-3]  ## remove .py
                    mod_info = self.inspect_module(entry, module_name)
                    if mod_info:
                        modules[module_name] = mod_info

                if modules:
                    registry[entry] = {
                        'label': meta['label'],
                        'icon': meta['icon'],
                        'color': meta['color'],
                        'modules': modules,
                    }

        ## error handling
        except Exception as e:
            ## return whatever we have so far
            pass

        return registry

    def inspect_module(self, category: str, module_name: str) -> dict:
        """
        Introspect a single module file.

        Uses spec_from_file_location to load modules directly by file path,
        avoiding conflicts with installed pip packages (e.g. 'elasticsearch'
        pip package shadowing mod/elasticsearch/).

        Args:
            category (str): Category directory name (e.g. 'common')
            module_name (str): Module name without .py (e.g. 'Http')

        Returns:
            dict: Module info with methods and params, or None on failure
        """

        try:
            ## build file path and import via spec to avoid pip package conflicts
            file_path = os.path.join(self.mod_path, category, '%s.py' % module_name)
            if not os.path.isfile(file_path):
                return None

            import_name = 'wf_mod_%s_%s' % (category, module_name)
            spec = importlib.util.spec_from_file_location(import_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            cls = getattr(module, module_name, None)

            if cls is None:
                return None

            ## extract methods
            methods = {}
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                ## skip private/magic methods
                if name.startswith('_'):
                    continue

                ## check if it has the procedure signature (self, context, cfgs)
                sig = inspect.signature(method)
                params_list = list(sig.parameters.keys())

                ## procedure methods: (self, context, cfgs)
                if len(params_list) >= 3 and 'context' in params_list and 'cfgs' in params_list:
                    method_info = self._parse_method(name, method)
                    if method_info:
                        methods[name] = method_info

                ## also include methods like connect/disconnect that may have (self, context, cfgs)
                ## or simpler signatures — check docstring for Args: section
                elif len(params_list) >= 2:
                    docstring = inspect.getdoc(method)
                    if docstring and 'Args:' in docstring:
                        method_info = self._parse_method(name, method)
                        if method_info:
                            methods[name] = method_info

            if not methods:
                return None

            ## get module docstring for description
            cls_doc = inspect.getdoc(cls) or ''
            first_line = cls_doc.split('\n')[0].strip() if cls_doc else module_name

            ## look up module-specific icon/color, fallback to category
            mod_meta = MODULE_META.get((category, module_name), {})
            cat_meta = CATEGORY_META.get(category, {'icon': 'bi-puzzle', 'color': '#6c757d'})

            return {
                'label': module_name,
                'description': first_line,
                'mod': 'mod.%s.%s' % (category, module_name),
                'icon': mod_meta.get('icon', cat_meta.get('icon', 'bi-puzzle')),
                'color': mod_meta.get('color', cat_meta.get('color', '#6c757d')),
                'methods': methods,
            }

        ## error handling
        except Exception as e:
            return None

    def _parse_method(self, name: str, method) -> dict:
        """
        Parse a method's docstring to extract parameter schemas.

        Args:
            name (str): Method name
            method: Method object

        Returns:
            dict: Method info with label and params
        """

        docstring = inspect.getdoc(method) or ''
        first_line = docstring.split('\n')[0].strip() if docstring else name

        ## parse Args: section from docstring
        params = self._parse_docstring_args(docstring)

        ## parse Returns: section
        returns = self._parse_docstring_returns(docstring)

        result = {
            'label': first_line,
            'params': params,
        }

        if returns:
            result['returns'] = returns

        return result

    def _parse_docstring_args(self, docstring: str) -> dict:
        """
        Parse the Args: section from a Google-style docstring.

        Extracts parameter names, types, and descriptions.
        Skips 'context' and 'cfgs' params (internal to workflow engine).

        Args:
            docstring (str): Full docstring text

        Returns:
            dict: Parameter schemas keyed by name
        """

        params = {}
        if not docstring:
            return params

        ## find Args: section (stop at blank line or new section like Returns:)
        args_match = re.search(r'Args:\s*\n((?:[ \t]+\S.*\n?)*)', docstring)
        if not args_match:
            return params

        args_text = args_match.group(1)

        ## parse each param line: "name (type): description"
        param_pattern = re.compile(
            r'^\s+(\w+)\s*\(([^)]+)\)\s*:\s*(.+?)$',
            re.MULTILINE
        )

        for match in param_pattern.finditer(args_text):
            param_name = match.group(1).strip()
            param_type = match.group(2).strip()
            param_desc = match.group(3).strip()

            ## skip internal params
            if param_name in ('context', 'cfgs', 'self', 'logger'):
                continue

            ## map python type to JS type
            js_type = TYPE_MAP.get(param_type.lower(), 'string')

            ## determine if optional
            is_optional = 'optional' in param_desc.lower()

            ## extract default value from description if present
            default_match = re.search(r'\(default:\s*(.+?)\)\s*$', param_desc)
            default_val = None
            has_default = False
            if default_match:
                default_raw = default_match.group(1).strip()
                default_val = self._parse_default_value(default_raw)
                has_default = True
                ## strip the (default: ...) from the description
                param_desc = re.sub(r'\s*\(default:\s*.+?\)\s*$', '', param_desc).strip()
                ## having a default implies optional
                is_optional = True

            param_info = {
                'type': js_type,
                'desc': param_desc,
                'required': not is_optional,
            }

            if has_default:
                param_info['default'] = default_val

            params[param_name] = param_info

        return params

    def _parse_default_value(self, raw: str):
        """
        Parse a default value string into a typed Python value.

        Supports: bool, null, quoted string, JSON array/object, number, plain string.

        Args:
            raw (str): Raw default value string from docstring

        Returns:
            Parsed value (bool, None, str, int, float, list, or dict)
        """

        ## handle boolean
        if raw.lower() in ('true', 'false'):
            return raw.lower() == 'true'

        ## handle null/none
        if raw.lower() in ('null', 'none'):
            return None

        ## handle quoted strings
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            return raw[1:-1]

        ## handle JSON structures (arrays, objects)
        if raw.startswith('[') or raw.startswith('{'):
            try:
                return json.loads(raw)
            except Exception:
                return raw

        ## handle numbers
        try:
            if '.' in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            pass

        ## fallback: treat as string
        return raw

    def _parse_docstring_returns(self, docstring: str) -> dict:
        """
        Parse the Returns: section from a Google-style docstring.

        Args:
            docstring (str): Full docstring text

        Returns:
            dict: Return type info, or None if not found
        """

        if not docstring:
            return None

        ## find Returns: section
        returns_match = re.search(r'Returns:\s*\n\s+(\w+)\s*:\s*(.+?)$', docstring, re.MULTILINE)
        if not returns_match:
            return None

        return {
            'type': returns_match.group(1).strip(),
            'desc': returns_match.group(2).strip(),
        }

    def list_modules(self) -> list:
        """
        List all module files with basic metadata (no introspection).

        Returns:
            list: List of dicts with category, name, file_path, size, modified
        """

        modules = []

        try:
            for entry in sorted(os.listdir(self.mod_path)):
                cat_path = os.path.join(self.mod_path, entry)
                if not os.path.isdir(cat_path):
                    continue
                if entry.startswith('_') or entry.startswith('.'):
                    continue

                for filename in sorted(os.listdir(cat_path)):
                    if not filename.endswith('.py'):
                        continue
                    if filename.startswith('_'):
                        continue
                    ## skip backup files
                    if ' ' in filename:
                        continue

                    file_path = os.path.join(cat_path, filename)
                    stat = os.stat(file_path)

                    modules.append({
                        'category': entry,
                        'name': filename[:-3],
                        'filename': filename,
                        'file_path': file_path,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                    })

        ## error handling
        except Exception as e:
            pass

        return modules
