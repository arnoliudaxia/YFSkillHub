---
name: us-patent-download
description: Download the official PDF for a US granted patent from the USPTO by patent number, such as US12552103B2. Use when a user wants to download, batch-download, or verify PDF files of US granted patents. Does not handle pending US applications or non-US patents.
compatibility: Requires bash, curl, and network access to image-ppubs.uspto.gov.
---

# US Granted-Patent PDF Download

Use the USPTO's official PDF endpoint rather than scraping the Google Patents interface.

## Scope

- **Supported:** ordinary US granted utility-patent identifiers consisting of digits, optionally prefixed with `US` and suffixed with a kind code, e.g. `12552103`, `US12552103`, or `US12552103B2`.
- **Not supported:** published/pending applications, non-US patent offices, and special US identifiers such as design (`USD...`), plant (`USPP...`), or reissue (`USRE...`) patents. State this limitation and use an appropriate official source instead.

## Before downloading

1. Confirm the user provided a US **granted patent** identifier.
2. Tell the user the output path and that a PDF will be written or overwritten. For a single explicit download request, proceed; otherwise ask before a batch or overwrite operation.
3. Download only from the official `image-ppubs.uspto.gov` endpoint.

## Single-file download

From this skill directory, run:

```bash
bash scripts/download-us-patent.sh US12552103B2
```

This writes `US12552103B2.pdf` in the current working directory. To choose an output file:

```bash
bash scripts/download-us-patent.sh US12552103B2 path/to/patent.pdf
```

The endpoint receives the bare number, so the request URL for the example is:

```text
https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12552103
```

## Verify the result

After a successful download, verify that it is a PDF and report its size and page count where `pdfinfo` is available:

```bash
file US12552103B2.pdf
pdfinfo US12552103B2.pdf | grep -E '^(Pages|Page size):'
sha256sum US12552103B2.pdf
```

A valid download must begin with the PDF signature (`%PDF-`). Do not describe an HTML error page as a downloaded patent.

## Batch use

For a user-approved list containing one ID per line:

```bash
while IFS= read -r patent_id; do
  [ -z "$patent_id" ] && continue
  bash scripts/download-us-patent.sh "$patent_id"
done < patent-ids.txt
```

Use a separate output directory for batches, log failures, and do not silently skip `curl` errors.
