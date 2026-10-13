# TAEL V2: Ollama Integration & Troubleshooting Guide

This guide covers common issues, root causes, and step-by-step solutions when deploying and running the **TAEL (`tael-agent`)** model on **Ollama** (specifically optimized for 8GB RAM laptops).

---

## 1. Quick Verification Commands

```powershell
# 1. Run full automated validation & installation suite
python install_ollama_tael.py

# 2. Or run PowerShell one-click installer
.\install_ollama.ps1

# 3. Verify model registration & metadata
ollama show tael-agent

# 4. Run interactive chat in Ollama
ollama run tael-agent

# 5. Run autonomous agent with full workspace tools (Read/Write/Git/Exec)
python tael_agent_runtime.py "Your task here"
```

---

## 2. Common Issues & Solutions

### Issue 1: `Error: could not connect to ollama app, is it running?`
* **Symptom:** Running `ollama list`, `ollama create`, or `ollama run` fails immediately with a connection refused error on `127.0.0.1:11434`.
* **Root Cause:** The Ollama background server daemon is not running.
* **Fix:**
  1. **Windows:** Start the **Ollama** desktop application from the Start Menu, or run the server manually in a terminal:
     ```powershell
     ollama serve
     ```
  2. Verify the service is listening:
     ```powershell
     Invoke-RestMethod -Uri http://localhost:11434/api/tags
     ```

---

### Issue 2: `Error: open ./granite-3.1-2b-instruct.Q4_K_M.gguf: The system cannot find the file specified`
* **Symptom:** Running `ollama create tael-agent -f Granite-Final-Agent-GGUF/Modelfile` from the root workspace folder fails to locate the `.gguf` file.
* **Root Cause:** The `FROM ./granite-3.1-2b-instruct.Q4_K_M.gguf` path inside `Modelfile` is resolved relative to the directory where `Modelfile` resides or the current working directory depending on the Ollama CLI version.
* **Fix:**
  Always run `ollama create` from inside the `Granite-Final-Agent-GGUF` directory, or use the automated installer script:
  ```powershell
  python install_ollama_tael.py
  ```
  Or manually:
  ```powershell
  Push-Location d:\TAEL_V2_Adaptive_AI\Granite-Final-Agent-GGUF
  ollama create tael-agent -f Modelfile
  Pop-Location
  ```

---

### Issue 3: Model Only Prints Code in `ollama run` Instead of Creating Files on Disk
* **Symptom:** When you ask `ollama run tael-agent` to *"create a website in TEMP_TAEL folder"*, it prints bash/HTML code or `<tool_call>` blocks in the terminal instead of creating the files on your filesystem.
* **Root Cause:** Raw `ollama run` is a pure text-generation REPL—it loads the LLM ("Brain") in an isolated sandbox without filesystem or shell tool executors ("Hands").
* **Fix:**
  To execute autonomous file creation, directory inspection, git operations, and terminal verification (like Claude Code / Antigravity / GitHub Copilot), invoke TAEL through the **TAEL Agent Runtime**:
  ```powershell
  python tael_agent_runtime.py "In TEMP_TAEL folder, create a simple static website with html, css, js."
  ```

---

### Issue 4: Out of Memory (OOM) or High RAM Swap on 8GB Laptops
* **Symptom:** Model loading fails with `unable to allocate buffer` or generation slows down to `< 2 tokens/sec` due to disk paging.
* **Root Cause:** Another large LLM (e.g., `llama3.1:8b` or `mistral:latest`) is still loaded in Ollama's memory cache, or `num_ctx` was raised above `4096`.
* **Fix:**
  1. Check currently loaded models in RAM:
     ```powershell
     ollama ps
     ```
  2. Unload any other model from RAM immediately:
     ```powershell
     ollama stop llama3.1:8b
     ```
  3. Keep `PARAMETER num_ctx 4096` in `Modelfile` (requires only ~1.8 GB total RAM alongside the 1.47 GB `Q4_K_M` weights).

---

### Issue 5: Model Continues Generating After Completing Answer or Prints `<|im_end|>`
* **Symptom:** The model repeats itself, simulates follow-up user turns, or outputs raw `<|im_start|>` / `<|im_end|>` tokens.
* **Root Cause:** Missing ChatML stop tokens or mismatched `TEMPLATE` formatting in `Modelfile`.
* **Fix:**
  Ensure the `Modelfile` contains the three mandatory stop parameters:
  ```dockerfile
  PARAMETER stop "<|im_end|>"
  PARAMETER stop "<|im_start|>"
  PARAMETER stop "<|end_of_text|>"
  PARAMETER repeat_penalty 1.05
  ```
  Then rebuild the model using `python install_ollama_tael.py`.

---

### Issue 6: Port `11434` Already in Use (`bind: Only one usage of each socket address is normally permitted`)
* **Symptom:** Running `ollama serve` fails because port `11434` is already bound.
* **Root Cause:** The Ollama tray application is already running in the background.
* **Fix:**
  You do not need to run `ollama serve` if the tray app is active. To find which process owns port `11434`:
  ```powershell
  netstat -ano | findstr :11434
  ```

---

### Issue 7: Slow CPU Inference (`< 8 tokens/sec`)
* **Symptom:** Token generation is slower than the expected `14 - 17 tokens/sec`.
* **Root Cause:** Laptop power plan is set to *Battery Saver*, or thread count exceeds physical CPU cores (causing hyperthreading thrashing).
* **Fix:**
  1. Switch Windows Power Mode to **Best Performance** / plug in AC power.
  2. Set optimal thread count matching physical cores (e.g., 6 threads):
     ```powershell
     $env:OLLAMA_NUM_PARALLEL = "1"
     ```
