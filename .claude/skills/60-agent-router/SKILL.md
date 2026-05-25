# 60-Agent Code Repair & Development Router Skill

Use this skill first when diagnosing, designing, or implementing new applications and resolving code bugs. Call only the specific agent, or the smallest safe team of agents, needed for the exact task.

## Hard rule

Select the minimum agent scope. Never run broad repairs when a specialist can handle the issue.

## 60-Agent Catalog

### Core Diagnosis & Research
1. `diagnose-research-repair` â€” Issue Checker & Researcher: Check for all coding issues, run search queries, read documentation, and plan the complete fix.
2. `repo-router` â€” Repository Router: Analyze repo architecture and route tasks to the smallest safe specialist developer team.
3. `error-triage` â€” Stack Trace Triager: Analyze logs, debugger outputs, and compile-time errors to pinpoint the root cause.
4. `network-diagnostics` â€” Connectivity Auditor: Diagnose API connection issues, host unreachable warnings, and port blocks.
5. `performance-profiler` â€” Bottleneck Locator: Locate memory leaks, slow database queries, and execution bottlenecks.
6. `compliance-audit` â€” Code Compliance Auditor: Inspect code workflows for license, formatting, and standard violations.

### App Development & Architecture
7. `app-architect` â€” Project Architect: Design file structures, routing schemas, and dependency trees for new apps.
8. `fullstack-developer` â€” Full-Stack Engineer: Implement end-to-end features spanning database, API endpoints, and user interface.
9. `ui-ux-designer` â€” Interface & Experience Designer: Design visual structures, themes, interactive flows, and responsive layouts.
10. `frontend-ui` â€” Frontend Developer: Implement React components, CSS layouts, HTML structures, and browser interaction logic.
11. `flask-fastapi` â€” Backend API Developer: Develop Python backend server routes, Uvicorn configurations, and templates.
12. `database-schema` â€” DB Schema Designer: Design SQL/NoSQL schemas, foreign keys, constraints, and tables.

### Code Fixing & Refactoring
13. `python-repair` â€” Python Specialist: Fix python package setups, broken venvs, import errors, and script syntax.
14. `node-react-repair` â€” NodeJS & React Developer: Fix package.json scripts, lockfiles, Node module errors, and build setups.
15. `typescript-repair` â€” TS Compiler Specialist: Resolve TypeScript compiler errors, configuration mismatches, and types.
16. `javascript-dev` â€” Vanilla JS Developer: Write and repair DOM operations, AJAX requests, and vanilla logic.
17. `powershell-repair` â€” Windows Automation Specialist: Fix PowerShell scripts, execution policies, env paths, and cmdlets.
18. `dataflex-odbc` â€” DataFlex Reader: Read and write DataFlex dat, pyodbc, and index configurations.
19. `cpp-cmake` â€” C++ & Build Specialist: Repair compiler warnings, header files, CMakeLists.txt, and link dependencies.
20. `csharp-dotnet` â€” .NET Developer: Fix C# files, csproj/sln configurations, NuGet dependencies, and msbuild targets.
21. `refactoring-expert` â€” Code Quality Expert: Refactor legacy code, simplify complex functions, and optimize nested conditions.
22. `code-optimizer` â€” Performance Optimizer: Maximize logic execution speed, configure caches, and reduce resource footprints.

### Database & Sync Specialists
23. `sql-safety` â€” SQL Safety Inspector: Prevent SQL injection, audit raw queries, and manage migrations safely.
24. `odbc-driver` â€” ODBC Configuration Agent: Setup, repair, and diagnose ODBC drivers, DSNs, and connection strings.
25. `data-migration` â€” Schema Migration Agent: Execute schema updates, backups, data transformations, and validation.
26. `shopify-fiztrade` â€” Shopify FIZTrade Integrator: Sync Shopify products, order payloads, API mappings, and retries.
27. `pawnpay-sync` â€” PawnPay Sync Developer: Fix PawnPay data synchronizers, DSN queries, and verification workflows.
28. `pawndex-dashboard` â€” Pawndex Interface Specialist: Fix Flask/FastAPI backend views, dashboard UI, and metrics tables.

### Environment & Environments Setup
29. `ollama-local-ai` â€” Ollama AI Specialist: Configure local LLMs, Ollama services, and offline model execution.
30. `claude-code-proxy` â€” Claude Code Proxy Engineer: Fix proxy server ports, routes, auth tokens, and SSE streaming.
31. `codespaces` â€” GitHub Codespaces Bootstrapper: Setup devcontainers, custom bootstrap scripts, and package setups.
32. `devcontainer` â€” Devcontainer Configurator: Fix JSON settings, features, and docker-compose hookups inside containers.
33. `windows-env` â€” Windows Path Specialist: Fix Windows environment variables, user paths, and software detection.
34. `wsl-linux-env` â€” WSL Linux Specialist: Repair WSL Ubuntu packages, permissions, paths, and CLI compatibility.
35. `npm-permissions` â€” NPM Prefix Repairer: Fix node EACCES permissions, global packages, and path overrides.
36. `gemini-cli` â€” Gemini CLI Helper: Fix Gemini CLI settings, environment checks, and commands.
37. `github-cli` â€” gh Tool Configurator: Authenticate gh extensions, verify orgs, and execute gh commands.

### Build, Test, & Release
38. `requirements-manager` â€” Dependency Pinning Agent: Fix requirements.txt, pyproject.toml, package.json, and lockfiles.
39. `test-runner` â€” Testing Specialist: Run, fix, and verify pytest, npm test, and other test command suites.
40. `api-tester` â€” API Test Suite Developer: Write integration and contract tests for endpoints using Postman or Python.
41. `browser-automation` â€” End-to-End Test Agent: Write and fix Playwright/Selenium browser automated tests.
42. `build-release` â€” Build Packager: Package applications, configure setup scripts, and output release bundles.
43. `github-actions-ci` â€” CI/CD Workflow Specialist: Fix GitHub Actions YAML files, runner versions, and secrets access.
44. `docker-repair` â€” Docker Container Specialist: Fix Dockerfiles, compose files, container links, and multi-stage builds.
45. `windows-service` â€” Service Wrapper Specialist: Configure NSSM wrappers, task schedulers, and auto-restart flags.
46. `final-verifier` â€” Release Verifier: Execute final verification checks and output merge readiness.

### Security & Privacy
47. `security-auditor` â€” Security Vulnerability Inspector: Audit source files and dependencies for vulnerabilities.
48. `secrets-guard` â€” API Key Protector: Inspect codebase for committed API keys, tokens, and env files.
49. `secrets-rotator` â€” API Key Rotator: Safely swap outdated keys, rotate tokens, and write new secret structures.
50. `backup-restore` â€” Backup Coordinator: Create and execute backup/restore strategies before destructive steps.

### Documentation & Reporting
51. `readme-docs` â€” Technical Writer: Generate README installation steps, user manuals, and runbooks.
52. `reader-report` â€” Summary Writer: Translate technical commits into readable reports for project managers.
53. `documentation-publisher` â€” Docs Publisher: Build Sphinx, MkDocs, or Docusaurus pages and publish output.

### Additional Specialized roles
54. `react-native-dev` â€” Mobile App Developer: Fix mobile UI issues, native bundles, and Android/iOS setup.
55. `electron-desktop-dev` â€” Desktop App Developer: Develop and package Electron.js desktop frameworks.
56. `redis-caching` â€” Redis Caching Specialist: Configure Redis caches, pub/sub channels, and memory boundaries.
57. `auth-security` â€” Authentication Engineer: Audit OAuth2, JWT tokens, session stores, and user permission gates.
58. `websocket-realtime` â€” WebSockets Developer: Build and debug real-time messaging, chat, and event loops.
59. `git-repair` â€” Git Versioning Expert: Resolve merge conflicts, fix detached HEAD states, and prune history.
60. `repo-cleanup` â€” Cache Cleaner: Clean project cache folders, build outputs, and unused large files.

## Default teams

- New App Blueprint: `app-architect`, `ui-ux-designer`, `fullstack-developer`, `database-schema`, `readme-docs`
- Bug Investigation & Repair: `diagnose-research-repair`, `error-triage`, `test-runner`, `final-verifier`
- Sync & ODBC Integration: `dataflex-odbc`, `odbc-driver`, `pawnpay-sync`, `secrets-guard`, `final-verifier`
- Local Environment & AI Setup: `ollama-local-ai`, `claude-code-proxy`, `windows-env` or `wsl-linux-env`
- CI/CD Deployment pipeline: `github-actions-ci`, `docker-repair`, `build-release`, `final-verifier`
- Security & Secrets Review: `security-auditor`, `secrets-guard`, `secrets-rotator`, `final-verifier`

## Required output format

1. Agents selected
2. Why selected
3. Commands to run
4. Files changed
5. Tests/checks run
6. Remaining risks
7. Final pass/fail status
