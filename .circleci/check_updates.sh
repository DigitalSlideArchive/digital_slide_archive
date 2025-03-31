#!/bin/bash

DEPENDENT_REPOS=(
  "girder/girder/commits/master"
  "girder/large_image/commits/master"
  "DigitalSlideArchive/HistomicsUI/commits/master"

  "girder/slicer_cli_web/commits/master"
  "girder/girder_worker/commits/master"
  "girder/girder_worker_utils/commits/master"
  "DigitalSlideArchive/import-tracker/commits/main"

  "girder/girder/commits/v4-integration"
  "DigitalSlideArchive/girder_assetstore/commits/girder-5"
)
# girder_assetstore should be main branch once it is official


LAST_COMMITS_FILE=".last_commits"

GITHUB_TOKEN="${GITHUB_TOKEN}"

get_latest_commit() {
  local repo=$1
  local api_url="https://api.github.com/repos/${repo}"
  local headers=""
  if [ -n "$GITHUB_TOKEN" ]; then
    headers="-H 'Authorization: token ${GITHUB_TOKEN}'"
  fi
  curl -s $headers "$api_url" | jq -r '.sha'
}

if [ -f "$LAST_COMMITS_FILE" ]; then
  source "$LAST_COMMITS_FILE"
  cat "$LAST_COMMITS_FILE"
fi

UPDATES_FOUND=false

for repo in "${DEPENDENT_REPOS[@]}"; do
  echo "Checking $repo..."
  latest_commit=$(get_latest_commit "$repo")
  last_commit_var="LAST_COMMIT_${repo//[\/ -]/_}" # Replace slashes with underscores
  last_commit="${!last_commit_var}"

  if [ "$latest_commit" != "$last_commit" ]; then
    echo "Update found in $repo: $latest_commit (previous: $last_commit)"
    UPDATES_FOUND=true
    echo "$last_commit_var='$latest_commit'" >> "$LAST_COMMITS_FILE"
  else
    echo "No updates in $repo."
  fi
done

if [ "$UPDATES_FOUND" = true ]; then
  echo "Updates found, triggering build pipeline..."
  curl -X POST \
    -H "Circle-Token: ${CIRCLECI_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"branch":"master"}' \
    https://circleci.com/api/v2/project/github/DigitalSlideArchive/digital_slide_archive/pipeline
else
  echo "No updates found, skipping build."
fi
