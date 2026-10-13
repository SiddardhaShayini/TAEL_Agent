## Description
Briefly describe the changes introduced by this pull request.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] New sandboxed tool in `tael_tools`
- [ ] Improvement to Dynamic Task Router heuristics
- [ ] Improvement to VS Code Extension
- [ ] Documentation update

## Checklist
- [ ] My code follows the code style and conventions of this project.
- [ ] I have added type hints and docstrings where appropriate.
- [ ] I have updated documentation accordingly.
- [ ] All automated unit tests pass locally:
  - `python test_tool_system.py`
  - `python test_router.py`
  - `python test_memory_system.py`
  - `cd tael-vscode-extension && npm test`
- [ ] I have verified sandboxing policies (`PathSandbox` / `CommandSandbox`) remain uncompromised.
