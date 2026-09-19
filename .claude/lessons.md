# Lessons Learned

## Workspace Discovery & Inspection (Zero Guessing)
- **Date**: 2026-09-19
- **Context**: Releasing project and pushing commits/tags to GitHub.
- **Lesson**: NEVER guess credentials, paths, or configurations. Thoroughly inspect the workspace first before executing operations. Project credentials (such as GitHub token/API keys) live directly in the workspace at `.github/api-key`. Always discover and read workspace files first to prevent errors and unauthenticated attempts.
