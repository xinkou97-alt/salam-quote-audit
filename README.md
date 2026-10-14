# Quote Audit

An offline construction quotation checker built with the [Salam Programming Language](https://github.com/SalamLang/Salam).

This original, AI-assisted project checks quantity × unit price against the claimed line total. It uses integer decimal arithmetic, reports invalid rows and duplicate item codes, and does not modify input files. It is a calculation aid, not a certified valuation or tax system.

Implementation is in progress. The input contract is tab-separated UTF-8 text with the header `code`, `description`, `quantity`, `unit_price`, `claimed_total`. Quantity has at most three decimal places; money has at most two. Negative values and scientific notation are rejected. Line totals round half up to cents before aggregation.
