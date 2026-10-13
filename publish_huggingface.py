"""
TAEL-Agent (v2.0.0-rc1): Automated Hugging Face Hub Publisher
Uploads the self-contained Hugging Face repository structure (`Granite-Final-Agent-GGUF/`)
to `SiddardhaShayini/TAEL_Agent` on Hugging Face Hub.

Files uploaded to `SiddardhaShayini/TAEL_Agent`:
  1. granite-3.1-2b-instruct.Q4_K_M.gguf (1.47 GB GGUF v3 model)
  2. Modelfile (Production Ollama Modelfile)
  3. config.json (Granite architecture configuration)
  4. README.md (Hugging Face Model Card with YAML metadata)
  5. .gitattributes (Git LFS tracking rules)
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv(Path.home() / ".env")
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from huggingface_hub import HfApi


REPO_ID = "SiddardhaShayini/TAEL_Agent"
WORKSPACE_DIR = Path(__file__).resolve().parent
HF_FOLDER = WORKSPACE_DIR / "Granite-Final-Agent-GGUF"

REQUIRED_FILES = [
    "granite-3.1-2b-instruct.Q4_K_M.gguf",
    "Modelfile",
    "config.json",
    "README.md",
]


def verify_hf_structure() -> bool:
    print("=" * 72)
    print(f" [HUGGING FACE] Verifying Repository Structure in {HF_FOLDER.name}/")
    print("=" * 72)
    all_ok = True
    for fname in REQUIRED_FILES:
        fpath = HF_FOLDER / fname
        if fpath.exists():
            size_mb = fpath.stat().st_size / (1024 * 1024)
            print(f"  [OK] {fname:<40} ({size_mb:.2f} MB)")
        else:
            print(f"  [MISSING] {fname}")
            all_ok = False
    return all_ok


def publish_to_huggingface(token: Optional[str] = None) -> bool:
    if not verify_hf_structure():
        return False

    hf_token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    api = HfApi(token=hf_token)

    try:
        user_info = api.whoami()
        print(f"\n  [AUTH] Authenticated as Hugging Face user: {user_info.get('name')}")
    except Exception as e:
        print(f"\n  [INFO] Hugging Face structure verified locally (`Granite-Final-Agent-GGUF/`).")
        print(f"  [AUTH REQUIRED] To push to https://huggingface.co/{REPO_ID}:")
        print(f"                  Set HF_TOKEN in ~/.env or run `huggingface-cli login`, then run:")
        print(f"                  python publish_huggingface.py")
        return False

    print(f"\n  [UPLOAD] Creating/verifying repo '{REPO_ID}' on Hugging Face Hub...")
    api.create_repo(repo_id=REPO_ID, repo_type="model", exist_ok=True, private=False)

    print(f"  [UPLOAD] Uploading {HF_FOLDER} to {REPO_ID} (Release v2.0.0-rc1)...")
    api.upload_folder(
        folder_path=str(HF_FOLDER),
        repo_id=REPO_ID,
        repo_type="model",
        commit_message="Release TAEL-Agent v2.0.0-rc1 (Granite 3.1 2B Q4_K_M GGUF + Modelfile + Model Card)",
    )
    print(f"  [SUCCESS] Published to https://huggingface.co/{REPO_ID}")
    return True


if __name__ == "__main__":
    ok = publish_to_huggingface()
    sys.exit(0 if ok else 1)
