#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL V2: Ollama Integration, Validation & Installation Script
-------------------------------------------------------------
Automates and verifies the complete Ollama deployment pipeline:
  1. Validates GGUF binary header (Magic bytes, GGUF version, tensor count, size)
  2. Validates Modelfile syntax, directives, template, and parameters
  3. Checks Ollama CLI & daemon availability
  4. Executes and verifies `ollama create tael-agent -f Modelfile`
  5. Executes and verifies `ollama run tael-agent` with live prompts
"""

import os
import sys
import time
import json
import struct
import hashlib
import re
import subprocess
from typing import Dict, Any, Tuple

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

WORKSPACE_DIR = r"d:\TAEL_V2_Adaptive_AI"
GGUF_DIR = os.path.join(WORKSPACE_DIR, "Granite-Final-Agent-GGUF")
GGUF_PATH = os.path.join(GGUF_DIR, "granite-3.1-2b-instruct.Q4_K_M.gguf")
MODELFILE_PATH = os.path.join(GGUF_DIR, "Modelfile")
MODEL_NAME = "tael-agent"
REPORT_PATH = os.path.join(WORKSPACE_DIR, "ollama_verification_report.json")


class OllamaInstallerValidator:
    """End-to-end validator and installer for TAEL on Ollama."""

    def __init__(self):
        self.report: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_name": MODEL_NAME,
            "gguf_validation": {},
            "modelfile_validation": {},
            "ollama_environment": {},
            "ollama_create": {},
            "ollama_run_tests": [],
            "overall_success": False,
        }

    # --------------------------------------------------------------------------
    # 1. Validate GGUF Binary
    # --------------------------------------------------------------------------

    def validate_gguf(self) -> bool:
        print("=" * 72)
        print(" [STEP 1/5] Validating GGUF Model Binary...")
        print("=" * 72)

        if not os.path.exists(GGUF_PATH):
            print(f" [FAIL] GGUF file not found at: {GGUF_PATH}")
            self.report["gguf_validation"] = {"valid": False, "error": "File not found"}
            return False

        file_size = os.path.getsize(GGUF_PATH)
        size_mb = file_size / (1024 * 1024)
        size_gb = file_size / (1024 * 1024 * 1024)

        try:
            with open(GGUF_PATH, "rb") as f:
                header = f.read(24)
                if len(header) < 24:
                    raise ValueError("File too small to contain a valid 24-byte GGUF header.")

                magic, version, tensor_count, metadata_kv_count = struct.unpack("<4sIQQ", header)
                magic_str = magic.decode("ascii", errors="replace")

                # Compute fast SHA-256 fingerprint of first 16 MB for quick verification
                f.seek(0)
                sample_chunk = f.read(16 * 1024 * 1024)
                partial_sha256 = hashlib.sha256(sample_chunk).hexdigest()

            is_valid = (
                magic_str == "GGUF"
                and version in (2, 3)
                and tensor_count > 100
                and file_size > 1_000_000_000
            )

            self.report["gguf_validation"] = {
                "valid": is_valid,
                "path": GGUF_PATH,
                "size_bytes": file_size,
                "size_mb": round(size_mb, 2),
                "size_gb": round(size_gb, 2),
                "magic": magic_str,
                "gguf_version": version,
                "tensor_count": tensor_count,
                "metadata_kv_count": metadata_kv_count,
                "head_16mb_sha256": partial_sha256,
            }

            if is_valid:
                print(f"  [PASS] File Path:        {GGUF_PATH}")
                print(f"  [PASS] File Size:        {file_size:,} bytes ({size_mb:.2f} MB / {size_gb:.2f} GiB)")
                print(f"  [PASS] Magic Header:     '{magic_str}' (Version {version})")
                print(f"  [PASS] Tensor Count:     {tensor_count} tensors")
                print(f"  [PASS] Metadata Pairs:   {metadata_kv_count} KV entries")
                print(f"  [PASS] Header SHA-256:   {partial_sha256[:32]}...")
                return True
            else:
                print(f"  [FAIL] Invalid GGUF header values: magic={magic_str}, version={version}")
                return False

        except Exception as e:
            print(f"  [FAIL] Error inspecting GGUF binary: {e}")
            self.report["gguf_validation"] = {"valid": False, "error": str(e)}
            return False

    # --------------------------------------------------------------------------
    # 2. Validate Modelfile
    # --------------------------------------------------------------------------

    def validate_modelfile(self) -> bool:
        print("\n" + "=" * 72)
        print(" [STEP 2/5] Validating Ollama Modelfile...")
        print("=" * 72)

        if not os.path.exists(MODELFILE_PATH):
            print(f"  [FAIL] Modelfile not found at: {MODELFILE_PATH}")
            self.report["modelfile_validation"] = {"valid": False, "error": "Modelfile not found"}
            return False

        with open(MODELFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Check FROM directive
        from_match = re.search(r"^FROM\s+(.+)$", content, re.MULTILINE)
        from_target = from_match.group(1).strip() if from_match else None
        resolved_from = os.path.normpath(os.path.join(GGUF_DIR, from_target)) if from_target else ""
        from_exists = os.path.exists(resolved_from)

        # Check TEMPLATE directive
        has_template = "TEMPLATE" in content and "<|im_start|>" in content and "<|im_end|>" in content

        # Check PARAMETER directives
        params = re.findall(r"^PARAMETER\s+(\S+)\s+(.+)$", content, re.MULTILINE)
        param_keys = [p[0] for p in params]
        has_stop = "stop" in param_keys
        has_temp = "temperature" in param_keys
        has_ctx = "num_ctx" in param_keys

        # Check SYSTEM directive
        has_system = "SYSTEM" in content and "TAEL" in content

        is_valid = all([from_exists, has_template, has_stop, has_temp, has_system])

        self.report["modelfile_validation"] = {
            "valid": is_valid,
            "path": MODELFILE_PATH,
            "from_target": from_target,
            "resolved_gguf_exists": from_exists,
            "has_chatml_template": has_template,
            "parameters": [{k: v} for k, v in params],
            "has_system_prompt": has_system,
        }

        if is_valid:
            print(f"  [PASS] Modelfile Path:   {MODELFILE_PATH}")
            print(f"  [PASS] FROM Directive:   '{from_target}' (Verified on disk)")
            print(f"  [PASS] ChatML Template:  Present (<|im_start|> / <|im_end|>)")
            print(f"  [PASS] Parameters:       {len(params)} configured ({', '.join(dict.fromkeys(param_keys))})")
            print(f"  [PASS] SYSTEM Prompt:    Present & verified")
            return True
        else:
            print(f"  [FAIL] Modelfile validation failed: {self.report['modelfile_validation']}")
            return False

    # --------------------------------------------------------------------------
    # 3. Check Ollama Environment
    # --------------------------------------------------------------------------

    def check_ollama_environment(self) -> bool:
        print("\n" + "=" * 72)
        print(" [STEP 3/5] Checking Ollama CLI & Daemon Status...")
        print("=" * 72)

        try:
            ver_res = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version_str = ver_res.stdout.strip() or ver_res.stderr.strip()

            list_res = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            daemon_running = list_res.returncode == 0

            self.report["ollama_environment"] = {
                "cli_available": ver_res.returncode == 0,
                "version": version_str,
                "daemon_running": daemon_running,
            }

            if daemon_running:
                print(f"  [PASS] Ollama Version:   {version_str}")
                print("  [PASS] Ollama Daemon:    Online and responding")
                return True
            else:
                print(f"  [FAIL] Ollama daemon not responding: {list_res.stderr}")
                return False

        except Exception as e:
            print(f"  [FAIL] Failed to execute ollama CLI: {e}")
            self.report["ollama_environment"] = {"cli_available": False, "error": str(e)}
            return False

    # --------------------------------------------------------------------------
    # 4. Verify `ollama create`
    # --------------------------------------------------------------------------

    def verify_ollama_create(self) -> bool:
        print("\n" + "=" * 72)
        print(f" [STEP 4/5] Running & Verifying `ollama create {MODEL_NAME} -f Modelfile`...")
        print("=" * 72)

        t0 = time.time()
        try:
            create_res = subprocess.run(
                ["ollama", "create", MODEL_NAME, "-f", "Modelfile"],
                cwd=GGUF_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            elapsed = time.time() - t0

            # Verify model appears in `ollama show`
            show_res = subprocess.run(
                ["ollama", "show", MODEL_NAME],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )

            success = create_res.returncode == 0 and show_res.returncode == 0

            self.report["ollama_create"] = {
                "success": success,
                "model_name": MODEL_NAME,
                "duration_sec": round(elapsed, 2),
                "stdout": create_res.stdout.strip(),
                "show_info": show_res.stdout.strip(),
            }

            if success:
                print(f"  [PASS] `ollama create {MODEL_NAME}` succeeded in {elapsed:.2f}s")
                print("  [PASS] Model metadata (`ollama show`):")
                for line in show_res.stdout.strip().splitlines()[:12]:
                    print(f"         {line}")
                return True
            else:
                print(f"  [FAIL] `ollama create` failed (code {create_res.returncode}): {create_res.stderr}")
                return False

        except Exception as e:
            print(f"  [FAIL] Exception during `ollama create`: {e}")
            self.report["ollama_create"] = {"success": False, "error": str(e)}
            return False

    # --------------------------------------------------------------------------
    # 5. Verify `ollama run`
    # --------------------------------------------------------------------------

    def verify_ollama_run(self) -> bool:
        print("\n" + "=" * 72)
        print(f" [STEP 5/5] Verifying `ollama run {MODEL_NAME}` with Live Prompts...")
        print("=" * 72)

        test_prompts = [
            {
                "id": "identity_check",
                "prompt": "State your name and primary role in one concise sentence.",
                "expected_keywords": ["tael", "assistant", "software", "coding", "ai", "engineer"],
            },
            {
                "id": "python_coding_check",
                "prompt": "Write a Python function `is_palindrome(s: str) -> bool` that returns True if s is a palindrome. Output only the code.",
                "expected_keywords": ["def ", "is_palindrome", "return", "[::-1]"],
            },
        ]

        all_passed = True
        for item in test_prompts:
            pid = item["id"]
            prompt = item["prompt"]
            print(f"\n  --> Running Test [{pid}]: \"{prompt}\"")
            t0 = time.time()

            try:
                run_res = subprocess.run(
                    ["ollama", "run", MODEL_NAME, prompt],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=90,
                )
                elapsed = time.time() - t0
                # Strip ANSI escape codes from terminal output
                raw_out = run_res.stdout or ""
                clean_out = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]+[hl]|\r", "", raw_out).strip()

                matched = any(kw in clean_out.lower() for kw in item["expected_keywords"])
                passed = run_res.returncode == 0 and len(clean_out) > 5 and matched

                self.report["ollama_run_tests"].append({
                    "id": pid,
                    "prompt": prompt,
                    "response": clean_out,
                    "latency_sec": round(elapsed, 2),
                    "passed": passed,
                })

                if passed:
                    print(f"      [PASS] Response received in {elapsed:.2f}s:")
                    preview = clean_out.replace("\n", " ")[:120]
                    print(f"      Output: {preview}...")
                else:
                    print(f"      [FAIL] Unexpected output or non-zero exit ({run_res.returncode}): {clean_out[:100]}")
                    all_passed = False

            except Exception as e:
                print(f"      [FAIL] Exception running prompt '{pid}': {e}")
                self.report["ollama_run_tests"].append({
                    "id": pid,
                    "prompt": prompt,
                    "error": str(e),
                    "passed": False,
                })
                all_passed = False

        return all_passed

    # --------------------------------------------------------------------------
    # Master Pipeline Runner
    # --------------------------------------------------------------------------

    def run_pipeline(self) -> bool:
        s1 = self.validate_gguf()
        s2 = self.validate_modelfile()
        s3 = self.check_ollama_environment()
        s4 = self.verify_ollama_create() if (s1 and s2 and s3) else False
        s5 = self.verify_ollama_run() if s4 else False

        self.report["overall_success"] = all([s1, s2, s3, s4, s5])

        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)

        print("\n" + "=" * 72)
        status_str = "SUCCESS - ALL 5 STAGES PASSED" if self.report["overall_success"] else "FAILED"
        print(f" [OLLAMA INTEGRATION SUMMARY] Status: {status_str}")
        print(f" [REPORT SAVED] {REPORT_PATH}")
        print("=" * 72 + "\n")
        return self.report["overall_success"]


if __name__ == "__main__":
    installer = OllamaInstallerValidator()
    ok = installer.run_pipeline()
    sys.exit(0 if ok else 1)
