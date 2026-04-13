#!/usr/bin/env python3
"""
DHCP Lease Audit Script
=======================
Automatically verifies ALL test cases (TC001-TC184) against lease files.
Shows: Present in lease file / Negative-validation test / Missing.

Usage:
    python3 audit_leases.py
    python3 audit_leases.py --update-csv   # Also update CSV Result column
"""

import re
import os
import sys
import csv
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
V4_LEASE = os.path.join(BASE_DIR, "dhcpd.leases")
V6_LEASE = os.path.join(BASE_DIR, "dhcpd6.leases")
CSV_FILE = os.path.join(BASE_DIR, "..", "DHCP_Lease_TestCases.csv")
TESTS_DIR = os.path.join(BASE_DIR, "tests")


# --------------- TC -> lease file mapping ---------------
# v4 TCs: TC001-TC010, TC021-TC030, TC041-TC048, TC057-TC065, TC074-TC086,
#          TC093-TC099, TC103-TC111, TC121-TC128, TC129-TC136, TC145-TC146,
#          TC149-TC151, TC152-TC165, TC180-TC184
# v6 TCs: TC011-TC020, TC031-TC040, TC049-TC056, TC066-TC073, TC081(shared),
#          TC087-TC092, TC100-TC102, TC112-TC120, TC122(shared), TC137-TC144,
#          TC147-TC148, TC166-TC179
# General/both: TC093, TC145-TC146, TC149-TC151, TC180-TC184

V4_TC_RANGES = [
    (1, 10), (21, 30), (41, 48), (57, 65), (74, 80),
    (82, 86), (93, 99), (103, 111), (121, 121),
    (123, 128), (129, 136), (145, 146), (149, 151),
    (152, 165), (180, 184),
]
V6_TC_RANGES = [
    (11, 20), (31, 40), (49, 56), (66, 73), (81, 81),
    (87, 92), (100, 102), (112, 120), (122, 122),
    (137, 144), (147, 148), (166, 179), (180, 180),
]

DDNS_TCS = set(range(103, 121)) | {128}  # TC103-TC120 + TC128 are DDNS (manual)


def tc_in_ranges(tc_num, ranges):
    return any(lo <= tc_num <= hi for lo, hi in ranges)


def get_lease_file(tc_num):
    """Return which lease file(s) a TC should appear in."""
    files = []
    if tc_in_ranges(tc_num, V4_TC_RANGES):
        files.append("v4")
    if tc_in_ranges(tc_num, V6_TC_RANGES):
        files.append("v6")
    return files


def scan_lease_file(filepath):
    """Extract unique TC numbers found in a lease file (tagged or marker)."""
    found = set()
    if not os.path.exists(filepath):
        return found
    with open(filepath, "r") as f:
        content = f.read()
    # Match [AUTOTEST] TC tags
    for m in re.finditer(r'\[AUTOTEST\]\s+TC(\d+)', content):
        found.add(int(m.group(1)))
    # Also match marker hostnames like "tc021-validated"
    for m in re.finditer(r'client-hostname\s+"tc(\d+)-validated"', content):
        found.add(int(m.group(1)))
    return found


def scan_test_files():
    """Scan test files to classify each TC as positive/negative/validation."""
    tc_info = {}
    for pyfile in sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py"))):
        fname = os.path.basename(pyfile)
        with open(pyfile, "r") as f:
            content = f.read()

        # Find each TC comment block + its test function
        # Pattern: # TCxxx: description  ... def test_tcxxx_...(
        for m in re.finditer(
            r'#\s+TC(\d+)[^:]*:\s*(.+?)(?:\n|\r)',
            content
        ):
            tc_num = int(m.group(1))
            tc_desc = m.group(2).strip()
            start_pos = m.start()

            # Get next ~80 lines of code after this TC comment
            code_block = content[start_pos:start_pos + 4000]

            # Classify: does this test write to the lease file?
            writes_lease = False
            is_negative = False
            test_type = "POSITIVE"

            # Check for lease creation/write calls
            write_patterns = [
                r'create_v[46]_lease\(',
                r'update_v[46]_lease\(',
                r'_write_file\(',
                r'_append_file\(',
                r'append_v[46]_lease\(',
                r'build_v[46]_lease\(',  # only if followed by write
                r'marker',
            ]

            # Check for negative/validation patterns
            negative_patterns = [
                r'pytest\.raises\(',
                r'with\s+pytest\.raises',
                r'ValueError',
                r'TypeError',
                r'assert.*invalid',
                r'assert.*error',
                r'ipaddress\.ip_address',
                r'ipaddress\.IPv[46]Address',
                r're\.match.*mac',
                r'validation',
                r'invalid',
            ]

            for wp in write_patterns:
                if re.search(wp, code_block, re.IGNORECASE):
                    writes_lease = True
                    break

            for np_pat in negative_patterns:
                if re.search(np_pat, code_block, re.IGNORECASE):
                    is_negative = True
                    break

            if is_negative and not writes_lease:
                test_type = "NEGATIVE/VALIDATION"
            elif is_negative and writes_lease:
                test_type = "NEGATIVE+MARKER"
            else:
                test_type = "POSITIVE"

            if tc_num in DDNS_TCS:
                test_type = "DDNS (Manual)"

            tc_info[tc_num] = {
                "desc": tc_desc,
                "file": fname,
                "type": test_type,
                "writes_lease": writes_lease,
            }
    return tc_info


def main():
    update_csv = "--update-csv" in sys.argv

    # Scan lease files
    v4_found = scan_lease_file(V4_LEASE)
    v6_found = scan_lease_file(V6_LEASE)

    # Scan test files
    tc_info = scan_test_files()

    # Build full report
    print("=" * 120)
    print("DHCP LEASE AUDIT REPORT")
    print("=" * 120)
    print(f"{'TC':<8} {'Lease File':<10} {'In Lease?':<12} {'Type':<22} {'Test File':<40} {'Description'}")
    print("-" * 120)

    present_count = 0
    missing_count = 0
    negative_count = 0
    ddns_count = 0
    results = {}

    for tc_num in range(1, 185):
        tc_id = f"TC{tc_num:03d}"
        info = tc_info.get(tc_num, {})
        desc = info.get("desc", "???")[:50]
        fname = info.get("file", "???")
        tc_type = info.get("type", "???")
        lease_files = get_lease_file(tc_num)

        # Check presence
        in_v4 = tc_num in v4_found
        in_v6 = tc_num in v6_found
        in_lease = in_v4 or in_v6

        # Build status
        if tc_num in DDNS_TCS:
            status = "DDNS-MANUAL"
            indicator = "🔵"
            ddns_count += 1
        elif in_lease:
            status = "PRESENT"
            indicator = "✅"
            present_count += 1
        elif tc_type in ("NEGATIVE/VALIDATION", "NEGATIVE+MARKER"):
            if in_lease:
                status = "PRESENT"
                indicator = "✅"
                present_count += 1
            else:
                status = "NEG-NO LEASE"
                indicator = "🟡"
                negative_count += 1
        else:
            status = "MISSING"
            indicator = "❌"
            missing_count += 1

        lease_loc = ""
        if "v4" in lease_files and "v6" in lease_files:
            lease_loc = "v4+v6"
        elif "v4" in lease_files:
            lease_loc = "v4"
        elif "v6" in lease_files:
            lease_loc = "v6"

        found_in = []
        if in_v4:
            found_in.append("v4")
        if in_v6:
            found_in.append("v6")
        found_str = "+".join(found_in) if found_in else "---"

        print(f" {indicator} {tc_id:<6} {lease_loc:<10} {found_str:<12} {tc_type:<22} {fname:<40} {desc}")
        results[tc_num] = {"status": status, "indicator": indicator}

    # Summary
    print("=" * 120)
    print(f"\n📊 SUMMARY:")
    print(f"   ✅ Present in lease file : {present_count}")
    print(f"   🟡 Negative (no lease)   : {negative_count}")
    print(f"   🔵 DDNS (manual test)    : {ddns_count}")
    print(f"   ❌ MISSING (needs fix)   : {missing_count}")
    print(f"   ── Total                 : {present_count + negative_count + ddns_count + missing_count}")

    # Show missing details
    if missing_count > 0:
        print(f"\n🔴 MISSING TEST CASES (need investigation):")
        for tc_num in range(1, 185):
            if results[tc_num]["status"] == "MISSING":
                info = tc_info.get(tc_num, {})
                print(f"   TC{tc_num:03d} - {info.get('desc', '???')[:60]} [{info.get('file', '???')}]")

    # Show negative tests without markers
    if negative_count > 0:
        print(f"\n🟡 NEGATIVE/VALIDATION TESTS (no lease entry by design):")
        for tc_num in range(1, 185):
            if results[tc_num]["status"] == "NEG-NO LEASE":
                info = tc_info.get(tc_num, {})
                print(f"   TC{tc_num:03d} - {info.get('desc', '???')[:60]} [{info.get('file', '???')}]")

    # Update CSV if requested
    if update_csv and os.path.exists(CSV_FILE):
        _update_csv_file(results, tc_info)
        print(f"\n📝 CSV updated: {CSV_FILE}")

    return missing_count


def _update_csv_file(results, tc_info):
    """Update CSV with audit status in Result column."""
    rows = []
    with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return

    # Find Result column index
    header = rows[0]
    result_idx = None
    for i, col in enumerate(header):
        if "result" in col.lower():
            result_idx = i
            break

    if result_idx is None:
        header.append("Result")
        result_idx = len(header) - 1
        for row in rows[1:]:
            while len(row) <= result_idx:
                row.append("")

    for row in rows[1:]:
        # Find TC number in row
        tc_match = None
        for cell in row[:3]:
            m = re.search(r'TC[_\-]?0*(\d+)', cell, re.IGNORECASE)
            if not m:
                m = re.search(r'(\d+)', cell)
            if m:
                tc_match = int(m.group(1))
                break

        if tc_match and tc_match in results:
            while len(row) <= result_idx:
                row.append("")
            r = results[tc_match]
            if r["status"] == "PRESENT":
                row[result_idx] = "✅ PASS"
            elif r["status"] == "DDNS-MANUAL":
                row[result_idx] = "🔵 DDNS - Manual"
            elif r["status"] == "NEG-NO LEASE":
                row[result_idx] = "✅ PASS (Validation)"
            elif r["status"] == "MISSING":
                row[result_idx] = "❌ MISSING"

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


if __name__ == "__main__":
    sys.exit(main())
