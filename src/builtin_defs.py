"""Funções intrínsecas Fortran 77 suportadas pelo compilador.

Fornece: is_builtin(name), RETURN_TYPES, call_builtin(name, args)
"""
from math import sqrt, exp, log, sin, cos, tan

BUILTIN_FUNCTIONS = {'MOD', 'REAL', 'INT', 'ABS', 'SQRT', 'EXP', 'LOG', 'SIN', 'COS', 'TAN'}

RETURN_TYPES = {
    'MOD': 'INTEGER', 'INT': 'INTEGER',
    'REAL': 'REAL', 'ABS': 'REAL', 'SQRT': 'REAL',
    'EXP': 'REAL', 'LOG': 'REAL', 'SIN': 'REAL', 'COS': 'REAL', 'TAN': 'REAL',
}

def is_builtin(name: str) -> bool:
    return bool(name) and name.upper() in BUILTIN_FUNCTIONS

def _sf(v):   # safe float
    try: return float(v)
    except Exception: return 0.0

def _si(v):   # safe int
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return 0

BUILTIN_IMPLS = {
    'MOD':  lambda a: (int(a[0]) % int(a[1])) if isinstance(a[0], int) and isinstance(a[1], int) else (_sf(a[0]) - int(_sf(a[0]) / _sf(a[1])) * _sf(a[1])) if a[1] != 0 else 0,
    'INT':  lambda a: _si(a[0]),
    'REAL': lambda a: _sf(a[0]),
    'ABS':  lambda a: abs(_sf(a[0])),
    'SQRT': lambda a: sqrt(_sf(a[0])),
    'EXP':  lambda a: exp(_sf(a[0])),
    'LOG':  lambda a: log(_sf(a[0])),
    'SIN':  lambda a: sin(_sf(a[0])),
    'COS':  lambda a: cos(_sf(a[0])),
    'TAN':  lambda a: tan(_sf(a[0])),
}

def call_builtin(name: str, args: list):
    fn = BUILTIN_IMPLS.get(name.upper())
    if not fn:
        raise NotImplementedError(f"Builtin '{name}' not implemented")
    return fn(args)