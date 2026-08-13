# Local model benchmark

Generated from reproducible Ollama API calls against controlled ForgeOps-oriented prompts.

- Context: 32768 tokens
- Primary: `qwen3-coder:30b`
- Fallback: `devstral-small-2:24b`
- Selection: Throughput selects the primary model; controlled quality selects the precision fallback

## qwen3-coder:30b

Quality: 0.833

Average speed: 72.75 tok/s

Relative speed: 6.76x

- module_comprehension: score 0.667, 14.49 s, 70.58 tok/s
- test_generation: score 0.5, 2.8 s, 71.81 tok/s
- controlled_bug_fix: score 1.0, 0.8 s, 72.58 tok/s
- instruction_following: score 1.0, 0.29 s, 76.03 tok/s
- tool_calling: score 1.0, 0.64 s, N/A tok/s
## devstral-small-2:24b

Quality: 0.85

Average speed: 10.76 tok/s

Relative speed: 1.0x

- module_comprehension: score 1.0, 19.99 s, 10.5 tok/s
- test_generation: score 1.0, 10.72 s, 10.53 tok/s
- controlled_bug_fix: score 0.25, 11.02 s, 10.52 tok/s
- instruction_following: score 1.0, 1.43 s, 11.48 tok/s
- tool_calling: score 1.0, 1.57 s, N/A tok/s
