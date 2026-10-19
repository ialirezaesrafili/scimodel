"""Neural-network surrogate used as a model-agnostic accuracy ceiling.

A small multilayer perceptron (NumPy only, Adam optimizer, early stopping,
ensemble averaging) estimates how much of the target's variance is
*learnable* from the predictors without assuming any equation. Comparing a
closed-form formula's cross-validated R² with this ceiling tells a researcher
whether the formula is missing structure, or whether the remaining error is
mostly measurement noise. The surrogate is a diagnostic, never the reported
scientific model.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

FloatArray: TypeAlias = npt.NDArray[np.float64]


@dataclass(frozen=True)
class NeuralSettings:
    hidden_layers: tuple[int, ...] = (32, 32)
    learning_rate: float = 0.01
    weight_decay: float = 1e-4
    max_epochs: int = 3000
    patience: int = 200
    ensemble: int = 3
    folds: int = 5
    seed: int = 0
    time_budget: float = 20.0


class MLPRegressor:
    """Fully connected tanh network trained with full-batch Adam."""

    def __init__(self, settings: NeuralSettings, rng: np.random.Generator) -> None:
        self.settings = settings
        self.rng = rng
        self.weights: list[FloatArray] = []
        self.biases: list[FloatArray] = []
        self._x_mean = np.zeros(1)
        self._x_std = np.ones(1)
        self._y_mean = 0.0
        self._y_std = 1.0

    def fit(self, x: FloatArray, y: FloatArray) -> MLPRegressor:
        self._x_mean, self._x_std = x.mean(axis=0), x.std(axis=0)
        self._x_std[self._x_std == 0] = 1.0
        self._y_mean, self._y_std = float(y.mean()), float(y.std()) or 1.0
        xs = (x - self._x_mean) / self._x_std
        ys = ((y - self._y_mean) / self._y_std)[:, None]

        order = self.rng.permutation(len(xs))
        n_val = max(1, len(xs) // 5) if len(xs) >= 10 else 0
        val_idx, train_idx = order[:n_val], order[n_val:]
        x_train, y_train = xs[train_idx], ys[train_idx]
        x_val, y_val = (xs[val_idx], ys[val_idx]) if n_val else (x_train, y_train)

        sizes = [xs.shape[1], *self.settings.hidden_layers, 1]
        self.weights = [
            self.rng.normal(0.0, np.sqrt(1.0 / fan_in), size=(fan_in, fan_out))
            for fan_in, fan_out in zip(sizes[:-1], sizes[1:], strict=True)
        ]
        self.biases = [np.zeros(fan_out) for fan_out in sizes[1:]]
        params = [*self.weights, *self.biases]
        first_moment = [np.zeros_like(p) for p in params]
        second_moment = [np.zeros_like(p) for p in params]
        best_loss, best_params, stale = np.inf, [p.copy() for p in params], 0
        beta1, beta2, eps = 0.9, 0.999, 1e-8

        for epoch in range(1, self.settings.max_epochs + 1):
            grads = self._gradients(x_train, y_train)
            for i, (param, grad) in enumerate(zip(params, grads, strict=True)):
                first_moment[i] = beta1 * first_moment[i] + (1 - beta1) * grad
                second_moment[i] = beta2 * second_moment[i] + (1 - beta2) * grad**2
                m_hat = first_moment[i] / (1 - beta1**epoch)
                v_hat = second_moment[i] / (1 - beta2**epoch)
                param -= self.settings.learning_rate * m_hat / (np.sqrt(v_hat) + eps)
            loss = float(np.mean((self._forward(x_val)[-1] - y_val) ** 2))
            if loss < best_loss - 1e-7:
                best_loss, best_params, stale = loss, [p.copy() for p in params], 0
            else:
                stale += 1
                if stale > self.settings.patience:
                    break
        for param, best in zip(params, best_params, strict=True):
            param[...] = best
        return self

    def predict(self, x: FloatArray) -> FloatArray:
        xs = (x - self._x_mean) / self._x_std
        return self._forward(xs)[-1][:, 0] * self._y_std + self._y_mean

    def _forward(self, x: FloatArray) -> list[FloatArray]:
        activations = [x]
        for layer, (weight, bias) in enumerate(zip(self.weights, self.biases, strict=True)):
            z = activations[-1] @ weight + bias
            activations.append(z if layer == len(self.weights) - 1 else np.tanh(z))
        return activations

    def _gradients(self, x: FloatArray, y: FloatArray) -> list[FloatArray]:
        activations = self._forward(x)
        delta = 2.0 * (activations[-1] - y) / len(x)
        weight_grads: list[FloatArray] = []
        bias_grads: list[FloatArray] = []
        for layer in range(len(self.weights) - 1, -1, -1):
            weight_grads.insert(
                0, activations[layer].T @ delta + self.settings.weight_decay * self.weights[layer]
            )
            bias_grads.insert(0, delta.sum(axis=0))
            if layer:
                delta = (delta @ self.weights[layer].T) * (1.0 - activations[layer] ** 2)
        return [*weight_grads, *bias_grads]


class NeuralBaseline:
    """Cross-validated ensemble MLP that reports a learnable-signal ceiling."""

    def __init__(self, settings: NeuralSettings | None = None) -> None:
        self.settings = settings or NeuralSettings()

    def evaluate(self, variables: dict[str, FloatArray], y: FloatArray) -> dict[str, Any]:
        started = time.monotonic()
        x = np.column_stack([variables[name] for name in variables])
        n = len(y)
        if n < 10:
            return {"status": "skipped", "reason": "At least 10 observations are required."}
        rng = np.random.default_rng(self.settings.seed)
        folds = _folds(n, min(self.settings.folds, n), rng)
        predictions = np.empty_like(y)
        deadline = started + self.settings.time_budget
        for test in folds:
            if time.monotonic() > deadline:
                return {
                    "status": "skipped",
                    "reason": f"Time budget of {self.settings.time_budget:.0f}s was exceeded.",
                }
            train = np.setdiff1d(np.arange(n), test)
            members = [
                MLPRegressor(self.settings, rng).fit(x[train], y[train])
                for _ in range(self.settings.ensemble)
            ]
            predictions[test] = np.mean([m.predict(x[test]) for m in members], axis=0)
        sse = float(np.sum((y - predictions) ** 2))
        sst = float(np.sum((y - y.mean()) ** 2))
        return {
            "status": "ok",
            "architecture": f"MLP {list(self.settings.hidden_layers)} tanh, Adam, "
            f"ensemble of {self.settings.ensemble}",
            "cv_folds": len(folds),
            "cv_rmse": float(np.sqrt(sse / n)),
            "cv_r_squared": 1.0 - sse / sst if sst > 0 else float("nan"),
            "seconds": round(time.monotonic() - started, 3),
        }


def _folds(n: int, k: int, rng: np.random.Generator) -> Sequence[npt.NDArray[np.intp]]:
    order = rng.permutation(n)
    return [fold for fold in np.array_split(order, k) if len(fold)]
