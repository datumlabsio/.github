# Branch protection

The settings every repo's `main` needs, and the one thing that changes as a repo matures. From [DES §3](https://github.com/datumlabsio/datum-standards/blob/main/standards/engineering/README.md).

## Always

- **Pull requests required.** No direct pushes to `main`, including from founders and from agents.
- **Force pushes blocked.** A rewritten history breaks everyone holding a clone, and it breaks rollback, which depends on published versions staying what they were (§10).
- **Deletions blocked.**
- **The standard CI checks required**, so a red build cannot be merged past.

## The phase policy

Required approvals change once, and only once:

| Phase | Approvals |
|---|---|
| Draft — nothing depends on it yet | **0** |
| Serving production, or serving an install | **1** |

Zero approvals in draft is deliberate. A repo nobody depends on, with one person working in it, gains nothing from a self-approval ritual — and a rule people route around teaches them the rules are optional. The pull request itself is still required, so the history stays reviewable.

Moving to one approval is a real transition. Do it when the repo starts serving something, not on a date.

## Once CODEOWNERS is in place

Add **require review from code owners** alongside the single approval. Not before — a code-owner rule with no valid owners blocks every pull request, and the fix looks like the rule is broken.

Order matters: `CODEOWNERS` merged, team granted write access, *then* the rule switched on. See [codeowners-conventions.md](codeowners-conventions.md).

## Bots

A bot or agent review does not count towards the required approval (DES §7). Agents draft and pre-review; a person approves. See [bot-identities.md](bot-identities.md).

## Keep the config in the repo

Export the ruleset to JSON and commit it. A setting that exists only in the GitHub UI has no history, no review, and no way to tell whether it changed — which is the same problem as configuration living in someone's head.

```bash
gh api repos/datumlabsio/<repo>/rulesets > rulesets/protect-main.json
```

## What the audit checks

- Pull requests required, force pushes and deletions blocked
- Required approvals match the repo's phase
- The standard checks are in the required list
- A repo serving production with 0 approvals is a finding
