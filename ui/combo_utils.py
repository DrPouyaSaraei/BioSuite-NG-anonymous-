"""
ui/combo_utils.py
Shared helper to make a QComboBox searchable-as-you-type, case-insensitive
-- e.g. pressing "r" jumps to "Rectum" regardless of case, and typing
further characters narrows the match further (not just the first letter).

Plain (non-editable) QComboBox already does a basic case-insensitive
first-letter keyboard search in Qt by default, but it's easy to lose
focus of / not discover, and only matches from the start of the string.
This helper makes the search explicit, visible (an actual text cursor
the user can type into), and searches ANYWHERE in the item text (not
just the start), which scales much better for a 48-organ / 39-site list.
"""
from __future__ import annotations
from PyQt6.QtWidgets import QComboBox, QCompleter
from PyQt6.QtCore import Qt


def enable_typeahead_search(combo: QComboBox) -> None:
    """Make `combo` searchable by typing -- case-insensitive, matches
    anywhere in the item text, cannot insert new/non-matching values."""
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    combo.setCompleter(completer)

    line_edit = combo.lineEdit()
    if line_edit is not None:
        line_edit.setPlaceholderText("Type to search...")
