# Project Rules - 5.1 AutoMaster

These are the project-specific engineering rules derived from the global DOGE Mode Principles. All AI agents MUST follow these to ensure system integrity.

## 1. Zero-Defect Code Generation
- **No Placeholders**: Never output `// ... existing code ...`. Always provide the full functional block.
- **Bracket Integrity**: Double-verify all `{}`, `[]`, `()` closures.

## 2. Full Restart Protocol (MANDATORY)
**YOU MUST RESTART THE SERVER AFTER ANY BACKEND CHANGE.**
The running Python process uses cached modules and will NOT pick up your edits without a hard restart.

### Restart Procedure
```powershell
# Kill old server + clear cache + restart
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item -Recurse -Force "core\pipeline\__pycache__" -ErrorAction SilentlyContinue
$env:PYTHONPATH='.'; python backend/main.py
```

### Protocol Requirements
1. **ALWAYS kill the old process** before starting a new one.
2. **ALWAYS clear `__pycache__`** to force the runtime to pick up changes.
3. **NEVER tell the user to "just refresh the browser"** after backend changes — the server must restart first.
4. **The Mandatory Phrase**: After restarting, you MUST tell the user: 
   > **"Server restarted — hard-refresh the browser (Ctrl+Shift+R) and run again."**

## 3. API Data Synchronization
- **Zero-Static UI Rule**: The frontend (`export.js`, `pipeline.js`) MUST NEVER hardcode values that the backend is responsible for generating (like output file names or dynamic sizes).
- **Explicit Propagation Chain**: 
  1. **Source**: Add data to backend context.
  2. **Transport**: Define in Pydantic API response model.
  3. **Destination**: Ensure frontend JS reads the dynamic payload.

## 4. Hardware-First Reasoning
- **Memory Awareness**: Standardize on **8B tier** models (Q8) to avoid disk swapping on 16GB systems.
- **Fail-Fast**: Stop processing immediately if VRAM usage exceeds 90% or RAM < 1GB.

---
**Last Updated**: March 23, 2026
**Central Authority**: See `Obsidian Vault/OpenClaw-Memory/Instructions/Rules.md`
