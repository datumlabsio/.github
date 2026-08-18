# CODEOWNERS conventions

GitHub reads `CODEOWNERS` from the repo it applies to. It cannot be inherited from this one, so **every repo needs its own file** — this page is the convention it should follow, and [DES §12](https://github.com/datumlabsio/datum-standards/blob/main/standards/engineering/README.md)'s audit is what enforces it.

## The rule

**The owner is a team, never an individual.** DES §3.

An individual owner looks fine until that person is on leave, changes crew, or leaves. Then the repo has an owner who cannot review, and the next pull request either waits or routes around the rule. A team survives all three.

## The part people get wrong

**A team only counts as an owner if it has write access to the repo.**

GitHub silently ignores a `CODEOWNERS` entry naming a team without write access. No error, no warning — reviews simply never get requested, and the repo looks protected while nothing is enforcing anything. This is the single most common way a `CODEOWNERS` file ends up decorative.

Granting access:

```bash
gh api -X PUT orgs/datumlabsio/teams/<team>/repos/datumlabsio/<repo> -f permission=push
```

## The shape

```
# Everything, unless a more specific rule below matches.
* @datumlabsio/core

# Later lines win. Use them where ownership is genuinely different,
# not to carve up a repo nobody shares.
/infra/           @datumlabsio/platform
/docs/            @datumlabsio/core
```

Last matching line wins, which is the opposite of most config files. Put the broad rule first and narrow below it.

## Per-directory ownership

Worth it in a repo where different crews genuinely own different paths — a monorepo, or a pipelines repo covering several installs. Not worth it in a repo one crew owns end to end, where it only creates lines that drift out of date.

If a directory has no owner more specific than `*`, that is fine. Silence means the top-level owner.

## What the audit checks

- The file exists
- Every entry names a team, not an individual
- Every team named has write access to that repo
- A repo whose only owner is a person, or a team that cannot review, is a finding
