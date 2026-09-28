"""Explicit, reproducible model setup. Never downloads from inside an API request."""
import hashlib
from pathlib import Path
import urllib.request

from app.config import settings
from app.services.model_manifest import MODELS, ZOO_REVISION


def download_models(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for model in MODELS.values():
        target = root / model["file"]
        if target.exists():
            with target.open("rb") as existing:
                if hashlib.file_digest(existing, "sha256").hexdigest() == model["sha256"]:
                    print(f"Verified {model['name']} (already present)")
                    continue
        url = f"https://media.githubusercontent.com/media/opencv/opencv_zoo/{ZOO_REVISION}/models/{model['folder']}/{model['file']}"
        partial = target.with_suffix(".download")
        try:
            digest = hashlib.sha256()
            size = 0
            with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > model["size"]:
                        raise ValueError("Model download exceeds expected size")
                    digest.update(chunk)
                    output.write(chunk)
            if size != model["size"] or digest.hexdigest() != model["sha256"]:
                raise ValueError("Model checksum mismatch; file not installed")
            partial.replace(target)
            print(f"Verified {model['name']} {model['version']} ({model['license']})")
        finally:
            partial.unlink(missing_ok=True)


if __name__ == "__main__":
    download_models(settings.model_root)
