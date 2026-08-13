# Local model benchmark

Generated from reproducible Ollama API calls against controlled ForgeOps-oriented prompts.

- Context: 32768 tokens
- Primary: `devstral-small-2:24b`
- Fallback: `qwen3-coder:30b`
- Selection: Highest controlled quality score; speed breaks ties

## devstral-small-2:24b

Quality: 0.85

Average speed: 10.47 tok/s

- module_comprehension: score 1.0, 21.05 s, 10.27 tok/s
- test_generation: score 1.0, 11.02 s, 10.26 tok/s
- controlled_bug_fix: score 0.25, 11.21 s, 10.34 tok/s
- instruction_following: score 1.0, 1.47 s, 11.0 tok/s
- tool_calling: score 1.0, 1.57 s, N/A tok/s
## qwen3-coder:30b

Quality: 0.833

Average speed: 74.15 tok/s

- module_comprehension: score 0.667, 12.42 s, 72.45 tok/s
- test_generation: score 0.5, 2.74 s, 73.43 tok/s
- controlled_bug_fix: score 1.0, 0.8 s, 73.69 tok/s
- instruction_following: score 1.0, 0.28 s, 77.03 tok/s
- tool_calling: score 1.0, 0.63 s, N/A tok/s
