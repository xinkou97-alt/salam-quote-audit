"""Black-box tests run the real native Salam application, not a translation."""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from decimal import Decimal, ROUND_HALF_UP

ROOT = Path(__file__).resolve().parents[1]
APP = Path(os.environ.get("QUOTE_AUDIT_EXE", ROOT / "build" / ("quote-audit.exe" if os.name == "nt" else "quote-audit")))
HEADER = "code\tdescription\tquantity\tunit_price\tclaimed_total\n"


class QuoteAuditTests(unittest.TestCase):
    def run_quote(self, text, expected=0, as_json=True):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "quote with spaces.tsv"
            source.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            result = subprocess.run([str(APP), str(source)] + (["--json"] if as_json else []), capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before, "input modified")
            if as_json and expected < 2:
                return json.loads(result.stdout)
            return result

    def test_exact_money(self):
        result = self.run_quote(HEADER + "A\tWork\t2\t0.29\t0.58\n")
        self.assertEqual(result["expected_total"], "0.58")
        self.assertEqual(result["findings"], [])

    def test_half_up(self):
        result = self.run_quote(HEADER + "A\tWork\t0.5\t0.01\t0.01\nB\tWork\t0.499\t0.01\t0.00\n")
        self.assertEqual(result["expected_total"], "0.01")

    def test_wrong_total(self):
        result = self.run_quote(HEADER + "A\tWork\t2\t3\t5\n", 1)
        self.assertEqual(result["difference"], "-1.00")
        self.assertEqual(result["findings"][0]["kind"], "arithmetic")

    def test_duplicate_codes(self):
        result = self.run_quote(HEADER + "A\tWork\t1\t1\t1\n A \tWork\t2\t1\t2\n", 1)
        self.assertEqual(result["findings"][0]["kind"], "duplicate")
        self.assertEqual(result["expected_total"], "3.00")

    def test_case_sensitive_codes(self):
        result = self.run_quote(HEADER + "A\tWork\t1\t1\t1\na\tWork\t2\t1\t2\n")
        self.assertEqual(result["valid_rows"], 2)

    def test_invalid_fields(self):
        for field, value in [(0, ""), (1, ""), (2, "0"), (2, "-1"), (2, "1e2"), (2, "1.0001"), (3, "1.999"), (3, "nan"), (4, "-1")]:
            with self.subTest(field=field, value=value):
                cells = ["A", "Work", "1", "1", "1"]
                cells[field] = value
                result = self.run_quote(HEADER + "\t".join(cells), 1)
                self.assertEqual(result["valid_rows"], 0)

    def test_columns_and_header(self):
        self.assertEqual(self.run_quote("bad\n", 1)["findings"][0]["kind"], "header")
        self.assertEqual(self.run_quote(HEADER + "A\tWork\t1\t1", 1)["findings"][0]["kind"], "columns")

    def test_empty_quote_and_blank_row(self):
        self.assertEqual(self.run_quote(HEADER, 1)["findings"][0]["kind"], "empty_quote")
        self.assertEqual(self.run_quote(HEADER + "\n", 1)["findings"][0]["kind"], "columns")

    def test_crlf_bom_and_unicode(self):
        text = (HEADER + "A\t混凝土报价\t1.005\t29\t29.15\n").replace("\n", "\r\n")
        self.assertEqual(self.run_quote(b"\xef\xbb\xbf" + text.encode())["expected_total"], "29.15")

    def test_nul_and_size_limit(self):
        self.run_quote((HEADER + "A\tWork\t1\t1\t1\x00TRAILING").encode(), 2)
        self.run_quote(b"x" * 524289, 2)

    def test_numeric_limits(self):
        result = self.run_quote(HEADER + "A\tWork\t1000000\t1000000\t1000000000000\n")
        self.assertEqual(result["expected_total"], "1000000000000.00")
        self.run_quote(HEADER + "A\tWork\t1000000.001\t1\t1\n", 1)

    def test_ten_thousand_rows(self):
        rows = [f"A{i}\tWork\t1\t0.01\t0.01" for i in range(10000)]
        result = self.run_quote(HEADER + "\n".join(rows))
        self.assertEqual(result["expected_total"], "100.00")
        self.run_quote(HEADER + "\n".join(rows + ["EXTRA\tWork\t1\t0.01\t0.01"]), 1)

    def test_random_decimal_reference(self):
        rng = random.Random(731)
        rows, total = [], Decimal("0")
        for i in range(250):
            quantity = Decimal(rng.randint(1, 10000000)) / 1000
            price = Decimal(rng.randint(0, 10000000)) / 100
            expected = (quantity * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rows.append(f"R{i}\tWork\t{quantity:.3f}\t{price:.2f}\t{expected:.2f}")
            total += expected
        result = self.run_quote(HEADER + "\n".join(rows))
        self.assertEqual(result["expected_total"], f"{total:.2f}")

    def test_text_report(self):
        result = self.run_quote(HEADER + "A\tWork\t1\t1\t0.99\n", 1, False)
        self.assertIn("line 2 [arithmetic]", result.stdout)
        self.assertIn("Difference: -0.01", result.stdout)

    def test_usage_and_missing_file(self):
        for args in [[], ["absent.tsv"], ["x.tsv", "--unknown"]]:
            result = subprocess.run([str(APP), *args], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2)
        self.assertEqual(subprocess.run([str(APP), "--help"], capture_output=True, timeout=10).returncode, 0)


if __name__ == "__main__":
    unittest.main()
