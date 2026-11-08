# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Integration tests for the bundled language server."""

import pytest

from .lsp_test_client import constants, defaults, session, utils

TEST_FILE_URI = utils.as_uri(str(constants.TEST_DATA / "sample1" / "sample.py"))


@pytest.mark.parametrize(
    ("contents", "expected_labels"),
    [
        ("value = hello.\n", ["anh", "baby"]),
        ("value = other.\n", []),
    ],
)
def test_completion_suggestions(contents, expected_labels):
    """The server suggests completion items only after the configured trigger text."""
    with session.LspSession() as ls_session:
        ls_session.initialize(defaults.VSCODE_DEFAULT_INITIALIZE)
        ls_session.notify_did_open(
            {
                "textDocument": {
                    "uri": TEST_FILE_URI,
                    "languageId": "python",
                    "version": 1,
                    "text": contents,
                }
            }
        )
        actual = ls_session.text_document_completion(
            {
                "textDocument": {"uri": TEST_FILE_URI},
                "position": {"line": 0, "character": len(contents.rstrip())},
            }
        )

    assert [item["label"] for item in actual] == expected_labels
