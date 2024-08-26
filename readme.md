# Artisan-chatbot-backend

- FastApi

## Getting Started

First, run the development server:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Branching Conventions

- `main` - Stable code for release.
- `release/[version-number]` - Base branch for development release.
- `feature/[feature-name]` - Feature branch derived from **release/[version-number]**.
- `fix/[feature-name]` - Hotfix branch after the `release` branch has been merged to **main**.

> <span style="color:#228BE6"> NOTE: feature-name should be beacon cased to avoid multi level slashes on branching. </span>

---

## Commit Message Conventions

#### Commit Tags

- `init` - when initializing a feature with base setup.
- `wip` - When the work in progress and checking out to different branch on uncircumstance situations.
- `feature` - added new features/modules.
- `improvements` - updates on existing features.
- `revamp` - when improved an existing code either logic wise or feature wise.
- `fix` - when fixing bugs/issues
- `ui` - when worked majorly on style changes for an feature.
- `test` - when test cases are added.
- `config` - when worked on config level changes like env, lang updates.

> <span style="color:#228BE6"> NOTE: Keep these commit tags in your commit message and don't mispell. </span>
