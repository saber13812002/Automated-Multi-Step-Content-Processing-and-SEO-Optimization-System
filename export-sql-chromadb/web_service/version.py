"""Version information for the web service."""
from pathlib import Path


def get_version() -> str:
    """Read version from VERSION file in project root."""
    try:
        # Try to find VERSION file in project root (going up from web_service)
        project_root = Path(__file__).parent.parent.parent
        version_file = project_root / "VERSION"
        
        if version_file.exists():
            with open(version_file, "r", encoding="utf-8") as f:
                version = f.read().strip()
                return version if version else "0.1.0"
        
        # Fallback: try current directory
        version_file = Path("VERSION")
        if version_file.exists():
            with open(version_file, "r", encoding="utf-8") as f:
                version = f.read().strip()
                return version if version else "0.1.0"
        
        return "0.1.0"
    except Exception:
        return "0.1.0"


__version__ = get_version()

