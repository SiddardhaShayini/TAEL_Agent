# Security Policy

## Security Overview

**TAEL-Agent** is an autonomous software engineering assistant capable of reading and writing files and executing terminal commands on behalf of the developer.

Because the model operates locally on the developer's system, security and sandboxing are foundational design principles. Defense-in-depth protections are enforced at the runtime level regardless of the model's raw token output.

---

## Supported Versions

| Version | Supported |
| :--- | :---: |
| `v2.0.0-rc1` / `v2.x` | :white_check_mark: |
| `< v2.0.0` (Historical prototypes) | :x: |

---

## Architectural Safeguards

1. **Path Sandboxing (`PathSandbox`):**
   - Strictly confines all file operations (`read_file`, `write_file`, `list_dir`, `search_text`) to the designated project workspace root using canonical path resolution (`os.path.commonpath` in Python and `path.relative` in TypeScript).
   - Directory traversal attempts (e.g. `../../Windows/System32` or `/etc/passwd`) are blocked with a `Security Sandbox Violation`.
   - Access to sensitive credential files (`.env`, `.env.local`, `*.pem`, `*.key`) is blocked by default.

2. **Command Blacklisting (`CommandSandbox`):**
   - Intercepts and blocks destructive commands prior to subprocess creation:
     - Destructive deletes (`rm -rf /`, `del /f /q`, `rmdir /s`, `Remove-Item -Recurse`)
     - Disk formatting (`format`, `mkfs`, `diskpart`, `fdisk`)
     - System power management (`shutdown`, `reboot`, `halt`)
     - Piped remote scripts (`curl ... | bash`, `Invoke-WebRequest ... | iex`)
     - Fork bombs (`:(){ :|:& };:`)
   - All command executions enforce strict process timeout limits (`15s–30s`) and output buffer truncation (`10,000` chars).

3. **Local-First & Zero-Telemetry:**
   - TAEL-Agent runs 100% offline via local `llama.cpp` or local Ollama (`http://127.0.0.1:11434`).
   - No prompts, source code, file contents, or execution outputs are sent to external cloud APIs.

---

## Reporting a Security Vulnerability

If you discover a security vulnerability or sandbox bypass in TAEL-Agent:

1. **Do NOT report it via a public GitHub issue.**
2. Send an email to **siddardhashayini9@gmail.com** with:
   - Description of the vulnerability and attack scenario
   - Minimal proof-of-concept (PoC) prompt or tool payload
   - System environment (OS, Python version, Ollama version)
3. You will receive an acknowledgment within 48 hours.
4. A security advisory and patched release will be coordinated responsibly.
