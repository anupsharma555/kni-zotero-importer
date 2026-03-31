from __future__ import annotations

import re

from .models import ResolvedCollection


DEFAULT_COLLECTION_ALIASES = {
    "00 kni - foundational texts & major reviews": "00 KNI- Foundational Texts & Reviews",
    "00 kni - foundational texts & reviews": "00 KNI- Foundational Texts & Reviews",
    "00 kni- foundational texts & major reviews": "00 KNI- Foundational Texts & Reviews",
    "00 kni- foundational texts & reviews": "00 KNI- Foundational Texts & Reviews",
}


def normalize_collection_lookup(value: str) -> str:
    lowered = value.strip().lower()
    lowered = lowered.replace("&", " and ")
    lowered = lowered.replace("–", "-").replace("—", "-")
    lowered = re.sub(r"\s+", " ", lowered)
    lowered = re.sub(r"\s*-\s*", " - ", lowered)
    return lowered.strip()


class CollectionResolver:
    def __init__(self, collections: dict[str, str], aliases: dict[str, str] | None = None) -> None:
        self.collections = collections
        self.aliases = {normalize_collection_lookup(k): v for k, v in (aliases or DEFAULT_COLLECTION_ALIASES).items()}
        self.normalized_to_name: dict[str, str] = {}
        duplicates: set[str] = set()
        for name in collections:
            normalized = normalize_collection_lookup(name)
            if normalized in self.normalized_to_name and self.normalized_to_name[normalized] != name:
                duplicates.add(normalized)
            else:
                self.normalized_to_name[normalized] = name
        for normalized in duplicates:
            self.normalized_to_name.pop(normalized, None)

    def resolve(self, requested_name: str) -> ResolvedCollection:
        if requested_name in self.collections:
            return ResolvedCollection(requested_name=requested_name, resolved_name=requested_name, key=self.collections[requested_name])

        normalized = normalize_collection_lookup(requested_name)
        alias_target = self.aliases.get(normalized)
        if alias_target and alias_target in self.collections:
            return ResolvedCollection(requested_name=requested_name, resolved_name=alias_target, key=self.collections[alias_target])

        direct_target = self.normalized_to_name.get(normalized)
        if direct_target:
            return ResolvedCollection(requested_name=requested_name, resolved_name=direct_target, key=self.collections[direct_target])

        raise ValueError(f"Collection does not match an existing Zotero collection: {requested_name}")
