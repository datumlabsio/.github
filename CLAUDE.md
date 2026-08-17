# datumlabsio/.github — org defaults for every repo

## Context

Archetype `docs` (DES §8). One of the three org repos in DES §2, alongside `datumlabsio/actions` (reusable CI workflows) and `datumlabsio/scaffolds` (templates per archetype).

What is here is served by GitHub to every other repo in the org that has no file of its own — PR template, issue forms, SECURITY, CONTRIBUTING, SUPPORT, CODE_OF_CONDUCT, and the public org page in `profile/`. Nothing is copied into those repos; GitHub displays it at the point of use. A change here is visible across the org immediately, which is why every change gets a PR.

The rules live in `datumlabsio/datum-standards` and change by RFC. This repo carries machinery, never rules.

## Commands

No build. Before opening a PR:

```bash
# Issue forms must be valid YAML — a broken form silently stops appearing
python3 -c "import yaml,glob,sys; [yaml.safe_load(open(f)) for f in glob.glob('.github/ISSUE_TEMPLATE/*.yml')]; print('FORMS OK')"

# Relative links must resolve
python3 - <<'EOF'
import re,os
bad=[]
for root,d,files in os.walk('.'):
    if '.git' in root: continue
    for f in [f for f in files if f.endswith('.md')]:
        p=os.path.join(root,f)
        for m in re.finditer(r'\]\(([^)#\s]+)(?:#[^)]*)?\)', open(p).read()):
            t=m.group(1)
            if not t.startswith(('http','mailto')) and not os.path.exists(os.path.normpath(os.path.join(root,t))):
                bad.append(f"{p} -> {t}")
print("\n".join(bad) or "ALL LINKS RESOLVE")
EOF
```

## Conventions

- **Say it once.** If a rule is in the DES or the DWM, link to it — do not restate it. Two copies of a rule drift, and the copy here is the one nobody updates.
- **Templates stay short.** The PR template is a checklist people actually fill in. Every line added makes the whole thing more likely to be deleted unread.
- Community health files at the repo root; PR and issue templates under `.github/`.
- Conventional Commits, branches `feat/…` `fix/…` `chore/…`.

## Guardrails

- **`profile/README.md` is public.** It renders at github.com/datumlabsio for anyone. Treat every edit to it as publishing. Commercial and marketing framing is @ifaizankhan's call per GOVERNANCE.
- **Never put personnel content anywhere in this repo** — no individual assignments, trials, or performance material. Roles and rules only.
- **Never invent a rule here.** If something needs to become a requirement, it goes to `datum-standards` as an RFC. A convention that appears first in this repo has skipped the process.
- Never add a workflow that acts on other repos without saying so in the PR description. This repo is org-wide by design, and that cuts both ways.
- Do not add secrets, tokens, or client names to any file here. This repo is public.

## Docs

- Conventions this repo will document for other repos — CODEOWNERS conventions, branch protection, bot identities, AI review scope — land in `docs/` in a follow-up PR. Not present yet.
- The standards themselves: [datumlabsio/datum-standards](https://github.com/datumlabsio/datum-standards) — start at its README.
