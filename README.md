# Quote Audit

An offline construction quotation checker built with the [Salam Programming Language](https://github.com/SalamLang/Salam).

This original, AI-assisted project checks quantity × unit price against the claimed line total. It uses integer decimal arithmetic, reports invalid rows and duplicate item codes, and does not modify input files. It is a calculation aid, not a certified valuation or tax system.

## Run

Install Salam **0.5.3** from its [official releases](https://github.com/SalamLang/Salam/releases/tag/v0.5.3), including the bundled C compiler. Put `salam` and `tcc` on your terminal's PATH, or pass their full paths to the build commands below. This application has no third-party dependencies and makes no network calls.

```sh
mkdir -p build
salam build salam.salam --cc=tcc --output=build/quote-audit --log-level=error
./build/quote-audit examples/clean.tsv
./build/quote-audit examples/discrepancies.tsv --json
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Path build -Force | Out-Null
# Replace both paths with your extracted official Salam release directory.
& 'C:\Tools\salam-windows\salam.exe' build salam.salam '--cc=C:\Tools\salam-windows\tcc\tcc.exe' --output=build/quote-audit.exe --log-level=error
& .\build\quote-audit.exe examples/clean.tsv
& .\build\quote-audit.exe examples/discrepancies.tsv --json
```

Use `--help` for usage. Exit codes are **0** for a clean quote, **1** for findings, and **2** for an input/usage failure. For automation, `--json` returns schema version 1 with decimal totals encoded as strings to preserve cents.

## Input contract

The input is tab-separated UTF-8 text with this exact header:

```text
code<TAB>description<TAB>quantity<TAB>unit_price<TAB>claimed_total
```

`<TAB>` denotes an actual tab character. LF and CRLF line endings and an optional UTF-8 BOM are accepted. Fields cannot contain embedded tabs or newlines. Item codes are trimmed, case-sensitive, and limited to 80 bytes; descriptions must be nonempty and at most 512 bytes.

- Quantity: positive, at most three decimal places, maximum **1,000,000** units.
- Unit price: nonnegative, at most two decimal places, maximum **1,000,000.00** currency units.
- Claimed line total: nonnegative, at most two decimal places, maximum **1,000,000,000,000.00** currency units.
- No currency symbols, thousands separators, exponent notation or signed numbers.
- Maximum **512 KiB** and **10,000** data rows. Blank data rows are findings; one final newline is allowed. A header-only file is not a valid quotation.

Each line computes `(quantity_thousandths * unit_price_cents + 500) / 1000`, rounding **half up** to cents before summation. The stated limits keep arithmetic below signed 64-bit overflow. One currency is assumed throughout a file; there is no exchange-rate or tax handling.

Invalid rows are excluded from totals. Valid rows with duplicate codes remain included, with an explicit duplicate finding. The JSON `totals_scope` and text report disclose this behavior. Diagnostics show line numbers and categories without echoing item descriptions or codes.

Example output for `examples/clean.tsv`:

```text
Quote Audit
Valid rows: 3
Expected total: 680.35
Claimed total: 680.35
Difference: 0.00
Findings: 0
```

## Tests

Build the application first, then run the black-box suite with Python 3.11 or newer:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
```

For native unit checks, compile and execute each of `tests/money_test.salam`, `tests/calculation_test.salam`, `tests/parser_test.salam` and `tests/audit_test.salam` using the same `--cc` option. Each returns a nonzero code on failure. Format checks use:

```sh
salam format src tests salam.salam --check
```

The integration suite runs the real compiled executable. It compares 250 seeded random line calculations with Python `Decimal`, exercises rounding and maximum input limits, parses JSON, and checks that each input file's SHA-256 remains unchanged. CI repeats native compilation and tests on Windows using the pinned official release and its SHA-256 file. Tests have been run locally on Windows; Linux/macOS and Docker are not claimed as tested.

## Source organization

`decimal` validates scaled decimal numbers; `money` and `quantity` implement their distinct limits and formatting; `model` defines records; `calculation` rounds line totals; `table` tokenizes TSV without relying on the current stdlib Split edge case; `quote_parser` validates rows; `duplicates` checks code identity; `audit` aggregates findings and totals; `reader` bounds file loading; `text_report` and `json_report` render outputs; `salam.salam` handles command-line usage.

The development history records successive implemented and tested milestones. Development used OpenAI Codex; no human-only coding, past customers, professional certification, acceptance or payment is claimed. Prepared for the Salam community reward in [issue #1713](https://github.com/SalamLang/Salam/issues/1713); this mention does not imply a reward has been awarded.
