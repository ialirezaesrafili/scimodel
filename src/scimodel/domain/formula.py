"""Domain abstractions for extensible mathematical formulas and safe AST evaluation."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import numpy.typing as npt


class FormulaSyntaxError(ValueError):
    """Raised when a mathematical formula cannot be parsed or contains forbidden syntax."""


class FormulaEvaluationError(RuntimeError):
    """Raised when evaluation of a mathematical formula fails numerically."""


@dataclass(frozen=True)
class ParameterSpec:
    """Specification of a tunable parameter in a mathematical formula."""

    name: str
    lower_bound: float = 0.0
    upper_bound: float = float("inf")
    initial_guess: float | None = None
    units: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            msg = f"Parameter name '{self.name}' is not a valid identifier."
            raise ValueError(msg)
        if self.lower_bound >= self.upper_bound:
            msg = f"Parameter '{self.name}' lower_bound must be strictly less than upper_bound."
            raise ValueError(msg)


# Whitelist of allowed mathematical unary and binary operations
_ALLOWED_BINOPS: Mapping[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a**b,
}

_ALLOWED_UNARYOPS: Mapping[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}

_ALLOWED_FUNCTIONS: Mapping[str, Callable[..., Any]] = {
    "exp": np.exp,
    "log": np.log,
    "log10": np.log10,
    "sqrt": np.sqrt,
    "sin": np.sin,
    "cos": np.cos,
    "tanh": np.tanh,
    "abs": np.abs,
}


@dataclass(frozen=True)
class ModelFormula:
    """Represents a validated, evaluable scientific model equation."""

    name: str
    expression: str
    parameters: Sequence[ParameterSpec]
    independent_vars: Sequence[str] = ("substrate_conc",)
    dependent_var: str = "reaction_velocity"
    latex_equation: str | None = None
    assumptions: Sequence[str] = field(default_factory=tuple)
    limitations: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.expression.strip():
            msg = "Formula expression must not be empty."
            raise FormulaSyntaxError(msg)
        # Parse and validate AST tree at instantiation time
        self._validate_ast()

    def _validate_ast(self) -> ast.Expression:
        try:
            tree = ast.parse(self.expression.strip(), mode="eval")
        except SyntaxError as exc:
            msg = f"Invalid formula syntax in '{self.expression}': {exc}"
            raise FormulaSyntaxError(msg) from exc

        allowed_names = (
            {p.name for p in self.parameters}
            | set(self.independent_vars)
            | set(_ALLOWED_FUNCTIONS.keys())
        )

        for node in ast.walk(tree):
            if isinstance(node, (ast.Expression, ast.operator, ast.unaryop, ast.expr_context)):
                continue
            if isinstance(node, (ast.Constant, ast.BinOp, ast.UnaryOp, ast.Call)):
                if isinstance(node, ast.BinOp) and type(node.op) not in _ALLOWED_BINOPS:
                    msg = f"Unsupported binary operator in formula: {type(node.op).__name__}"
                    raise FormulaSyntaxError(msg)
                if isinstance(node, ast.UnaryOp) and type(node.op) not in _ALLOWED_UNARYOPS:
                    msg = f"Unsupported unary operator in formula: {type(node.op).__name__}"
                    raise FormulaSyntaxError(msg)
                continue
            if isinstance(node, ast.Name):
                if node.id not in allowed_names:
                    msg = (
                        f"Undefined or forbidden symbol '{node.id}' in formula '{self.expression}'."
                    )
                    raise FormulaSyntaxError(msg)
                continue
            msg = f"Unsupported AST syntax node '{type(node).__name__}' in formula expression."
            raise FormulaSyntaxError(msg)

        return tree

    def evaluate(
        self,
        variable_values: Mapping[str, npt.NDArray[np.float64]],
        parameter_values: Mapping[str, float],
    ) -> npt.NDArray[np.float64]:
        """Safely evaluate the formula against NumPy data arrays without eval()."""
        tree = self._validate_ast()

        # Build symbol table
        context: dict[str, Any] = dict(_ALLOWED_FUNCTIONS)
        for var_name in self.independent_vars:
            if var_name not in variable_values:
                msg = f"Missing value for independent variable '{var_name}'."
                raise FormulaEvaluationError(msg)
            context[var_name] = variable_values[var_name]

        for param in self.parameters:
            if param.name not in parameter_values:
                msg = f"Missing value for parameter '{param.name}'."
                raise FormulaEvaluationError(msg)
            context[param.name] = parameter_values[param.name]

        def _eval_node(node: ast.AST) -> Any:
            if isinstance(node, ast.Expression):
                return _eval_node(node.body)
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name):
                return context[node.id]
            if isinstance(node, ast.BinOp):
                bin_op = _ALLOWED_BINOPS[type(node.op)]
                return bin_op(_eval_node(node.left), _eval_node(node.right))
            if isinstance(node, ast.UnaryOp):
                unary_op = _ALLOWED_UNARYOPS[type(node.op)]
                return unary_op(_eval_node(node.operand))
            if isinstance(node, ast.Call):
                func_node = node.func
                if not isinstance(func_node, ast.Name) or func_node.id not in _ALLOWED_FUNCTIONS:
                    msg = "Only whitelisted mathematical functions are callable."
                    raise FormulaEvaluationError(msg)
                func = _ALLOWED_FUNCTIONS[func_node.id]
                args = [_eval_node(arg) for arg in node.args]
                return func(*args)
            msg = f"Evaluation of AST node {type(node).__name__} is not supported."
            raise FormulaEvaluationError(msg)

        try:
            result = _eval_node(tree)
            return cast(npt.NDArray[np.float64], np.asarray(result, dtype=np.float64))
        except Exception as exc:
            msg = f"Numerical evaluation error in formula '{self.expression}': {exc}"
            raise FormulaEvaluationError(msg) from exc
