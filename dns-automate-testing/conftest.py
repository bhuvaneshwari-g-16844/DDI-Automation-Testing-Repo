import pytest
import os
import subprocess


# ────────────────────────────────────────────────────────────────────── #
#  Auto-generate /tmp/pytest_full_results.txt & update CSV after tests
# ────────────────────────────────────────────────────────────────────── #
_collected_results = []


@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    """Collect each test's final outcome (call phase) in verbose format."""
    if report.when == "call":
        status = "PASSED" if report.passed else ("FAILED" if report.failed else "SKIPPED")
        _collected_results.append((report.nodeid, status, getattr(report, "longreprtext", "")))
    elif report.when == "setup" and report.skipped:
        _collected_results.append((report.nodeid, "SKIPPED", ""))


def pytest_sessionfinish(session, exitstatus):
    """After all tests finish, write results file and run CSV updater."""
    results_file = "/tmp/pytest_full_results.txt"
    csv_updater = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "domain_and_records_api_automate_testing", "update_csv_status.py"
    )

    # Only run if there are api_tests results
    api_results = [r for r in _collected_results if "domain_and_records_api_automate_testing/" in r[0]]
    if not api_results:
        return

    # Write verbose results in the same format pytest -v produces
    with open(results_file, "w") as f:
        for nodeid, status, longrepr in _collected_results:
            f.write("{} {} \n".format(nodeid, status))
            if status == "FAILED" and longrepr:
                f.write("FAILED {} - {}\n".format(
                    nodeid, longrepr.splitlines()[-1] if longrepr.splitlines() else ""))

    # Run the CSV updater
    if os.path.exists(csv_updater):
        subprocess.run(["python3", csv_updater], cwd=os.path.dirname(csv_updater))