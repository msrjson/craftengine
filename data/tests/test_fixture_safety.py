"""The suite preserves every record it did not create in a throwaway database.

NR-02 forbids physical deletion and destructive DDL in every environment, the
test environment included. On PostgreSQL the suite runs in a database created
for the session and never dropped; this test keeps the tests themselves from
deleting, truncating or dropping anything.

A line may still carry such a statement when it cannot touch a shared
database - a hostile payload given to a validator as a string, or a statement
on a private in-memory SQLite connection. Such a line ends with a
`# nr02: <reason>` comment, so every exception is visible and justified where
it is written.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import re

import pytest

TESTS = os.path.dirname(os.path.abspath(__file__))

DESTRUCTIVE = re.compile(
    r"\bDELETE\s+FROM\b|\bTRUNCATE\b|\bDROP\s+(?:TABLE|ROLE|OWNED|SCHEMA|DATABASE|POLICY|INDEX|VIEW)\b"
    # `.delete()` with no argument is the ORM; with one it is an HTTP verb, a
    # storage path or a policy ability, none of which touch a table.
    r"|\.delete\(\s*\)|\.truncate\(|\.force_delete\(|\.drop_table\(|\.drop_if_exists\(|\.drop_column\(",
    re.IGNORECASE,
)
EXEMPTION = re.compile(r"#\s*nr02:\s*\S")


def _offending_lines():
    for name in sorted(os.listdir(TESTS)):
        if not name.endswith(".py") or name == os.path.basename(__file__):
            continue
        with open(os.path.join(TESTS, name), encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                if DESTRUCTIVE.search(line) and not EXEMPTION.search(line):
                    yield ":".join((name, str(number)))


def test_no_test_deletes_truncates_or_drops():
    assert list(_offending_lines()) == []


@pytest.mark.parametrize("line", [
    'DB.statement("DELETE FROM users WHERE id = ?", [1])',
    "schema.drop_table('gadgets')",
    'DB.table("jobs").delete()',
    "user.delete()",
    "Note.force_delete()",
])
def test_the_scan_recognises_destructive_statements(line):
    assert DESTRUCTIVE.search(line)


@pytest.mark.parametrize("line", ['Route.delete("/things", destroy)', 'Storage.delete("avatar.png")'])
def test_http_verbs_and_storage_are_not_deletions(line):
    assert not DESTRUCTIVE.search(line)


def test_a_justified_line_is_exempt():
    assert EXEMPTION.search("'; DROP TABLE users --'  # nr02: hostile payload, never executed")
