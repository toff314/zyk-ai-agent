import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import server


def test_parse_groups_empty():
    assert server._parse_groups(None) == []
    assert server._parse_groups("") == []


def test_parse_groups_splits_and_strips():
    assert server._parse_groups("group-a, group-b ,group-c") == [
        "group-a",
        "group-b",
        "group-c",
    ]


def test_clamp_limit_defaults_and_caps():
    assert server._clamp_limit(None) == 20
    assert server._clamp_limit(0) == 20
    assert server._clamp_limit(-5) == 20
    assert server._clamp_limit(5) == 5
    assert server._clamp_limit(999) == 200


def test_truncate_patch():
    assert server._truncate_patch("short", 10) == "short"
    assert server._truncate_patch("abcdef", 3) == "abc... [truncated]"
    assert server._truncate_patch(None, 10) == ""
