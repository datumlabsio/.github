# Datum Police — everything you need

The checks that run on your pull requests, where to find them, and what to do
when one goes red.

You do not install anything. You do not learn a new tool. This page is the
whole of it.

---

## The two names

**The Datum Engineering Standard** is the written rules — what a repository
should have. **Datum Police** is the automation that checks them. When someone
says "the police blocked my PR", they mean a check failed.

---

## What runs on your pull request

Four checks, on every pull request, in every adopted repository.

| Check | The question it asks |
|---|---|
| `security / secrets` | Does this change add a password, key or token? |
| `security / semgrep` | Does the code do something known to be dangerous? |
| `security / dependencies` | Do the libraries you depend on have known holes? |
| `security / age` | Is the scanner itself out of date? |

Plus the checks that fit your kind of repository — tests, linting, types, a
build, `dbt build`, a container scan. Those are the same ones you already had;
they now come from one shared place instead of a copy per repo.

**Only the first one blocks a merge on its own.** The others report, and
high-confidence findings escalate.

### Where to find the results

Open your pull request → **Checks** tab → pick the check in the left sidebar.

For **Semgrep** specifically, the useful view is not the raw log:

1. Pull request → **Checks** → `security / semgrep`
2. Read the **Summary** at the top, not the log below it

The summary groups findings by **what it takes to fix them**, not by rule or
severity — because "where do I start" is the actual question, and severity does
not answer it. Findings are also annotated inline on the **Files changed** tab,
against the line they refer to.

---

## Requesting a new repository

Nobody hand-builds repositories any more.

1. Go to **[github.com/datumlabsio/.github/issues/new/choose](https://github.com/datumlabsio/.github/issues/new/choose)**
2. Choose **Request a repository**
3. Answer four questions: name, what it is for, owning team, what kind of thing
   it is
4. Submit. A member applies the **`repo-request`** label — that label is the
   trigger

About ninety seconds later the repository exists, with CI, linting, security
checks, `CODEOWNERS` and branch protection already wired in. The workflow
comments back on your issue with the answers it used, **including the defaults
you were not asked for** — read those, they are the ones worth checking.

If you are not sure which kind to pick, pick the closest one. `generic` is the
honest answer for anything unusual: it gives you the floor every repo gets and
no build gates at all, which beats a hand-made repo that inherits nothing.

---

## Adopting a repository that already exists

**You do not adopt it. It comes to you as a pull request.**

1. Same page: **[issues/new/choose](https://github.com/datumlabsio/.github/issues/new/choose)**
2. Choose **Adopt a repository**
3. A member applies the **`adopt-request`** label

Then, without you doing anything:

- **Preflight** checks every prerequisite at once and reports all the missing
  ones together, rather than one per retry
- It works out what kind of repository yours is from the files already in it
- It renders only the files you do not already have
- CI proves the diff is **additive** — nothing modified, nothing deleted —
  before the pull request is opened
- You review and merge it like any other pull request

### What arrives, and what never does

It adds between thirteen and eighteen files depending on the kind of repo:
the CI caller, `CODEOWNERS`, a pre-commit config, linter configs, dependency
policy.

It will **never**:

- add source code, or a starter app
- touch your project structure — your `pyproject.toml`, `package.json` or
  gitops tree
- add a second release process
- change how you build, test or deploy
- read or write anything outside your repository

Your CI file is called `datum-ci.yml`, deliberately — so it cannot collide with
a `ci.yml` you already have. Both run, neither touches the other.

### If your repository is in a client or partner organisation

One file, and one pull request. Every pull request is scanned the same way, and
there is **no app to install, no secret to add, and no access granted to us** —
the checks themselves are public, which is what makes it work from outside.

Be straight about the limit: we cannot protect a branch in an organisation we
do not own, and we cannot see inside a private repository there. On those
repositories this is a **useful default, not enforcement**.

---

## If a secret gets pushed

This is the one that matters, so it behaves differently from everything else.

**What happens automatically:**

1. `security / secrets` goes red and **the merge is blocked**
2. An issue is filed in the team's private tracking repository
3. The team's Slack channel gets an alert, linking straight to that issue

**What you do, in this order:**

1. **Rotate the credential.** Nothing else counts until this is done.
2. **Then** remove it from the code and push the fix.
3. **Then** close the issue.

### Why rotation comes first

By the time the check goes red, the secret has already been **pushed**. It is
in a branch on GitHub whether or not the pull request ever merges, and anyone
who has cloned the repository already has it.

**Deleting the line does not delete it.** Git keeps every version of every file
forever. Rewriting history does not help either — the old objects survive in
clones, forks and caches.

Rotating is the only action that makes the old value worthless.

Close the issue when the credential is **rotated** — not when the pull request
is fixed. Those are different things, and the issue is tracking the first one.

### Nobody is in trouble

Every finding so far came out of ordinary work, and none of it was catchable in
code review. Findings name the **repository**, never a person.

---

## "It found thirty problems and none of them are breaking anything"

Fair, and you are not the first to say it.

**What blocks:** a secret in your change, a high-confidence dangerous pattern,
a dependency with a known high-severity hole.

**What does not block:** everything else. It files a ticket against the team
that owns the repository. It does not sit on your pull request.

**If the scanner is wrong**, tell us. We suppress the finding in the **shared
config**, so it is fixed for everyone rather than waived for one repository. A
false positive is a bug in our work, not a hurdle for yours. This has already
happened several times.

---

## Catching it before you push

The same checks run on your machine, in about ten seconds, if you turn the
hooks on once:

```bash
pip install pre-commit    # or: brew install pre-commit
pre-commit install
```

From then on they run on every `git commit`. To check everything at once:

```bash
pre-commit run --all-files
```

Ten seconds at your desk beats a red check and a comment in review.

---

## What this does NOT do yet — accurate as of 18 September 2026

Read this bit. The gaps matter more than the features, because silence is
easily mistaken for safety.

- **It only sees pull requests.** A secret pushed to a branch with no pull
  request open is **not** detected. Silence on a feature branch does not mean
  it is clean.
- **GitHub's own secret scanning and push protection are off.** Our checks are
  the only thing looking. Nothing stops a secret at the moment you push.
- **Semgrep scans your whole repository, not just your change.** On an older
  codebase that means findings you did not write showing up on your pull
  request. This is being fixed — it will move to reporting only what your
  change introduces.
- **Not every repository is covered.** Protection follows a repository property
  that is set when it adopts. Until then a repository has the checks but a red
  one does not block a merge.

---

## Who to ask

Anything at all, including the awkward ones: **@humayun-1**, or open an issue
at [issues/new/choose](https://github.com/datumlabsio/.github/issues/new/choose)
— there is a form for bugs in the checks themselves.

If you think a check is wrong, say so. That is the fastest way it gets fixed
for everybody.
