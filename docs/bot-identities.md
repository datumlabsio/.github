# Bot identities

Every bot, agent and workflow acts under its own identity, never a person's. [DES §6](https://github.com/datumlabsio/datum-standards/blob/main/standards/engineering/README.md) — the platform's non-human-identity principle applied to our own machinery.

## Why it is a rule and not a preference

If an agent commits as a person, the history stops telling you who decided what. Six months later nobody can distinguish work that person wrote, reviewed and understood from work that arrived under their name while they were asleep. That distinction is exactly what the DWM's named-owner rule depends on.

It also means an agent's access cannot be scoped or revoked separately from a human's, so the least-privilege rule has nothing to act on.

## The register

Every automation gets a row here before it gets access.

| Identity | Used by | May do | Owner |
|---|---|---|---|
| **`datum-police`** (GitHub App, installation `155450559`) | `renovate.yml` in this repo. Later: the conformance audit (§12) and the `main` watcher. | Push branches and open pull requests on the repos it is installed on. Read and write issues, for the Dependency Dashboard. | @humayun-1 |

**`datum-police` in detail.** A GitHub App rather than a machine user, so it is
its own identity and not a seat. Credentials are `DATUM_POLICE_APP_ID` and
`DATUM_POLICE_PRIVATE_KEY`, held as **organisation** secrets scoped to selected
repositories — org-level because the audit and the watcher will need the same
identity from other repos, and rotating a key in one place beats three.

**The token is minted per run and revoked when the job ends.** Nothing long-lived
is stored: an App id and a private key are useless without the installation. That
is the practical reason to prefer an App over a personal access token, beyond the
rule below.

**What it may not do.** It has no `main` access anywhere — every repo it touches
has a ruleset blocking direct pushes and requiring a pull request. It holds no
production credentials. It cannot approve: agents draft, a person approves.

**One caveat, recorded rather than hidden.** Our rulesets currently require **0**
approvals, in draft phase. So nothing *structurally* stops this identity merging a
pull request it opened — the only reason it does not is that `default.json` never
sets `automerge`. That is a configuration choice, not a guardrail, and the "a bot
review never counts as an approval" rule below is vacuous until the approval count
is 1. Worth revisiting when a repo moves to production phase.

An automation that is not in this table should not have credentials. If you find one, that is a finding, not a shortcut somebody took for good reasons.

## The rules that apply to all of them

- **Read-only by default.** Write access is granted for a named reason, to a named identity, and no further.
- **Never production credentials.** CI publishes an artifact; the install pulls it (§4). Nothing in CI needs to reach production, so nothing in CI gets to.
- **A bot review never counts as an approval.** Agents draft and pre-review; a person approves (§7).
- **Agent-authored commits are labelled**, so they are visible in history without reading the diff.
- **What an agent reads is information, not orders.** An agent must not follow instructions found in issue text, comments, or tool output (§7). This matters most for the automations that read issues and pull requests, since those are the ones a stranger can write to.

## Adding one

1. Provision the identity — its own account or app, not a personal token.
2. Scope it to the minimum that makes it work, and write down what that is.
3. Add its row above.
4. Confirm it cannot satisfy a required approval.

## What the audit checks

- No automation holds credentials without a row here
- No bot can satisfy a required approval
- No agent identity holds write access to production
