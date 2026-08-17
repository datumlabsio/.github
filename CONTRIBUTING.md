# Contributing

This applies to every repo in the `datumlabsio` organization. A repo may add to it, but the parts below are the same everywhere.

## How a change lands

Branch, PR, review, merge. No direct pushes to `main` — not for founders, not for agents.

- Branch names: `feat/…`, `fix/…`, `chore/…`. Short-lived — merged in days, not weeks.
- Commit titles follow [Conventional Commits](https://www.conventionalcommits.org/). This is what gives us changelogs and version numbers for free.
- Every PR gets an AI first-pass review before a human reviews it. The agent drafts and pre-reviews; a person judges and merges.
- Every PR has one named owner. They own the decision to ship, and that does not transfer to the agent that wrote the code.

Keep a PR under 400 changed lines where you can. Generated code, renames and dependency bumps do not count — just say so in the description. A PR nobody can hold in their head gets approved, not reviewed.

## What a reviewer is checking

Three questions:

1. Is this the right change?
2. Does it work in the edge cases?
3. Can the next person understand it?

Style is not one of them. Passing the pinned linters is what style means here, and the configs live in `datumlabsio/actions`. If you disagree with a config, that is a PR against the config, not a comment on someone's PR.

## Where the rules actually live

This file is the short version. The rules themselves are in **[datumlabsio/datum-standards](https://github.com/datumlabsio/datum-standards)**, and they change by RFC — never by decree and never by drift.

- What a repo must have, how CI works, the security baseline: the [DES](https://github.com/datumlabsio/datum-standards/blob/main/standards/engineering/README.md).
- How people and agents work day to day: the [DWM](https://github.com/datumlabsio/datum-standards/blob/main/standards/working-model/README.md).
- How to propose a change: [CONTRIBUTING in that repo](https://github.com/datumlabsio/datum-standards/blob/main/CONTRIBUTING.md).

If you think a rule is wrong, write it down and open an RFC. A rejected RFC with reasons is still useful; an argument that happens in a PR comment and then evaporates is not.

## New repos

Every repo is born from a scaffold in `datumlabsio/scaffolds`, one per archetype. No blank-page repos. If you are starting something and there is no scaffold that fits, that is a conversation before it is a repo.

## Reporting something sensitive

Security issues do not go in issues or PRs. See [SECURITY.md](SECURITY.md).
