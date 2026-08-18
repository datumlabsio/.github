# AI review scope

Every pull request gets a first-pass AI review before a human reviews it — [DES §7](https://github.com/datumlabsio/datum-standards/blob/main/standards/engineering/README.md), the DWM's agents-draft-humans-judge model enforced by machinery rather than culture.

§7 also requires this page to exist: the workflow **must** say which problems block a pull request and which only comment. An undeclared scope means nobody knows whether a red check is a stop sign or a suggestion, and a check people learn to ignore is worse than no check.

## Current scope

**Everything comments. Nothing blocks.**

That is deliberate for the first phase. A reviewer that blocks and is occasionally wrong stalls every repo in the org at once, and the fix — switching it off — costs more trust than it saves. Comments-only lets us find out how good it actually is while the cost of being wrong is a paragraph somebody scrolls past.

| Category | Today |
|---|---|
| Security practice | comment |
| Coding practice | comment |
| DES conformance | comment |
| Anything else | comment |

## What it reviews

- Security and coding practice
- Conformance to the DES — the rules a human reviewer is least likely to hold in their head

## What it does not do

- **It does not replace human review.** The named owner still judges and merges (DWM §3).
- **Its review does not count towards the required approval** (§7).
- **It does not decide style.** Passing the pinned linters is what style means here (§5). A comment arguing about formatting is a bug in the prompt, not feedback.

## Moving a category to blocking

A deliberate change, not a slider someone nudges:

1. Show the category has been quiet on false positives for a stretch of real pull requests.
2. Update the table above in a pull request, so the change is reviewed and dated.
3. Make the corresponding gate required in branch protection.

Going the other way — a blocking category that turns noisy — is an immediate revert, not a discussion.

## Identity

It runs as the dedicated bot identity, never as a person. See [bot-identities.md](bot-identities.md).
