#!/usr/bin/env python3
"""
update_csv_status.py
====================
Maps pytest API test results to CSV test cases and updates the Status column.

Usage:
    python3 update_csv_status.py

It reads:
  - /tmp/pytest_full_results.txt (pytest -v --tb=line output)
  - api_records_testcases.csv

And writes the updated CSV with Status column filled in:
  Pass          = Test automated and passed
  Fail (dig)    = API call passed but dig DNS verification failed
  Skipped       = Test skipped (e.g., DS not supported on DDNS)
  Not Automated = No automated test exists for this test case
"""

import csv
import re
import os

# ── 1. Parse pytest results ────────────────────────────────────────────────
RESULTS_FILE = '/tmp/pytest_full_results.txt'
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'api_records_testcases.csv')

test_results = {}   # (module, func_name) -> 'PASSED' | 'FAILED' | 'SKIPPED'
fail_reasons = {}   # (module, func_name) -> reason string

# Map folder path to module key
FOLDER_TO_MOD = {
    'arecords': 'A',
    'aaaa_records': 'AAAA',
    'caa_records': 'CAA',
    'cname_records': 'CNAME',
    'ds_records': 'DS',
    'hinfo_records': 'HINFO',
    'https_records': 'HTTPS',
    'mx_records': 'MX',
    'naptr_records': 'NAPTR',
    'ns_records': 'NS',
    'ptr_records': 'PTR',
    'srv_records': 'SRV',
    'txt_records': 'TXT',
    'spf_records': 'SPF',
}

# Results from test_all_negative_boundary.py are stored with a special key
# Format: ('NEG', class_name, func_name, param_id) -> status
neg_results = {}   # (class, func, param_or_none) -> 'PASSED' | 'FAILED' | 'SKIPPED'

with open(RESULTS_FILE) as f:
    for line in f:
        line = line.strip()

        # Parse verbose lines from subfolder tests:
        #   domain_and_records_api_automate_testing/folder/test_xxx.py::Class::func PASSED [nn%]
        m = re.search(r'domain_and_records_api_automate_testing/(\w+)/test_\w+\.py::(\w+)::(\w+)\s+(PASSED|FAILED|SKIPPED)', line)
        if m:
            folder, cls, func, status = m.groups()
            mod = FOLDER_TO_MOD.get(folder)
            if mod:
                test_results[(mod, func)] = status

        # Parse verbose lines from test_all_negative_boundary.py:
        #   domain_and_records_api_automate_testing/test_all_negative_boundary.py::Class::func[PARAM] PASSED [nn%]
        nb = re.search(r'domain_and_records_api_automate_testing/test_all_negative_boundary\.py::(\w+)::(\w+?)(?:\[([^\]]+)\])?\s+(PASSED|FAILED|SKIPPED)', line)
        if nb:
            cls, func, param, status = nb.groups()
            neg_results[(cls, func, param)] = status

        # Parse FAILED summary lines for reason
        fm = re.match(r'^FAILED\s+domain_and_records_api_automate_testing/(\w+)/test_\w+\.py::\w+::(\w+)\s+-\s+(.*)', line)
        if fm:
            folder, func, reason = fm.groups()
            mod = FOLDER_TO_MOD.get(folder)
            if mod:
                fail_reasons[(mod, func)] = reason.strip()


# ── 2. Define test function mapping per module ──────────────────────────────
# Each module has: create(3), get_all, get_nonexist, update, delete
MODULE_FUNCS = {
    'A':     {'create': ['test_create_api1','test_create_api2','test_create_api3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_api1', 'delete': 'test_delete_api2'},
    'AAAA':  {'create': ['test_create_aaaa1','test_create_aaaa2','test_create_aaaa3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_aaaa1', 'delete': 'test_delete_aaaa2'},
    'CAA':   {'create': ['test_create_caa1','test_create_caa2','test_create_caa3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_caa1', 'delete': 'test_delete_caa2'},
    'CNAME': {'create': ['test_create_cname1','test_create_cname2','test_create_cname3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_cname1', 'delete': 'test_delete_cname2'},
    'DS':    {'create': ['test_create_ds1','test_create_ds2','test_create_ds3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_ds1', 'delete': 'test_delete_ds2'},
    'HINFO': {'create': ['test_create_hinfo1','test_create_hinfo2','test_create_hinfo3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_hinfo1', 'delete': 'test_delete_hinfo2'},
    'HTTPS': {'create': ['test_create_https1','test_create_https2','test_create_https3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_https1', 'delete': 'test_delete_https2'},
    'MX':    {'create': ['test_create_mx1','test_create_mx2','test_create_mx3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_mx1', 'delete': 'test_delete_mx2'},
    'NAPTR': {'create': ['test_create_naptr1','test_create_naptr2','test_create_naptr3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_naptr1', 'delete': 'test_delete_naptr2'},
    'NS':    {'create': ['test_create_nsr1','test_create_nsr2','test_create_nsr3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_nsr1', 'delete': 'test_delete_nsr2'},
    'PTR':   {'create': ['test_create_ptr1','test_create_ptr2','test_create_ptr3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_ptr1', 'delete': 'test_delete_ptr2'},
    'SRV':   {'create': ['test_create_srv1','test_create_srv2','test_create_srv3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_srv1', 'delete': 'test_delete_srv2'},
    'TXT':   {'create': ['test_create_txt1','test_create_txt2','test_create_txt3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_txt1', 'delete': 'test_delete_txt2'},
    'SPF':   {'create': ['test_create_spf1','test_create_spf2','test_create_spf3'],
              'get_all': 'test_get_all_three', 'get_nonexist': 'test_get_nonexistent',
              'update': 'test_update_spf1', 'delete': 'test_delete_spf2'},
}


def get_func_status(mod, func_name):
    """Return (status_str, is_dig_fail)."""
    s = test_results.get((mod, func_name))
    if s is None:
        return None, False
    if s == 'PASSED':
        return 'Pass', False
    if s == 'SKIPPED':
        return 'Skipped', False
    # FAILED — check if it's a dig failure
    reason = fail_reasons.get((mod, func_name), '')
    is_dig = 'dig' in reason.lower()
    return 'Fail (dig)' if is_dig else 'Fail', is_dig


def get_combined(mod, func_names):
    """Combine statuses from multiple functions."""
    statuses = []
    for fn in (func_names if isinstance(func_names, list) else [func_names]):
        s, _ = get_func_status(mod, fn)
        if s:
            statuses.append(s)
    if not statuses:
        return 'Not Automated'
    if all(s == 'Pass' for s in statuses):
        return 'Pass'
    if all(s == 'Skipped' for s in statuses):
        return 'Skipped'
    if any('dig' in s for s in statuses):
        return 'Fail (dig)'
    return 'Fail'


# ── 3. Map each CSV TC to its automation status ────────────────────────────

def map_tc(tc_no, description):
    """Return status string for a CSV test case."""
    m = re.match(r'(\w+)-TC-(\d+)', tc_no)
    if not m:
        return 'Not Automated'

    prefix = m.group(1)
    tc_num = int(m.group(2))
    desc = description.lower()

    # SPF-TC test cases map to both SPF and TXT modules
    if prefix == 'SPF':
        spf = MODULE_FUNCS.get('SPF', {})
        txt = MODULE_FUNCS.get('TXT', {})
        if tc_num == 1:   return get_combined('SPF', spf['create'])
        if tc_num == 2:   return get_combined('TXT', txt['create'])
        if tc_num == 3:   # Update TTL (both SPF & TXT)
            s1 = get_combined('SPF', spf['update'])
            s2 = get_combined('TXT', txt['update'])
            return 'Pass' if s1 == 'Pass' and s2 == 'Pass' else s1 if 'Fail' in s1 else s2
        if tc_num == 4:   # Delete
            s1 = get_combined('SPF', spf['delete'])
            s2 = get_combined('TXT', txt['delete'])
            return 'Pass' if s1 == 'Pass' and s2 == 'Pass' else s1 if 'Fail' in s1 else s2
        if tc_num == 5:   return get_combined('SPF', spf['get_all'])
        if tc_num == 6:   return get_combined('SPF', spf['get_all'])
        if tc_num == 7:   return get_combined('SPF', spf['create'])
        if tc_num == 8:   return get_combined('TXT', txt['create'])
        if tc_num == 9:   # Update values
            s1 = get_combined('SPF', spf['update'])
            s2 = get_combined('TXT', txt['update'])
            return 'Pass' if s1 == 'Pass' and s2 == 'Pass' else s1 if 'Fail' in s1 else s2
        if tc_num == 10:  return get_combined('SPF', spf['get_nonexist'])
        if tc_num == 25:  # dig verification
            s1 = get_combined('SPF', spf['create'])
            s2 = get_combined('TXT', txt['create'])
            return 'Pass' if s1 == 'Pass' and s2 == 'Pass' else 'Fail (dig)' if 'dig' in s2 else s2
        if tc_num == 30:  # PUT update + records
            s1 = get_combined('SPF', spf['update'])
            s2 = get_combined('TXT', txt['update'])
            return 'Pass' if s1 == 'Pass' and s2 == 'Pass' else s1 if 'Fail' in s1 else s2
        # SPF-TC-011+ : pass through to negative/boundary mapper
        return _map_neg_boundary(prefix, 'SPF', desc)

    # Standard record types
    mod = prefix
    if mod not in MODULE_FUNCS:
        return 'Not Automated'
    funcs = MODULE_FUNCS[mod]

    # ── Positive CRUD tests (TC-001 to TC-008 pattern) ──
    if 'post: create' in desc and 'verify via api' in desc:
        return get_combined(mod, funcs['create'])
    if ('post: add' in desc or 'post: create' in desc) and 'verify record values' in desc:
        return get_combined(mod, funcs['create'])
    if 'put: update' in desc and 'ttl' in desc and 'remove records' not in desc:
        return get_combined(mod, funcs['update'])
    if 'put: update' in desc and 'verify updated values' in desc:
        return get_combined(mod, funcs['update'])
    if 'delete' in desc and 'verify across' in desc:
        return get_combined(mod, funcs['delete'])
    if 'delete: delete' in desc and 'verify' in desc and 'no longer' not in desc:
        return get_combined(mod, funcs['delete'])
    if 'get: retrieve all' in desc:
        return get_combined(mod, funcs['get_all'])
    if 'get specific' in desc:
        return get_combined(mod, funcs['get_all'])
    if 'no longer exists' in desc:
        s1 = get_combined(mod, funcs['get_nonexist'])
        s2 = get_combined(mod, funcs['delete'])
        return 'Pass' if s1 == 'Pass' and s2 == 'Pass' else s1 if 'Fail' in s1 else s2

    # ── NS/PTR special: single/multiple values ──
    if 'single record value' in desc and 'post' in desc:
        return get_combined(mod, funcs['create'])
    if 'multiple record values' in desc and 'post' in desc:
        return get_combined(mod, funcs['create'])
    if 'single value' in desc and 'put' in desc:
        return get_combined(mod, funcs['update'])
    if 'multiple values' in desc and 'put' in desc:
        return get_combined(mod, funcs['update'])

    # ── dig / Linux server verification ──
    if 'linux server' in desc and 'dig' in desc:
        return get_combined(mod, funcs['create'])

    # ── PUT: update TTL and remove records (the mandatory TC) ──
    if 'update record ttl and remove records' in desc:
        return get_combined(mod, funcs['update'])

    # ── Windows / named config / Schedule / Integration (not automated) ──
    if 'windows server' in desc:
        return 'Not Automated'
    if 'named configuration' in desc:
        return 'Not Automated'
    if 'schedule enable' in desc:
        return 'Not Automated'

    # ── Negative & Boundary tests (test_all_negative_boundary.py) ──
    return _map_neg_boundary(prefix, mod, desc)


# ── Map to neg/boundary tests from test_all_negative_boundary.py ──────────
# CSV prefix -> API record type param used in parametrize
PREFIX_TO_RT = {
    'A': 'A', 'AAAA': 'AAAA', 'CAA': 'CAA', 'CNAME': 'CNAME',
    'DS': 'DS', 'HINFO': 'HINFO', 'HTTPS': 'HTTPS', 'MX': 'MX',
    'NAPTR': 'NAPTR', 'NS': 'NS', 'PTR': 'PTR', 'SRV': 'SRV',
    'SPF': 'SPF_TXT',
}


def _neg_status(cls, func, param=None):
    """Look up a neg/boundary test result."""
    s = neg_results.get((cls, func, param))
    if s is None:
        return 'Not Automated'
    if s == 'PASSED':
        return 'Pass'
    if s == 'SKIPPED':
        return 'Skipped'
    return 'Fail'


def _map_neg_boundary(prefix, mod, desc):
    """Map negative/boundary CSV description to test_all_negative_boundary.py results."""
    rt = PREFIX_TO_RT.get(prefix)
    if not rt:
        return 'Not Automated'

    # POST: incorrect zone name
    if 'incorrect zone name' in desc:
        return _neg_status('TestNegIncorrectZone', 'test_create_incorrect_zone', rt)

    # POST: incorrect domain name
    if 'incorrect domain name' in desc and 'post' in desc:
        return _neg_status('TestNegIncorrectDomain', 'test_create_incorrect_domain', rt)

    # POST: incorrect record values (IPv4, IPv6, host name, target, digest, key tag, etc.)
    if any(x in desc for x in ['incorrect ipv4', 'incorrect ipv6', 'incorrect host name',
                                 'incorrect target', 'incorrect digest', 'incorrect key tag',
                                 'incorrect record value', 'incorrect system name']):
        return _neg_status('TestNegIncorrectRecords', 'test_create_incorrect_records', rt)

    # POST: incorrect cluster name
    if 'incorrect cluster name' in desc and 'post' in desc:
        return _neg_status('TestNegIncorrectCluster', 'test_create_incorrect_cluster', rt)

    # PUT: incorrect cluster name
    if 'incorrect cluster name' in desc and 'put' in desc:
        return _neg_status('TestNegIncorrectCluster', 'test_update_incorrect_cluster', rt)

    # POST: empty records
    if 'empty records' in desc and 'post' in desc:
        return _neg_status('TestNegEmptyRecords', 'test_create_empty_records', rt)

    # PUT: empty records
    if 'empty records' in desc and 'put' in desc:
        return _neg_status('TestNegEmptyRecords', 'test_update_empty_records', rt)

    # POST: same domain name already exists (duplicate)
    if 'same domain name that already exists' in desc:
        return _neg_status('TestNegDuplicateDomain', 'test_create_duplicate_domain', rt)

    # POST: duplicate record values
    if 'duplicate record values' in desc:
        return _neg_status('TestNegDuplicateRecords', 'test_create_duplicate_record_values', rt)

    # POST: lowercase then uppercase (case insensitive)
    if 'lowercase' in desc and 'uppercase' in desc:
        return _neg_status('TestNegCaseInsensitiveDup', 'test_case_insensitive_dup', rt)

    # PUT: same domain name as another record
    if 'same domain name as another' in desc:
        return _neg_status('TestNegUpdateDomainConflict', 'test_update_same_domain_as_another', rt)

    # POST: * wildcard subdomain
    if 'wildcard' in desc and ('post' in desc or 'create' in desc):
        if 'not allowed' in desc:
            return _neg_status('TestBoundaryWildcard', 'test_create_wildcard_not_allowed', rt)
        return _neg_status('TestBoundaryWildcard', 'test_create_wildcard_allowed', rt)

    # PUT: * wildcard subdomain
    if 'wildcard' in desc and 'put' in desc:
        return _neg_status('TestBoundaryUpdateWildcardRoot', 'test_update_wildcard', rt)

    # POST: @ root subdomain
    if '@ root' in desc and ('post' in desc or 'create' in desc):
        if 'not allowed' in desc:
            return _neg_status('TestBoundaryRoot', 'test_create_root_not_allowed', rt)
        return _neg_status('TestBoundaryRoot', 'test_create_root_allowed', rt)

    # PUT: @ root subdomain
    if '@ root' in desc and 'put' in desc:
        return _neg_status('TestBoundaryUpdateWildcardRoot', 'test_update_root', rt)

    # CAA specific: flag 0/255/256, invalid tag
    if prefix == 'CAA':
        if 'flag value 0' in desc:
            return _neg_status('TestCAABoundaryFlag', 'test_caa_flag_0', None)
        if 'flag value 255' in desc and 'valid' in desc:
            return _neg_status('TestCAABoundaryFlag', 'test_caa_flag_255', None)
        if 'flag value 256' in desc:
            return _neg_status('TestCAABoundaryFlag', 'test_caa_flag_256', None)
        if 'invalid tag' in desc:
            return _neg_status('TestCAABoundaryFlag', 'test_caa_invalid_tag', None)

    # SRV specific: weight/preference 0/255/256
    if prefix == 'SRV':
        if 'value 0' in desc and 'valid minimum' in desc:
            return _neg_status('TestSRVBoundaryValues', 'test_srv_weight_pref_0', None)
        if 'value 255' in desc and 'valid maximum' in desc:
            return _neg_status('TestSRVBoundaryValues', 'test_srv_weight_pref_255', None)
        if 'value 256' in desc:
            return _neg_status('TestSRVBoundaryValues', 'test_srv_weight_pref_256', None)
        if 'and verify via api' in desc:
            return _neg_status('TestSRVPositive', 'test_srv_create_and_verify', None)
        if 'verify record values' in desc:
            return _neg_status('TestSRVPositive', 'test_srv_create_and_verify', None)
        if 'retrieve all' in desc:
            return _neg_status('TestSRVPositive', 'test_srv_list_all', None)
        if 'retrieve single' in desc or 'get specific' in desc:
            return _neg_status('TestSRVPositive', 'test_srv_get_specific', None)
        if 'update' in desc and 'ttl' in desc:
            return _neg_status('TestSRVPositive', 'test_srv_update_ttl', None)
        if 'update' in desc and 'updated values' in desc:
            return _neg_status('TestSRVPositive', 'test_srv_update_values', None)
        if 'delete' in desc and 'no longer' in desc:
            return _neg_status('TestSRVPositive', 'test_srv_delete_verify', None)
        if 'delete' in desc and 'verify' in desc and 'no longer' not in desc:
            return _neg_status('TestSRVPositive', 'test_srv_delete_verify', None)
        if '* and @' in desc or 'special char' in desc:
            return _neg_status('TestBoundaryWildcard', 'test_create_wildcard_not_allowed', rt)

    # CNAME specific: multiple hosts
    if prefix == 'CNAME' and 'multiple hosts' in desc:
        return _neg_status('TestCNAMESpecific', 'test_cname_multiple_hosts', None)
    if prefix == 'CNAME' and '@ root' in desc and 'not allowed' in desc:
        return _neg_status('TestBoundaryRoot', 'test_create_root_not_allowed', 'CNAME')

    # SPF specific: multiple values, @root
    if prefix == 'SPF':
        if 'multiple values' in desc and 'spf allows only' in desc:
            return _neg_status('TestSPFSpecific', 'test_spf_multiple_values', None)
        if '@ root' in desc and 'one type allowed' in desc:
            return _neg_status('TestSPFSpecific', 'test_spf_root_record', None)
        if '@ root' in desc:
            return _neg_status('TestSPFSpecific', 'test_spf_root_record', None)
        if 'wildcard' in desc:
            return _neg_status('TestBoundaryWildcard', 'test_create_wildcard_allowed', 'SPF_TXT')
        if 'update' in desc and 'ttl' in desc:
            return _neg_status('TestSPFTXTPositive', 'test_spf_txt_update_ttl', None)
        if 'update' in desc and 'values' in desc:
            return _neg_status('TestSPFTXTPositive', 'test_spf_txt_update_values', None)
        if 'multiple record values' in desc and 'txt' in desc:
            return _neg_status('TestTXTPositive', 'test_txt_multiple_values', None)
        if '255 char' in desc:
            return _neg_status('TestBoundary255Chars', 'test_txt_255_char_value', None)

    # TXT specific: multiple values, verify
    if prefix == 'SPF' and 'txt record' in desc and 'multiple record values' in desc:
        return _neg_status('TestTXTPositive', 'test_txt_multiple_values', None)

    # DS specific: multiple records, same digest type
    if prefix == 'DS':
        if 'multiple ds records' in desc or 'add multiple' in desc:
            return _neg_status('TestDSSpecific', 'test_ds_multiple_records', None)
        if 'same digest type' in desc:
            return _neg_status('TestDSSpecific', 'test_ds_multiple_records', None)

    # PTR specific: * and @ not allowed
    if prefix == 'PTR' and ('* and @' in desc or 'special char' in desc):
        return _neg_status('TestBoundaryRoot', 'test_create_root_not_allowed', 'PTR')

    # Generic: update TTL and remove records then add back
    if 'update record ttl and remove records' in desc:
        return _neg_status('TestUpdateTTLRemoveAdd', 'test_update_ttl_remove_add', rt)

    # dig/Linux server verification
    if 'linux server' in desc and 'dig' in desc:
        # These are covered by the CRUD tests' dig sections
        return get_combined(mod, MODULE_FUNCS.get(mod, {}).get('create', []))

    # 255 character record value
    if '255 char' in desc:
        return _neg_status('TestBoundary255Chars', 'test_txt_255_char_value', None)

    # MX/NS incorrect host name / preference
    if 'incorrect host name' in desc or 'incorrect target and preference' in desc:
        return _neg_status('TestNegIncorrectRecords', 'test_create_incorrect_records', rt)

    return 'Not Automated'


# ── 4. Read CSV, update Status, write back ──────────────────────────────────
rows = []
with open(CSV_FILE, 'r', newline='') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows.append(header)
    for row in reader:
        while len(row) < 9:
            row.append('')
        tc_no = row[1].strip()
        description = row[4].strip()
        row[8] = map_tc(tc_no, description)
        rows.append(row)

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(rows)


# ── 5. Print summary report ────────────────────────────────────────────────
from collections import Counter, defaultdict

total_counts = Counter()
module_counts = defaultdict(Counter)

for row in rows[1:]:
    status = row[8]
    module = row[2].strip()
    total_counts[status] += 1
    module_counts[module][status] += 1

print("=" * 72)
print("  API TEST CASES — STATUS UPDATE REPORT")
print("=" * 72)
print(f"\n  Total Test Cases: {sum(total_counts.values())}")
print()
for s in ['Pass', 'Fail (dig)', 'Fail', 'Skipped', 'Not Automated']:
    if total_counts[s]:
        print(f"    {s:20s} : {total_counts[s]:3d}")

print("\n" + "-" * 72)
print(f"  {'Module':<18s} {'Pass':>6s} {'Fail(dig)':>10s} {'Fail':>6s} {'Skip':>6s} {'NotAuto':>8s} {'Total':>6s}")
print("-" * 72)

mod_order = ['A Record','AAAA Record','CAA Record','CNAME Record','DS Record',
             'MX Record','SRV Record','NS Record','PTR Record','SPF/TXT Record',
             'NAPTR Record','HINFO Record','HTTPS Record']

for mod in mod_order:
    mc = module_counts.get(mod, Counter())
    p = mc.get('Pass', 0)
    fd = mc.get('Fail (dig)', 0)
    fl = mc.get('Fail', 0)
    sk = mc.get('Skipped', 0)
    na = mc.get('Not Automated', 0)
    t = p + fd + fl + sk + na
    print(f"  {mod:<18s} {p:>6d} {fd:>10d} {fl:>6d} {sk:>6d} {na:>8d} {t:>6d}")

print("-" * 72)
tp = total_counts.get('Pass', 0)
tfd = total_counts.get('Fail (dig)', 0)
tfl = total_counts.get('Fail', 0)
tsk = total_counts.get('Skipped', 0)
tna = total_counts.get('Not Automated', 0)
tt = tp + tfd + tfl + tsk + tna
print(f"  {'TOTAL':<18s} {tp:>6d} {tfd:>10d} {tfl:>6d} {tsk:>6d} {tna:>8d} {tt:>6d}")

print()
remaining = tna
not_possible = 18 + 10  # Windows(13) + named config(5) + schedule(10)
print(f"  Not Automated breakdown:")
print(f"    Windows/named config/schedule (cannot automate) : {min(not_possible, remaining)}")
print(f"    Remaining unmapped                              : {max(0, remaining - not_possible)}")

print(f"\n  CSV file updated: {CSV_FILE}")
print("=" * 72)
