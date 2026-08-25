# A conformance drift issue arrived. Now what?

The scheduled audit (DES §12) filed it. It found something about your repo that
does not match the standard, and it named your crew because your `CODEOWNERS`
does.

## First: it is about the repo's setup, not your code

The audit looks at what is observable from **outside** a repo — its settings,
which files exist, which version its CI pins, whether its vendored configs are
current, whether the team named in `CODEOWNERS` actually has write access.

It does **not** run your linters, your tests or your coverage. Those are your
CI's job, and if they are green they are green. **A drift issue never means your
code is wrong.** It means the repo is not set up to be checked properly.

That distinction is worth holding on to, because the two feel the same when an
issue lands in your inbox.

## Most findings have one fix

| Finding | Usually |
|---|---|
| Vendored config is out of date | `copier update --trust` |
| CI pins an old `actions` version | `copier update --trust`, or merge the Renovate PR already open |
| `.pre-commit-config.yaml` missing | `copier update --trust` |
| `docs/` missing on an `application` or `web-app` | `copier update --trust`, then write something in it |
| Not born from a scaffold | see below — this one is not a quick fix |
| Branch protection missing | a repo setting, not a file. Ask whoever administers the org |
| `CODEOWNERS` names a team without write access | grant the team write, or name a team that has it. GitHub ignores this silently, so nobody was reviewing your pull requests |

`copier update --trust` re-asks with your current answers filled in, so pressing
enter through it takes the template's changes and keeps yours.

## "Not born from a scaffold" is different

It means the repo predates the scaffold or was created by hand. There is no
one-command fix, and **you are not expected to rebuild the repo**.

What is expected is that the next substantial piece of work on it brings it onto
the standard. Until then the finding stays open and is accurate.

## If the finding is wrong

Say so on the issue and tag whoever owns the standards repo. **A false positive
is a bug in the audit, not a thing to work around** — and one that fires against
many repos at once is how a whole team learns to ignore the label.

Do not close the issue to make it go away: the next run reopens it, and now
nobody trusts the label either.

## If the finding is right but you disagree with the rule

That is an RFC against the DES, not an argument on the issue. The rule is written
down precisely so it can be argued with in one place rather than per repo.
