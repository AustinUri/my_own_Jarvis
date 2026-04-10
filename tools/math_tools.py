from __future__ import annotations

import ast
import operator as op


_ALLOWED = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
    ast.FloorDiv: op.floordiv,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculate_expression(expression: str) -> str:
    cleaned = expression.strip().replace("^", "**")
    if not cleaned:
        return "No calculation expression was provided."
    try:
        parsed = ast.parse(cleaned, mode="eval")
        result = _eval(parsed.body)
    except Exception:
        return f"I could not calculate '{expression}'."

    if result.is_integer():
        return f"The result is {int(result)}."
    return f"The result is {result:.4f}."
