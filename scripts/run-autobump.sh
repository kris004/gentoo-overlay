#!/usr/bin/env bash
# Update eligible ebuild releases, validate them, and push scoped bot commits.

set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
cd "${REPO_ROOT}"

readonly GITHUB_TOKEN_VALUE="${GITHUB_TOKEN:?GITHUB_TOKEN must be set}"
readonly GITHUB_REPOSITORY_VALUE="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"
readonly GITHUB_RUN_ID_VALUE="${GITHUB_RUN_ID:?GITHUB_RUN_ID must be set}"
readonly RUNNER_TEMP_VALUE="${RUNNER_TEMP:?RUNNER_TEMP must be set}"
readonly SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
readonly TARGET_BRANCH="${AUTOBUMP_BRANCH:-main}"
readonly RUN_URL="${SERVER_URL}/${GITHUB_REPOSITORY_VALUE}/actions/runs/${GITHUB_RUN_ID_VALUE}"
readonly DISTDIR="${RUNNER_TEMP_VALUE}/gentoo-distfiles"

# Do not expose a contents-write token to ebuild QA subprocesses.
unset GH_TOKEN GITHUB_TOKEN

current_atom=""

find_open_issue() {
  local title="$1"

  GH_TOKEN="${GITHUB_TOKEN_VALUE}" gh issue list \
    --repo "${GITHUB_REPOSITORY_VALUE}" \
    --state open \
    --limit 100 \
    --json number,title \
    --jq ".[] | select(.title == \"${title}\") | .number" | sed -n '1p'
}

report_failure() {
  local exit_status="$1"
  local issue_number
  local title
  local body

  [[ -n "${current_atom}" ]] || return 0
  title="[autobump] ${current_atom}"
  printf -v body \
    "The automatic ebuild update for %s failed with exit status %s.\n\nThe previous published ebuild remains unchanged. [Inspect the workflow run](%s)." \
    "${current_atom}" "${exit_status}" "${RUN_URL}"

  issue_number="$(find_open_issue "${title}")"
  if [[ -n "${issue_number}" ]]; then
    GH_TOKEN="${GITHUB_TOKEN_VALUE}" gh issue comment "${issue_number}" \
      --repo "${GITHUB_REPOSITORY_VALUE}" \
      --body "${body}"
  else
    GH_TOKEN="${GITHUB_TOKEN_VALUE}" gh issue create \
      --repo "${GITHUB_REPOSITORY_VALUE}" \
      --title "${title}" \
      --body "${body}"
  fi
}

close_failure_issue() {
  local issue_number
  local title

  title="[autobump] ${current_atom}"
  issue_number="$(find_open_issue "${title}")" || return 0
  [[ -n "${issue_number}" ]] || return 0
  GH_TOKEN="${GITHUB_TOKEN_VALUE}" gh issue close "${issue_number}" \
    --repo "${GITHUB_REPOSITORY_VALUE}" \
    --comment "The package is current again. Recovered in [workflow run ${GITHUB_RUN_ID_VALUE}](${RUN_URL})." \
    >/dev/null || true
}

handle_error() {
  local exit_status="$?"

  trap - ERR
  set +e
  report_failure "${exit_status}"
  exit "${exit_status}"
}
trap handle_error ERR

if [[ -n "$(git status --porcelain=v1)" ]]; then
  echo "autobump: checkout is not clean" >&2
  false
fi

mkdir -p "${DISTDIR}" "${HOME}/.cache/pkgcheck/repos"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
GH_TOKEN="${GITHUB_TOKEN_VALUE}" gh auth setup-git

package_list="$(python3 scripts/autobump.py list)"
mapfile -t packages <<<"${package_list}"
for current_atom in "${packages[@]}"; do
  result_file="${RUNNER_TEMP_VALUE}/${current_atom//\//__}.json"
  AUTOBUMP_GITHUB_TOKEN="${GITHUB_TOKEN_VALUE}" \
    python3 scripts/autobump.py update \
    --package "${current_atom}" \
    --result "${result_file}"

  status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "${result_file}")"
  case "${status}" in
    current | waiting)
      close_failure_issue
      ;;
    updated)
      package_dir="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["package_dir"])' "${result_file}")"
      state_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["state_path"])' "${result_file}")"
      versions="$(python3 -c 'import json,sys; print(", ".join(x["gentoo_version"] for x in json.load(open(sys.argv[1]))["updates"]))' "${result_file}")"

      pkgdev manifest --config no -d "${DISTDIR}" "${package_dir}"
      pmaint --config no regen --dir "${HOME}/.cache/pkgcheck/repos" .
      pkgcheck scan --exit=error,warning,style,PythonCompatUpdate "${package_dir}"

      git add -- "${package_dir}" "${state_path}"
      git diff --cached --check
      if git diff --cached --quiet; then
        echo "autobump: ${current_atom} reported an update but produced no diff" >&2
        false
      fi
      if [[ -n "$(git status --porcelain=v1 | grep -v '^\(A\|M\)  ' || true)" ]]; then
        echo "autobump: unexpected worktree changes for ${current_atom}" >&2
        git status --short >&2
        false
      fi

      git commit \
        -m "${current_atom}: add ${versions}" \
        -m "Generated from verified upstream releases by the overlay autobump workflow."
      GH_TOKEN="${GITHUB_TOKEN_VALUE}" git push origin "HEAD:${TARGET_BRANCH}"
      close_failure_issue
      ;;
    *)
      echo "autobump: unknown updater status ${status@Q} for ${current_atom}" >&2
      false
      ;;
  esac
done

current_atom=""
