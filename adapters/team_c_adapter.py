"""Simple Team C adapter: ontology loader + lightweight reasoning helpers.

This module provides a small, deterministic semantic classifier suitable for
demoing Team C integration (ontology-based classification, ancestor reasoning,
and equivalent term lookup). It is intentionally self-contained and offline.
"""
import json
import os
from typing import Dict, List, Set

_ONTOLOGY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "team_c_ontology.json")


class TeamCAdapter:
    def __init__(self, ontology_path: str = None):
        self.ontology_path = ontology_path or _ONTOLOGY_PATH
        self.ontology = self._load_ontology()
        self._build_reverse_maps()

    def _load_ontology(self) -> Dict:
        try:
            with open(self.ontology_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Fallback to a minimal ontology if the file is missing
            return {"classes": {}}

    def _build_reverse_maps(self):
        self.parents = {}
        self.equivalents = {}
        self.tags = {}
        classes = self.ontology.get("classes", {})
        for cls, props in classes.items():
            self.parents[cls] = props.get("parents", [])
            for eq in props.get("equivalent", []):
                self.equivalents.setdefault(eq, []).append(cls)
            for tag in props.get("tags", []):
                self.tags.setdefault(cls, []).append(tag)

    def _ancestors(self, cls_name: str) -> Set[str]:
        """Return the set of ancestors (including the class itself)."""
        seen = set()
        stack = [cls_name]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            for p in self.parents.get(cur, []):
                stack.append(p)
        return seen

    def resolve_equivalents(self, term: str) -> List[str]:
        """Return candidate class names that are equivalent to term.

        The ontology lists equivalents as class synonyms; we treat either
        a direct class name or an equivalent name as a match.
        """
        matches = []
        classes = self.ontology.get("classes", {})
        # Direct match
        if term in classes:
            matches.append(term)
        # Equivalent match
        for cls, props in classes.items():
            if term in props.get("equivalent", []):
                matches.append(cls)
        # Also check lowercase variants
        low = term.lower()
        for cls in classes:
            if cls.lower() == low:
                matches.append(cls)
        return list(dict.fromkeys(matches))

    def classify_data(self, data_type: str) -> Dict[str, object]:
        """Classify a data type string using the ontology.

        Returns a dict with discovered classes, ancestor chain, and semantic tags.
        """
        if not data_type:
            return {"classes": [], "ancestors": [], "tags": []}

        # Try to resolve by class name or equivalent
        candidates = self.resolve_equivalents(data_type)
        classes = set()
        tags = set()
        for c in candidates:
            classes.add(c)
            for a in self._ancestors(c):
                classes.add(a)
            for t in self.tags.get(c, []):
                tags.add(t)

        # If no candidate found, attempt substring heuristics
        if not classes:
            low = data_type.lower()
            for cls, props in self.ontology.get("classes", {}).items():
                if cls.lower() in low or any(eq.lower() in low for eq in props.get("equivalent", [])):
                    classes.add(cls)
                    for a in self._ancestors(cls):
                        classes.add(a)
                    for t in props.get("tags", []):
                        tags.add(t)

        return {
            "input": data_type,
            "classes": sorted(list(classes)),
            "ancestors": sorted(list(classes)),
            "tags": sorted(list(tags))
        }


def get_adapter() -> TeamCAdapter:
    return TeamCAdapter()


if __name__ == "__main__":
    a = TeamCAdapter()
    print(json.dumps(a.classify_data("Diagnosis"), indent=2))
