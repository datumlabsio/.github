# Renovate — how a fix reaches 200 repos

DES §2 says: fix a gate once in `datumlabsio/actions` and every repo inherits it on the next bump. **Renovate is the "next bump."** Without it that sentence is aspirational — a release in `actions` reaches nothing, because every repo pins an exact version and nothing opens the pull request to move it.

## How it is wired

| Where | What |
|---|---|
| `datumlabsio/.github` → `default.json` | The org preset. Every rule lives here. |
| every repo → `renovate.json` | Three lines: `extends: ["local>datumlabsio/.github"]` |

A repo does not configure Renovate. It inherits, the same way its CI inherits — so a policy change is one pull request here rather than 200.

The scaffold writes `renovate.json` at birth, so a new repo is covered from its first commit.

## What it does, and when

| Change | Timing | Pull request |
|---|---|---|
| `datumlabsio/actions` version | **immediately** | its own, labelled `datum-actions` |
| Security fix | **immediately**, typed `fix` | labelled `security` |
| Third-party actions (SHA-pinned) | Monday morning | grouped |
| Vendored tool pins | Monday morning | grouped per surface |
| A major on a linter or compiler | never automatic | waits for approval on the dashboard |

Weekly rather than continuous is deliberate. A bump that arrives on a Monday gets read; one that arrives all week gets muted, and a muted queue is the same as no Renovate at all.

## Four decisions worth knowing

**`actions` bumps are never grouped and never delayed.** That pull request is the path a gate fix travels. Bundling it with a lockfile update makes the important change hard to see.

**`actions` is pinned by version, not by digest.** `pinDigests` is off for `datumlabsio/**` because DES §4 wants an exact version tag here — a SHA cannot be read as *which release am I on*, and the whole point of the pin is being able to answer that. Third-party actions are the opposite: SHA-pinned, because a tag can be moved by someone else.

**npm packages wait 10 days.** pnpm refuses packages published inside its own `minimumReleaseAge`, and a range that resolves to a just-published patch is then rejected — so a same-day bump would land a lockfile CI cannot install. The delay is correctness, not caution.

**A major on a vendored linter needs a human.** Passing the pinned linter *is* conformance (DES §5). A major that changes rules changes what conformance means in every repo at once, so it arrives as a dashboard entry to approve rather than a pull request to merge.

## The custom managers

Renovate has no built-in manager for a bare `name=version` list under a filename we invented, so the vendored pins are matched by regex. All four files, nineteen pins, each with its real datasource:

| File | Format | Datasource |
|---|---|---|
| `tool-versions.txt`, `dbt-tool-versions.txt` | `ruff==0.16.3` | PyPI |
| `web-tool-versions.txt` | `pnpm=11.22.0` | npm — except `node`, which has its own datasource, and `biome`, which publishes as `@biomejs/biome` |
| `gitops-tool-versions.txt` | `kustomize=v5.8.1` | GitHub releases — except `yamllint`, which is on PyPI |

**kustomize needed special handling.** It tags releases as `kustomize/v5.8.1` in a repo that also tags `kyaml/`, `api/` and `cmd/config/`. Without `extractVersionTemplate` Renovate would cheerfully "upgrade" kustomize to `kyaml/v0.21.1`.

## Changing a rule

Edit `default.json`, and validate before you push — the validator catches things a JSON parse does not:

```bash
npx --package renovate renovate-config-validator default.json
```

It rejected three real mistakes in the first draft of this file: `//` is not a valid comment key (use `description`), `managerFilePatterns` is the newer name for `fileMatch` and older Renovate refuses it, and `prPriority` cannot sit inside `vulnerabilityAlerts`.

A valid config that matches nothing is the failure mode to watch for. When you add a pin format, check the regex against the real file rather than trusting it.
