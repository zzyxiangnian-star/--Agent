from __future__ import annotations

import ast
import contextlib
import io
import multiprocessing as mp
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


class SandboxSecurityError(ValueError):
    pass


class SandboxExecutionError(RuntimeError):
    pass


class SandboxTimeoutError(TimeoutError):
    pass


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    result_json: dict[str, Any]
    artifact_paths: list[str]
    duration_ms: int


FORBIDDEN_IMPORTS = {
    "os", "sys", "subprocess", "socket", "requests", "urllib", "pathlib",
    "shutil", "glob", "pickle", "dill", "ctypes", "multiprocessing",
}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input"}
FORBIDDEN_ATTRS = {"system", "popen", "remove", "unlink", "rmdir", "mkdir", "rename", "replace"}


def validate_code(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise SandboxSecurityError(f"Syntax error: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name.split(".")[0] for alias in getattr(node, "names", [])]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module.split(".")[0])
            blocked = sorted(set(names) & FORBIDDEN_IMPORTS)
            if blocked:
                raise SandboxSecurityError(f"Forbidden import: {', '.join(blocked)}")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                raise SandboxSecurityError(f"Forbidden call: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRS:
                raise SandboxSecurityError(f"Forbidden attribute call: {node.func.attr}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise SandboxSecurityError("Dunder attribute access is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise SandboxSecurityError("Dunder names are not allowed")


def execute_pandas_code(code: str, df: pd.DataFrame, artifact_dir: Path, timeout_seconds: int = 8) -> SandboxResult:
    validate_code(code)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    queue: mp.Queue = mp.Queue()
    start = time.perf_counter()
    process = mp.Process(target=_worker, args=(code, df, str(artifact_dir), queue))
    process.start()
    process.join(timeout_seconds)
    duration_ms = int((time.perf_counter() - start) * 1000)
    if process.is_alive():
        process.terminate()
        process.join(2)
        raise SandboxTimeoutError(f"Code execution exceeded {timeout_seconds}s")
    if queue.empty():
        raise SandboxExecutionError("Sandbox process exited without result")
    payload = queue.get()
    if payload["status"] == "error":
        raise SandboxExecutionError(payload["stderr"])
    payload.pop("status", None)
    payload["duration_ms"] = duration_ms
    return SandboxResult(**payload)


def _worker(code: str, df: pd.DataFrame, artifact_dir: str, queue: mp.Queue) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    artifacts: list[str] = []
    artifact_path = Path(artifact_dir).resolve()

    def save_chart(filename: str = "chart.png") -> str:
        clean = Path(filename).name
        if not clean.lower().endswith(".png"):
            clean += ".png"
        target = artifact_path / clean
        import matplotlib.pyplot as plt

        plt.tight_layout()
        plt.savefig(target, dpi=150, bbox_inches="tight")
        plt.close()
        artifacts.append(str(target))
        return str(target)

    env: dict[str, Any] = {
        "__builtins__": {
            "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict, "enumerate": enumerate,
            "float": float, "int": int, "len": len, "list": list, "max": max, "min": min,
            "print": print, "range": range, "round": round, "set": set, "sorted": sorted,
            "str": str, "sum": sum, "tuple": tuple, "zip": zip,
        },
        "pd": pd,
        "df": df.copy(),
        "save_chart": save_chart,
    }
    try:
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns

        env.update({"np": np, "plt": plt, "sns": sns})
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(compile(code, "<sandbox>", "exec"), env)
        result = env.get("result", {})
        if isinstance(result, pd.DataFrame):
            result = {"data": result.head(100).to_dict("records")}
        elif not isinstance(result, dict):
            result = {"value": str(result)}
        queue.put(
            {
                "status": "ok",
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "result_json": _json_safe(result),
                "artifact_paths": artifacts,
                "duration_ms": 0,
            }
        )
    except Exception as exc:
        queue.put(
            {
                "status": "error",
                "stdout": stdout.getvalue(),
                "stderr": f"{type(exc).__name__}: {exc}",
                "result_json": {},
                "artifact_paths": artifacts,
                "duration_ms": 0,
            }
        )


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
