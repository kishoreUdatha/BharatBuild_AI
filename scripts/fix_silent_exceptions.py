#!/usr/bin/env python3
"""
Script to find and help fix silent exception handling in the codebase.

This identifies patterns like:
- except Exception: pass
- except: pass
- except Exception as e: pass

Run: python scripts/fix_silent_exceptions.py

Options:
  --fix     Attempt to auto-fix by adding logging (creates backup)
  --report  Generate a detailed report of issues found
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict

# Patterns to find
SILENT_EXCEPTION_PATTERNS = [
    # except Exception: pass
    (r'except\s+Exception\s*:\s*\n\s*pass', 'except Exception: pass'),
    # except: pass
    (r'except\s*:\s*\n\s*pass', 'bare except: pass'),
    # except Exception as e: pass
    (r'except\s+Exception\s+as\s+\w+\s*:\s*\n\s*pass', 'except Exception as e: pass'),
    # except SomeError: pass
    (r'except\s+\w+Error\s*:\s*\n\s*pass', 'except SomeError: pass'),
]

# Files to exclude
EXCLUDE_PATTERNS = [
    'test_', '_test.py', 'conftest.py', '__pycache__',
    '.venv', 'alembic/versions', 'migrations'
]


def should_exclude(file_path: str) -> bool:
    """Check if file should be excluded from analysis"""
    return any(pattern in file_path for pattern in EXCLUDE_PATTERNS)


def find_silent_exceptions(file_path: Path) -> List[Tuple[int, str, str]]:
    """Find silent exception patterns in a file.

    Returns list of (line_number, pattern_type, line_content)
    """
    issues = []
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Check for pass after except
            if i > 0 and 'pass' in line.strip():
                prev_line = lines[i-1].strip()
                if prev_line.startswith('except'):
                    # Determine pattern type
                    if 'Exception' in prev_line:
                        if ' as ' in prev_line:
                            pattern_type = 'except Exception as e: pass'
                        else:
                            pattern_type = 'except Exception: pass'
                    elif prev_line == 'except:':
                        pattern_type = 'bare except: pass'
                    else:
                        pattern_type = 'except SomeError: pass'

                    issues.append((i + 1, pattern_type, f"{prev_line}\n{line.strip()}"))

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return issues


def analyze_codebase(root_path: Path) -> Dict[str, List[Tuple[int, str, str]]]:
    """Analyze entire codebase for silent exceptions"""
    results = defaultdict(list)

    app_path = root_path / 'backend' / 'app'
    if not app_path.exists():
        print(f"Error: {app_path} not found")
        return results

    for py_file in app_path.rglob('*.py'):
        if should_exclude(str(py_file)):
            continue

        issues = find_silent_exceptions(py_file)
        if issues:
            rel_path = py_file.relative_to(root_path)
            results[str(rel_path)] = issues

    return results


def generate_report(results: Dict[str, List[Tuple[int, str, str]]]) -> str:
    """Generate a detailed report of issues found"""
    report_lines = [
        "=" * 60,
        "SILENT EXCEPTION HANDLING REPORT",
        "=" * 60,
        ""
    ]

    total_issues = sum(len(issues) for issues in results.values())
    report_lines.append(f"Total issues found: {total_issues}")
    report_lines.append(f"Files affected: {len(results)}")
    report_lines.append("")

    # Group by pattern type
    by_pattern = defaultdict(list)
    for file_path, issues in results.items():
        for line_num, pattern_type, content in issues:
            by_pattern[pattern_type].append((file_path, line_num))

    report_lines.append("Issues by type:")
    for pattern_type, occurrences in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
        report_lines.append(f"  {pattern_type}: {len(occurrences)}")

    report_lines.append("")
    report_lines.append("-" * 60)
    report_lines.append("DETAILED FINDINGS")
    report_lines.append("-" * 60)

    # Sort files by number of issues
    for file_path, issues in sorted(results.items(), key=lambda x: -len(x[1])):
        report_lines.append(f"\n{file_path} ({len(issues)} issues):")
        for line_num, pattern_type, content in issues:
            report_lines.append(f"  Line {line_num}: {pattern_type}")

    report_lines.append("")
    report_lines.append("=" * 60)
    report_lines.append("RECOMMENDED FIX")
    report_lines.append("=" * 60)
    report_lines.append("""
Replace:
    except Exception:
        pass

With:
    except Exception as e:
        logger.error(f"[ModuleName] Operation failed: {e}", exc_info=True)
        # Either re-raise or handle appropriately
        raise

Or for non-critical operations:
    except Exception as e:
        logger.warning(f"[ModuleName] Non-critical error: {e}")
        # Return default/fallback value
        return None
""")

    return "\n".join(report_lines)


def get_suggested_fix(file_path: str, line_num: int, pattern_type: str) -> str:
    """Generate suggested fix for a specific issue"""
    # Extract module name from file path
    parts = file_path.replace('\\', '/').split('/')
    module_name = parts[-1].replace('.py', '').title().replace('_', '')

    return f"""
# At line {line_num}, replace:
#   except Exception:
#       pass
# With:
    except Exception as e:
        logger.error(f"[{module_name}] Operation failed: {{e}}", exc_info=True)
        raise  # or return appropriate fallback
"""


def main():
    """Main entry point"""
    # Find project root
    script_path = Path(__file__).resolve()
    root_path = script_path.parent.parent

    print("Analyzing codebase for silent exception handling...")
    print(f"Root path: {root_path}")
    print()

    results = analyze_codebase(root_path)

    if not results:
        print("No silent exception patterns found! ")
        return 0

    # Generate and print report
    report = generate_report(results)
    print(report)

    # Save report to file
    report_path = root_path / 'reports' / 'silent_exceptions_report.txt'
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report)
    print(f"\nReport saved to: {report_path}")

    # Priority files to fix (top 5 by issue count)
    print("\n" + "=" * 60)
    print("PRIORITY FILES TO FIX (Top 5)")
    print("=" * 60)

    top_files = sorted(results.items(), key=lambda x: -len(x[1]))[:5]
    for file_path, issues in top_files:
        print(f"\n{file_path}:")
        print(f"  Issues: {len(issues)}")
        print(f"  Command: code {root_path / file_path}")

    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
