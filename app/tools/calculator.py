"""Calculator tool — a safe arithmetic evaluator.

Uses Python's ``ast`` to walk a whitelist of nodes instead of ``eval`` so the
model can't execute arbitrary code. Supports + - * / // % ** , unary minus,
parentheses, and a handful of math functions/constants.
"""

from __future__ import annotations

import ast
import math
import operator

from .base import Tool, ToolRegistry

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "floor": math.floor,
    "ceil": math.ceil, "log": math.log, "log10": math.log10, "exp": math.exp,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "pow": math.pow,
    "min": min, "max": max,
}
_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"unsupported function: {node.func.id}")
        return fn(*[_eval(a) for a in node.args])
    raise ValueError(f"unsupported expression element: {type(node).__name__}")


def register(registry: ToolRegistry, config) -> None:
    def calculate(expression: str) -> str:
        try:
            tree = ast.parse(expression, mode="eval")
            result = _eval(tree)
        except ZeroDivisionError:
            return "Error: division by zero."
        except Exception as exc:  # noqa: BLE001
            return f"Error: could not evaluate expression ({exc})."
        # Present clean integers without a trailing .0
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)

    registry.register(
        Tool(
            name="calculator",
            description=(
                "Evaluate a mathematical expression precisely. Supports + - * / "
                "// % ** parentheses and functions like sqrt, log, sin, min, max, "
                "round, plus constants pi and e. Use this instead of doing "
                "arithmetic yourself."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "e.g. '(1299.99 * 3) * 1.08' or 'sqrt(2) * pi'.",
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            handler=calculate,
        )
    )
