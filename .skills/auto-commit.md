# Auto-Commit Skill

## Trigger
After completing any task or chunk of changes that modifies files. Use this skill when:
- User explicitly requests a commit
- Task completion is confirmed by user
- A logical chunk of work is finished

## Rules

### 1. Commit ALL Changes
Always stage and commit all changes (tracked + untracked files).

### 2. Conventional Commits Format
```
type(scope): description
```
- Max 80 characters for the entire message
- Use lowercase for type and description
- Scope is optional but recommended

### 3. Valid Types
- `feat`: New feature or functionality
- `fix`: Bug fix
- `refactor`: Code refactoring
- `chore`: Maintenance, dependencies, tooling
- `docs`: Documentation only
- `test`: Adding/updating tests

### 4. Description Guidelines
- Start with verb in imperative form
- Be concise but descriptive
- If >80 chars, truncate with `...` or simplify

## Examples

### Good (≤80 chars)
- `feat(search): add 200ms debounce`
- `fix(url): extract domain from career page`
- `chore: update AGENTS.md with new structure`
- `docs(api): add filter endpoint documentation`
- `refactor(api): simplify job query builder`

### Bad (>80 chars)
- `feat(search): add 200ms debounce to prevent excessive API calls when user types in search field`

## Exclusions

Skip these files/directories:
- `out/` - generated output files
- `node_modules/` - npm dependencies
- `*.log` - log files
- `.git/` - git internal files
- `*.db` - SQLite databases
- `*.csv` - generated CSV files
- Build artifacts (`build/`, `dist/`)

## Implementation Steps

When commit is needed:

1. **Check status**: Run `git status` to see all changes
2. **Stage all**: Run `git add -A`
3. **Create message**: Compose commit message following rules above
4. **Commit**: Run `git commit -m "type(scope): description"`
5. **Report**: Show commit hash to user

## Notes

- Always confirm with user before committing if not explicitly requested
- If unsure about type, use `chore`
- Include relevant issue numbers if applicable (e.g., `fix(#123): ...`)