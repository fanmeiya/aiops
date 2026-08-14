from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OBSOLETE_FILES = {
    "JAVA_FEATURE_INVENTORY.md",
    "JAVA_TO_PYTHON_MAPPING.md",
    "docs/intent-recognition-enhancement-design.md",
    ".walicode/output.json",
}
OBSOLETE_MARKERS = (
    "Spring Boot",
    "Spring AI",
    "Google ADK",
    "MyBatis",
    "JSch",
    "walissh-server-domain/src/main/java",
)


def test_obsolete_migration_files_are_absent():
    tracked_paths = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert tracked_paths.isdisjoint(OBSOLETE_FILES)


def test_current_project_docs_only_describe_python_runtime():
    docs = [
        ROOT / "README.md",
        ROOT / "FEATURE_INVENTORY.md",
        ROOT / "IMPLEMENTATION_MAPPING.md",
        ROOT / "API_COMPATIBILITY_MATRIX.md",
        ROOT / "AUTOMATION_READINESS.md",
        ROOT / "COMPATIBILITY_QUIRKS.md",
        ROOT / "docs/intent-recognition-design.md",
    ]
    content = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    for marker in OBSOLETE_MARKERS:
        assert marker not in content
