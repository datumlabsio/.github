#!/usr/bin/env bash
# Everything that must be true before a repository can be adopted, checked at
# once and reported together.
#
#     preflight.sh <org> <repo> <owning-team>
#
# Adoption failed SIX times on real repositories and not one failure was in the
# code. Each was a separate thing outside it -- a label, an App installation, a
# git credential, a branch name, a property's edit permission, a secret's
# repository scope -- and each was found by running the whole thing and reading
# a log. Six runs to learn six facts that could have been six lines.
#
# So they are checked first, and ALL of them are reported, not just the first to
# fail. Finding out about the second prerequisite after fixing the first is the
# thing this exists to stop.
set -uo pipefail

ORG="$1"; NAME="$2"; TEAM="$3"
PROPERTY="datum-standard"
fail=0

bad() { echo "  ✗ $1"; fail=1; }
ok()  { echo "  ✓ $1"; }
# A check that could not RUN is not a check that failed. Reporting it as a
# failure sends someone to fix a thing that was never broken -- which is what
# happened here once already, on the property's edit permission.
unk() { echo "  ? $1"; }

echo "Preflight for $ORG/$NAME"
echo

# --- the App can see the repository ---------------------------------------
if gh api "repos/$ORG/$NAME" -q .name >/dev/null 2>&1; then
  ok "datum-police can see the repository"
else
  bad "datum-police cannot see $ORG/$NAME. Add it at
      https://github.com/organizations/$ORG/settings/installations
      Nothing else here can be checked until this is fixed."
  echo; echo "Preflight FAILED."; exit 1
fi

# --- it is not already adopted --------------------------------------------
DEFAULT=$(gh api "repos/$ORG/$NAME" -q .default_branch)
if gh api "repos/$ORG/$NAME/contents/.copier-answers.yml?ref=$DEFAULT" -q .sha >/dev/null 2>&1; then
  bad "already adopted -- .copier-answers.yml is on '$DEFAULT'. Use scaffold-update to move it forward."
else
  ok "not yet adopted"
fi

# --- CODEOWNERS will not be inert -----------------------------------------
# GitHub silently ignores a CODEOWNERS entry naming a team without write, so
# reviews are never requested and nothing anywhere looks wrong.
#
# THE COUNT IS THE TELL. This call does not fail when the token may not see
# teams -- it returns 200 and a filtered list, which for datum-police is empty.
# So "no permission for our team" and "no visibility into any team" arrive
# identically, and the second was reported as the first: ember-capital has
# push, and preflight said it had none. Zero teams is not an answer about one
# team; a repository in this organisation has at least one.
#
# Only the COUNT is printed, never the names. This repository is public and so
# are its Actions logs.
TEAM_ERR=$(mktemp)
TEAMS_JSON=$(gh api "repos/$ORG/$NAME/teams" 2>"$TEAM_ERR")
TEAM_RC=$?
read -r TEAM_COUNT PERM <<<"$(printf '%s' "$TEAMS_JSON" | python3 -c '
import json, sys
try:
    teams = json.load(sys.stdin)
except Exception:
    teams = []
found = [t.get("permission", "") for t in teams if t.get("slug") == sys.argv[1]]
print(len(teams), found[0] if found else "")' "$TEAM" 2>/dev/null)"
TEAM_COUNT="${TEAM_COUNT:-0}"

if [ "$TEAM_RC" -ne 0 ]; then
  unk "cannot read which teams have access to $NAME, so whether CODEOWNERS will
      be honoured is UNKNOWN -- not known to be wrong. GitHub said:
      $(tr -d '\r' < "$TEAM_ERR" | head -2 | tr '\n' ' ')
      Verify by hand: gh api repos/$ORG/$NAME/teams"
elif [ "$TEAM_COUNT" -eq 0 ]; then
  unk "this token can see NO teams on $NAME -- not one, and every repository
      here has at least one. That is a limit on what the token may see, NOT a
      statement about '$TEAM', and the two used to be reported the same way.
      Whether CODEOWNERS will be honoured is UNKNOWN.
      Verify by hand: gh api repos/$ORG/$NAME/teams"
else
  case "$PERM" in
    push|maintain|admin) ok "team '$TEAM' has $PERM -- CODEOWNERS will be honoured" ;;
    "") bad "team '$TEAM' is not among the $TEAM_COUNT team(s) with access to $NAME,
      so its CODEOWNERS entry would be silently ignored -- no error, no reviews
      requested, nothing looks wrong.
      gh api -X PUT orgs/$ORG/teams/$TEAM/repos/$ORG/$NAME -f permission=push" ;;
    *)  bad "team '$TEAM' has '$PERM', which is not write. CODEOWNERS would be inert.
      gh api -X PUT orgs/$ORG/teams/$TEAM/repos/$ORG/$NAME -f permission=push" ;;
  esac
fi
rm -f "$TEAM_ERR"

# --- the property exists and this token may write it -----------------------
EDITABLE=$(gh api "orgs/$ORG/properties/schema/$PROPERTY" -q .values_editable_by 2>/dev/null)
if [ -z "$EDITABLE" ]; then
  bad "the '$PROPERTY' property is not defined for the organisation, so nothing
      will mark this repository adopted and the organisation ruleset will not reach it."
elif [ "$EDITABLE" != "org_and_repo_actors" ]; then
  bad "'$PROPERTY' is editable by '$EDITABLE'. An App is a REPOSITORY actor, so it
      cannot set it -- the API says 'Actor doesn't have permissions to edit
      properties'. Tick 'Allow repository actors to set this property' on
      https://github.com/organizations/$ORG/settings/properties"
else
  ok "'$PROPERTY' is writable by repository actors"
fi

# --- the one that cannot be checked from here ------------------------------
# Reading an organisation secret's repository scope needs org admin, which this
# token deliberately does not have. It is stated rather than checked, because a
# missing secret makes scaffold-update report SUCCESS and do nothing -- the
# worst of the six, and invisible until somebody triggers it and reads the log.
echo "  ? DATUM_POLICE_APP_ID and DATUM_POLICE_PRIVATE_KEY must include $NAME in
      their repository scope, or scaffold-update will run, report success, and
      do nothing. Cannot be checked without org admin:
      https://github.com/organizations/$ORG/settings/secrets/actions"

echo
if [ "$fail" -eq 1 ]; then
  echo "Preflight FAILED. Everything above marked ✗ has to be fixed; they are all listed so you can do them in one pass."
  exit 1
fi
echo "Preflight passed."
