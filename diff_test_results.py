#!/usr/bin/env python3
"""
Compares two JUnit XML test result files (before vs after a fix) and
reports which tests changed status. A test that newly PASSES after a
"fix" is just as worth flagging as one that newly fails — it can mean
the fix accidentally papered over a real bug instead of resolving it.

Usage:
    python diff_test_results.py --baseline before.xml --current after.xml
"""
import argparse
import sys
import xml.etree.ElementTree as ET


def parse_results(path):
    """Returns {test_name: 'pass'|'fail'|'error'|'skipped'}"""
    results = {}
    try:
        tree = ET.parse(path)
    except (FileNotFoundError, ET.ParseError) as e:
        print(f"WARNING: could not parse {path}: {e}", file=sys.stderr)
        return results

    root = tree.getroot()
    # JUnit XML can be <testsuite> at root or wrapped in <testsuites>
    testcases = root.findall(".//testcase")

    for tc in testcases:
        name = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        if tc.find("failure") is not None:
            status = "fail"
        elif tc.find("error") is not None:
            status = "error"
        elif tc.find("skipped") is not None:
            status = "skipped"
        else:
            status = "pass"
        results[name] = status
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    args = parser.parse_args()

    baseline = parse_results(args.baseline)
    current = parse_results(args.current)

    all_tests = set(baseline.keys()) | set(current.keys())
    changed = []

    for test in sorted(all_tests):
        b_status = baseline.get(test, "<did not exist>")
        c_status = current.get(test, "<removed>")
        if b_status != c_status:
            changed.append((test, b_status, c_status))

    if not changed:
        return  # empty stdout = no change, matches diff_pipeline_output.py convention

    print(f"Test result diff: {len(changed)} test(s) changed status\n")
    for test, before, after in changed:
        flag = ""
        if before == "fail" and after == "pass":
            flag = "  <- fix may have resolved this (verify it's real, not a masked assertion)"
        elif before == "pass" and after == "fail":
            flag = "  <- REGRESSION"
        print(f"  {test}: {before} -> {after}{flag}")


if __name__ == "__main__":
    main()
  
