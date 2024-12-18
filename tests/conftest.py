"""See full diffs in pytest.

:author: Shay Hill
:created: `!v strftime("%Y-%m-%d")`
"""

from typing import Any

def pytest_assertrepr_compare(config: Any, op: str, left: str, right: str):
    """See full error diffs"""
    if op in ("==", "!="):
        return ["{0} {1} {2}".format(left, op, right)]
