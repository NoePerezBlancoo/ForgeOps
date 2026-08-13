# ForgeOps agent instructions

ForgeOps is a multi-tenant industrial CMMS. Next.js provides the PWA, FastAPI exposes `/api/v1`, PostgreSQL enforces tenant isolation with RLS, Redis coordinates rate limits and RQ jobs, and private S3-compatible storage holds documents.

## Boundaries

- Never weaken company scoping, role checks, RLS, operator separation, secure cookies or storage authorization.
- Treat auth, permissions, RLS, Alembic migrations, billing, infrastructure and deployment as high risk.
- Production, secrets, destructive database operations, Railway, DNS and backups are never delegated locally.
- Local agents work only in an `ai/*` worktree and never push, merge or commit directly.
- Follow the task's `allowed_paths`. Unrelated cleanup is out of scope.

## Backend

- Python 3.12, FastAPI, SQLAlchemy and Pydantic.
- Use repository/service boundaries and parameterized database operations.
- Run `ruff check app scripts tests alembic` and focused pytest suites.
- Alembic changes require direct Codex ownership and PostgreSQL validation.

## Frontend

- Next.js 16, React 19, TypeScript and the existing visual system.
- Preserve responsive behavior, accessibility and role-aware navigation.
- Run ESLint, TypeScript, Vitest and a production build when frontend code changes.

## Local orchestration

Read `.ai/README.md` and `docs/local-ai/codex-orchestration.md`. The supervisor is the authority for scope validation, secret scanning, checks and commits.

