# Hardware and development environment

Detected on 2026-08-13. This report intentionally omits usernames, serial numbers, network addresses and credentials.

| Component | Detected |
| --- | --- |
| Operating system | Windows 11 Pro, build 26200 |
| CPU | AMD Ryzen 7 9800X3D, 8 cores / 16 logical processors |
| RAM | 31.1 GB usable |
| Primary GPU | NVIDIA GeForce RTX 5080 |
| VRAM | 16,303 MB |
| NVIDIA driver | 596.49 |
| Integrated GPU | AMD Radeon Graphics |
| Local disk | 3,814.4 GB total / 3,045.2 GB free at audit time |
| WSL | 2.7.3.0, kernel 6.6.114.1 |
| Linux distributions | Ubuntu 24.04 LTS and Docker Desktop internal distribution |
| Docker Desktop | 29.5.2, Linux engine, 16 CPUs / 15.2 GB assigned memory |
| Python | 3.14.5 host; agent image uses 3.12 |
| Node.js | 24.16.0 host; agent image uses 22 |
| Git | 2.55.0.windows.3 |
| GitHub CLI | 2.93.0 |
| PowerShell | Windows PowerShell 5.1 |
| Ollama | 0.32.9 |

The 16 GB GPU supports strong quantized coding models, but a nominal 19 GB model cannot remain entirely in VRAM with a useful KV cache. Benchmarking therefore compares the sparse Qwen3 Coder 30B model with the denser 24B Devstral Small 2 model at 32K context.

