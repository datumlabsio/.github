# Security

## Reporting a vulnerability

Use **GitHub private vulnerability reporting** on the affected repo: open its **Security** tab and choose *Report a vulnerability*. It is private, it goes to the maintainers, and it gives us one place to coordinate a fix and a disclosure.

<!-- TODO(@humayun-1): add the security email here if you want a non-GitHub path. -->

Do not open a public issue for a vulnerability. Do not describe it in a PR, a commit message, or a Slack channel that anyone can read.

Tell us what you found, which repo and version, what an attacker could do with it, and how to reproduce it. A rough report sent early beats a polished one sent late.

We will confirm we received it, tell you whether we can reproduce it, and keep you updated until it is fixed.

## If a secret gets committed

Secret scanning with push protection is on across the org, so most secrets are blocked before they land. Sometimes one gets through anyway — an older commit, a file type the scanner does not cover, a credential that does not match a known pattern.

**Deleting the commit is not the fix.** Once a secret has been pushed, treat it as public. It is in the reflog, in forks, in anyone's local clone, and possibly in a cache you do not control.

Do this in order:

1. **Rotate the credential.** Issue a new one and put it in the secret manager. This is the only step that actually stops the exposure.
2. **Revoke the old one.** Not "let it expire" — revoke it now.
3. **Check what it touched.** Pull the access logs for the window between the push and the revoke. Assume it was used until you can see that it was not.
4. **Tell the owning crew**, and the client if the credential was theirs. A rotated key with nobody told is an incident you will meet again later.
5. **Then clean the history**, if it is worth it. This is housekeeping, not remediation, and it rewrites history — coordinate with anyone holding a clone.
6. **Write down how it got in.** A config file that should have read from the environment, a missing `.gitignore` line, a scanner gap. Fix that, or you will do all of this again.

Secrets belong in the install's secret manager or the CI environment store. Never in code, never in config, never in a workflow file. That is DPS §8, and it is the rule that makes steps 1 through 6 rare.

## Scope

This policy covers every repo in the `datumlabsio` organization, including per-install engagement orgs.
