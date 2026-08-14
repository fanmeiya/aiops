from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_PROJECT_ROOTS = {"app", "tests", "docs"}
ALLOWED_ROOT_FILES = {
    ".env.example", ".gitignore", "API_COMPATIBILITY_MATRIX.md",
    "AUTOMATION_READINESS.md", "COMPATIBILITY_QUIRKS.md", "Dockerfile",
    "FEATURE_INVENTORY.md", "IMPLEMENTATION_MAPPING.md", "README.md",
    "pyproject.toml",
}


def test_repository_has_only_python_project_roots():
    entries = {path.name for path in ROOT.iterdir() if path.name not in {".git", ".pytest_cache"}}
    assert entries <= PYTHON_PROJECT_ROOTS | ALLOWED_ROOT_FILES


def test_model_runtime_is_langgraph_and_deepseek():
    dependencies = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    runtime = (ROOT / "app/agent/runtime.py").read_text(encoding="utf-8").lower()
    assert '"langgraph' in dependencies
    assert '"openai' in dependencies
    assert "langchain" not in dependencies
    assert "stategraph" in runtime
    assert "deepseek_client" in runtime
