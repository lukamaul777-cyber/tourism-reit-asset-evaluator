"""Final deployment readiness checks for Tourism REIT Asset Evaluator."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_data_files import validate_data_files
from scripts.validate_project_config import validate_project_config


REQUIRED_FOLDERS = [
    "config",
    "data",
    "docs",
    "pages",
    "src",
    "reports",
]

REQUIRED_APP_FILES = [
    "app.py",
    "requirements.txt",
    "README.md",
]

KEY_BACKEND_MODULES = [
    "src.gatekeeper",
    "src.scoring_model",
    "src.reliability_validity",
    "src.scenario_simulator",
    "src.report_generator",
    "src.chart_utils",
    "src.data_loader",
]


def check_required_folders() -> list[str]:
    """Return missing deployment-critical folders."""
    return [
        folder
        for folder in REQUIRED_FOLDERS
        if not (PROJECT_ROOT / folder).is_dir()
    ]


def check_required_files() -> list[str]:
    """Return missing deployment-critical files."""
    return [
        file_name
        for file_name in REQUIRED_APP_FILES
        if not (PROJECT_ROOT / file_name).is_file()
    ]


def check_backend_imports() -> list[str]:
    """Return backend modules that cannot be imported."""
    errors: list[str] = []
    for module_name in KEY_BACKEND_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - CLI diagnostic path
            errors.append(f"{module_name}: {exc}")
    return errors


def print_check(label: str, errors: list[str]) -> bool:
    """Print one check result and return whether it passed."""
    if errors:
        print(f"[FAIL] {label}")
        for error in errors:
            print(f"  - {error}")
        return False

    print(f"[PASS] {label}")
    return True


def main() -> int:
    """Run final deployment readiness checks."""
    print("Tourism REIT Asset Evaluator final deployment check")
    print("=" * 56)

    checks = [
        ("Configuration validation", validate_project_config()),
        ("Data validation", validate_data_files()),
        ("Required folders", check_required_folders()),
        ("Required app files", check_required_files()),
        ("Backend module imports", check_backend_imports()),
    ]

    passed = 0
    for label, errors in checks:
        if print_check(label, errors):
            passed += 1

    total = len(checks)
    print("=" * 56)
    if passed == total:
        print(f"Final check passed: {passed}/{total} checks succeeded.")
        return 0

    print(f"Final check failed: {passed}/{total} checks succeeded.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
