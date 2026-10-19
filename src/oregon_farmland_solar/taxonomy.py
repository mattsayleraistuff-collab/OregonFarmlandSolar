"""Load and validate the reason taxonomy (data/taxonomy/reasons.yaml)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

CATCH_ALL_ID = "other_uncoded"
_ID_RE = re.compile(r"[a-z][a-z0-9_]*")
_STATUSES = {"active", "deprecated"}


class TaxonomyError(ValueError):
    """The taxonomy file is malformed or internally inconsistent."""


@dataclass(frozen=True)
class Entry:
    """One reason category.

    Attributes:
        id: Stable lower snake_case id. Never renamed or reused.
        label: Short display name.
        definition: What belongs in this category.
        status: "active" or "deprecated".
        replaced_by: Id of the entry that supersedes a deprecated one.
    """

    id: str
    label: str
    definition: str
    status: str
    replaced_by: str | None = None


@dataclass(frozen=True)
class Taxonomy:
    """A loaded, validated reason taxonomy.

    Attributes:
        version: Taxonomy version number from the file.
        entries: All entries, active and deprecated.
    """

    version: int
    entries: tuple[Entry, ...]

    def ids(self) -> set[str]:
        """Returns the ids of all entries, including deprecated ones."""
        return {e.id for e in self.entries}

    def active_ids(self) -> set[str]:
        """Returns the ids of entries that may be used for new coding."""
        return {e.id for e in self.entries if e.status == "active"}

    def get(self, entry_id: str) -> Entry | None:
        """Returns the entry with the given id, or None if there is none."""
        return next((e for e in self.entries if e.id == entry_id), None)


def load_taxonomy(path: str | Path) -> Taxonomy:
    """Loads and validates a taxonomy YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        The validated Taxonomy.

    Raises:
        TaxonomyError: If the file is malformed, has duplicate or badly formed ids, an
            invalid status, a deprecated entry without a valid ``replaced_by``, or lacks
            the catch-all ``other_uncoded`` entry.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "entries" not in raw or "version" not in raw:
        raise TaxonomyError("taxonomy must be a mapping with 'version' and 'entries'")

    entries: list[Entry] = []
    seen: set[str] = set()
    for item in raw["entries"]:
        missing = {"id", "label", "definition", "status"} - set(item)
        if missing:
            raise TaxonomyError(f"entry {item.get('id', '?')!r} missing fields: {sorted(missing)}")
        entry = Entry(
            id=str(item["id"]),
            label=str(item["label"]),
            definition=str(item["definition"]),
            status=str(item["status"]),
            replaced_by=item.get("replaced_by"),
        )
        if not _ID_RE.fullmatch(entry.id):
            raise TaxonomyError(f"invalid id {entry.id!r}: use lower snake_case")
        if entry.status not in _STATUSES:
            raise TaxonomyError(f"entry {entry.id!r} has invalid status {entry.status!r}")
        if entry.id in seen:
            raise TaxonomyError(f"duplicate id {entry.id!r}")
        seen.add(entry.id)
        entries.append(entry)

    for entry in entries:
        if entry.status == "deprecated":
            if entry.replaced_by is None or entry.replaced_by not in seen:
                raise TaxonomyError(
                    f"deprecated entry {entry.id!r} needs replaced_by pointing to an existing id"
                )
    if CATCH_ALL_ID not in seen:
        raise TaxonomyError(f"taxonomy must include the catch-all id {CATCH_ALL_ID!r}")

    return Taxonomy(version=int(raw["version"]), entries=tuple(entries))
