"""Check that landing-page HTML is rendered through safe Streamlit markdown calls."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_FILES = [
    PROJECT_ROOT / "app.py",
    PROJECT_ROOT / "src" / "landing_page.py",
]
HTML_MARKERS = ("<div", "<section", "<article", "<style", "<span", "<a ", "<footer", "<h1", "<h2", "<p")
FORBIDDEN_OUTPUT_CALLS = {
    "write",
    "text",
    "code",
}


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _literal_text(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value for part in node.values if isinstance(part, ast.Constant) and isinstance(part.value, str))
    return ""


def _contains_html(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in HTML_MARKERS)


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _call_name(node.func)
        first_arg = node.args[0] if node.args else None
        first_text = _literal_text(first_arg) if first_arg is not None else ""

        if call_name in FORBIDDEN_OUTPUT_CALLS and _contains_html(first_text):
            errors.append(
                f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} uses st.{call_name} with an HTML-looking string."
            )

        if call_name == "markdown" and _contains_html(first_text):
            has_unsafe = any(
                keyword.arg == "unsafe_allow_html"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            )
            if not has_unsafe:
                errors.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} renders HTML-looking markdown without unsafe_allow_html=True."
                )

    return errors


def main() -> int:
    errors: list[str] = []
    for path in TARGET_FILES:
        if not path.exists():
            errors.append(f"Missing target file: {path}")
            continue
        errors.extend(validate_file(path))

    if errors:
        print("Landing raw HTML validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Landing raw HTML validation passed.")
    print("Checked files:")
    for path in TARGET_FILES:
        print(f"- {path.relative_to(PROJECT_ROOT)}")
    print("HTML-like blocks are not sent through st.write/st.text/st.code, and markdown HTML uses unsafe_allow_html=True.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
