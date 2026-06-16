"""A safe calculator tool.

Supports the usual arithmetic (``+ - * / // % **``) plus a few named helper
functions the agent can use directly:

* ``sqrt(x)``    -- square root
* ``square(x)``  -- x squared
* ``cube(x)``    -- x cubed
* ``percent(a, b)`` -- a percent of b, i.e. ``a / 100 * b``
* common math functions: ``abs, round, pow, sin, cos, tan, log, log10, exp``

Expressions are evaluated with a restricted AST walker, so arbitrary code can
never run -- only numbers, the operators above and the whitelisted functions.
"""

from __future__ import annotations

import ast
import math
import operator as op
from typing import Any, Callable, Dict

from .base import Tool

# Allowed binary / unary operators mapped to their implementations.
_BIN_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}
_UNARY_OPS: Dict[type, Callable[[Any], Any]] = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

# Whitelisted names callable from within an expression.
_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "sqrt": math.sqrt,
    "square": lambda x: x * x,
    "cube": lambda x: x * x * x,
    "percent": lambda a, b: a / 100.0 * b,
    "abs": abs,
    "round": round,
    "pow": pow,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "factorial": math.factorial,
}
_CONSTANTS: Dict[str, float] = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):  # numbers only
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCTIONS.get(node.func.id)
        if fn is None:
            raise ValueError(f"Unknown function: {node.func.id}")
        args = [_eval_node(a) for a in node.args]
        return fn(*args)
    raise ValueError(f"Unsupported expression element: {ast.dump(node)}")


def safe_eval(expression: str) -> float:
    """Evaluate a mathematical ``expression`` string safely."""
    parsed = ast.parse(expression, mode="eval")
    return _eval_node(parsed)


def _calculate(expression: str) -> str:
    result = safe_eval(expression)
    # Present whole-number floats without the trailing ".0" for readability.
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{expression} = {result}"


CALCULATOR_TOOL = Tool(
    name="calculator",
    description=(
        "Evaluate a mathematical expression. Supports +, -, *, /, // (integer "
        "division), % (modulo), ** (power), and the functions sqrt(x), "
        "square(x), cube(x), percent(a, b) (a percent of b), abs, round, pow, "
        "sin, cos, tan, log, log10, exp and factorial. Constants pi, e and tau "
        "are available. Examples: '12 * (3 + 4)', 'sqrt(144)', 'square(9)', "
        "'cube(3)', 'percent(15, 200)'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate.",
            }
        },
        "required": ["expression"],
    },
    handler=_calculate,
)

TOOLS = [CALCULATOR_TOOL]
