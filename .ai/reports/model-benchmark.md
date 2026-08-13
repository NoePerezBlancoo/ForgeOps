# Local model benchmark

Generated from reproducible Ollama API calls against controlled ForgeOps-oriented prompts.

- Context: 32768 tokens
- Primary: `qwen3-coder:30b`
- Fallback: `devstral-small-2:24b`
- Selection: Fastest model within 0.05 quality points of the best controlled score

## qwen3-coder:30b

Quality: 0.833  
Average speed: 74.39 tok/s

- module_comprehension: score 0.667, 12.6 s, 72.69 tok/s
- test_generation: score 0.5, 2.71 s, 74.74 tok/s
- controlled_bug_fix: score 1.0, 0.79 s, 73.91 tok/s
- instruction_following: score 1.0, 0.27 s, 76.22 tok/s
- tool_calling: score 1.0, 0.62 s, N/A tok/s
## devstral-small-2:24b

Quality: 0.85  
Average speed: 10.31 tok/s

- module_comprehension: score 1.0, 19.9 s, 10.34 tok/s
- test_generation: score 1.0, 11.0 s, 10.25 tok/s
- controlled_bug_fix: score 0.25, 11.37 s, 10.18 tok/s
- instruction_following: score 1.0, 1.5 s, 10.48 tok/s
- tool_calling: score 1.0, 1.55 s, N/A tok/s
