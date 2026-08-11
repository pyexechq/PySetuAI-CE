"""Safe evaluator for LLM routing rule conditions."""

from __future__ import annotations

import ast
import operator
from typing import Any

_COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

_BOOL_OPS = {
    ast.And: all,
    ast.Or: any,
}


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    raw = condition.strip()
    if not raw:
        return False
    if raw.lower() == "default":
        return True

    try:
        tree = ast.parse(raw, mode="eval")
        return bool(_eval_node(tree.body, context))
    except (SyntaxError, TypeError, ValueError, KeyError):
        return False


def _attr_path(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return _attr_path(node.value) + [node.attr]
    raise ValueError("Unsupported attribute expression")


def _resolve(context: dict[str, Any], node: ast.AST) -> Any:
    path = _attr_path(node)
    current: Any = context
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _eval_node(node: ast.AST, context: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in {"true", "True"}:
            return True
        if node.id in {"false", "False"}:
            return False
        return context.get(node.id)
    if isinstance(node, ast.Attribute):
        return _resolve(context, node)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            op_fn = _COMPARE_OPS.get(type(op))
            if op_fn is None:
                raise ValueError("Unsupported comparison operator")
            right = _eval_node(comparator, context)
            if not op_fn(left, right):
                return False
        return True
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(value, context) for value in node.values]
        return _BOOL_OPS[type(node.op)](values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_node(node.operand, context)
    raise ValueError("Unsupported expression")
