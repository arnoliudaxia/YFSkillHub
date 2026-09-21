#!/usr/bin/env bash
# Download the official USPTO PDF for an ordinary US granted utility patent.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: download-us-patent.sh PATENT_ID [OUTPUT.pdf]

Downloads an ordinary US granted utility patent from USPTO.
Accepted PATENT_ID examples: 12552103, US12552103, US12552103B2.
Does not support applications, non-US patents, or US design/plant/reissue IDs.
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

patent_id=${1^^}
if [[ $patent_id =~ ^US([0-9]+)([A-Z][0-9])?$ ]]; then
  number=${BASH_REMATCH[1]}
elif [[ $patent_id =~ ^[0-9]+$ ]]; then
  number=$patent_id
else
  printf 'Unsupported patent ID: %s\n' "$1" >&2
  printf 'Expected an ordinary US granted utility-patent ID, e.g. US12552103B2.\n' >&2
  exit 2
fi

output=${2:-"${patent_id}.pdf"}
url="https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/${number}"
temp_output="${output}.part"
trap 'rm -f "$temp_output"' EXIT

printf 'Downloading US patent %s from USPTO...\n' "$number" >&2
curl --fail --location --retry 2 --connect-timeout 20 --max-time 300 \
  --output "$temp_output" "$url"

if [[ $(head -c 5 "$temp_output") != '%PDF-' ]]; then
  printf 'USPTO response is not a PDF; output was not saved.\n' >&2
  exit 1
fi

mv -f "$temp_output" "$output"
trap - EXIT
printf 'Saved: %s\n' "$output"
