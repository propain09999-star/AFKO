#!/usr/bin/env python3
"""
Generic invariant checker. Reads contracts/invariants.yml and validates
actual pipeline output (JSON) against every rule, regardless of whether
anything crashed. A value can be perfectly "successful" by every log
and exit code and still violate an invariant — that's the case this
exists to catch.

Usage:
    python check_invariants.py --output actual_output.json --contract contracts/invariants.yml

Exit code 1 if any "critical" severity invariant fails (for CI gating).
Exit code 0 otherwise — "high"/lower severity failures are reported
but don't block by default; tune to taste.
"""
import argparse
import json
import sys
import yaml

# Deliberately tiny, safe expression evaluator — NOT eval(). Only
# these operators are supported, on purpose, so a rule expression
# can never do anything beyond compare values.
import ast
import operator

ALLOWED_OPS = {
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
    ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b,
}


def safe_eval(expr, context):
    """Evaluates a restricted boolean expression like '0 <= value <= 1'."""
    tree = ast.parse(expr, mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval(comparator)
                fn = ALLOWED_OPS.get(type(op))
                if fn is None:
                    raise ValueError(f"Unsupported operator: {op}")
                result = result and fn(left, right)
                left = right
            return result
        if isinstance(node, ast.BoolOp):
            values = [_eval(v) for v in node.values]
            fn = ALLOWED_OPS[type(node.op)]
            out = values[0]
            for v in values[1:]:
                out = fn(out, v)
            return out
        if isinstance(node, ast.Name):
            if node.id == "true":
                return True
            if node.id == "false":
                return False
            if node.id == "null":
                return None
            return context.get(node.id)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "len":
            return len(_eval(node.args[0]))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not _eval(node.operand)
        if isinstance(node, ast.Compare) is False and isinstance(node, ast.Attribute):
            raise ValueError("Attribute access not permitted in rules")
        raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    return _eval(tree)


def get_field(obj, dot_path):
    """Resolves a dot-path like 'a.b.c' against nested JSON."""
    parts = dot_path.split(".")
    current = obj
    for p in parts:
        if isinstance(current, dict) and p in current:
            current = current[p]
        else:
            return None
    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Path to actual pipeline output JSON")
    parser.add_argument("--contract", default="contracts/invariants.yml")
    args = parser.parse_args()

    with open(args.output) as f:
        data = json.load(f)
    with open(args.contract) as f:
        contract = yaml.safe_load(f)

    failures = []
    for inv in contract.get("invariants", []):
        depends_on = inv.get("depends_on")
        if depends_on:
            try:
                if not safe_eval(depends_on, data):
                    continue  # precondition not met, skip this invariant
            except Exception:
                pass  # if depends_on itself can't evaluate, fall through to checking anyway

        value = get_field(data, inv["field"])
        context = dict(data)
        context["value"] = value

        try:
            passed = safe_eval(inv["rule"], context)
        except Exception as e:
            passed = False
            inv = {**inv, "eval_error": str(e)}

        if not passed:
            failures.append(inv)

    if not failures:
        print("All invariants satisfied.")
        return

    print(f"{len(failures)} invariant(s) violated:\n")
    critical_failure = False
    for f in failures:
        sev = f.get("severity", "unknown")
        print(f"  [{sev.upper()}] {f['name']}: {f.get('description', '')}")
        if "eval_error" in f:
            print(f"      (evaluation error: {f['eval_error']})")
        if sev == "critical":
            critical_failure = True

    if critical_failure:
        sys.exit(1)


if __name__ == "__main__":
    main()
