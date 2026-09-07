"""Deterministic semantic duplicate and uniqueness validator for object registry."""

import json
from pathlib import Path

from pydantic import BaseModel


class DuplicateCheckResult(BaseModel):
    """Result of semantic duplicate check against Object Registry."""

    is_duplicate: bool
    candidate_name: str
    matched_object_id: str | None = None
    matched_canonical_name: str | None = None
    matched_display_name: str | None = None
    matched_reserved_by: str | None = None
    match_type: str | None = None  # EXACT_CANONICAL | SYNONYM | COMPOUND_VARIANT | FUZZY_STRING
    similarity_score: float = 0.0
    reason: str


class ObjectRegistryValidator:
    """Validator enforcing Zero Duplicate Object Policy using the frozen Semantic Object Registry."""

    def __init__(self, registry_path: str | Path):
        self.registry_path = Path(registry_path)
        self.objects_by_canonical: dict[str, dict] = {}
        self.synonym_map: dict[str, str] = {}
        self.compound_map: dict[str, str] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Object registry not found at: {self.registry_path}")

        with open(self.registry_path, encoding="utf-8") as f:
            data = json.load(f)

        for obj in data.get("objects", []):
            canonical = obj["canonical_name"].lower().strip()
            self.objects_by_canonical[canonical] = obj

            # Map synonyms to canonical
            for syn in obj.get("synonyms", []):
                self.synonym_map[syn.lower().strip()] = canonical

            # Map compound variants to canonical
            for comp in obj.get("compound_variants", []):
                self.compound_map[comp.lower().strip()] = canonical

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return ObjectRegistryValidator._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row: list[int] = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def _similarity_ratio(s1: str, s2: str) -> float:
        dist = ObjectRegistryValidator._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        return 1.0 - (dist / max_len) if max_len > 0 else 1.0

    def check_object(
        self, candidate_name: str, requesting_page_id: str | None = None
    ) -> DuplicateCheckResult:
        """Check if a candidate object name duplicates an existing registered object.

        Args:
            candidate_name: Name of the object to validate (e.g. "red apple", "toy car", "banana").
            requesting_page_id: Current page requesting the object (e.g. "P005" or "category_page_005").

        Returns:
            DuplicateCheckResult indicating duplicate status and matched details.
        """
        clean_name = candidate_name.lower().strip()

        # 1. Exact Canonical Match
        if clean_name in self.objects_by_canonical:
            obj = self.objects_by_canonical[clean_name]
            reserved_by = obj.get("reserved_by", "")

            # If requested by the designated page, it is valid and allowed
            if requesting_page_id and (
                requesting_page_id.lower() in reserved_by.lower()
                or reserved_by.lower() in requesting_page_id.lower()
            ):
                return DuplicateCheckResult(
                    is_duplicate=False,
                    candidate_name=candidate_name,
                    matched_object_id=obj["object_id"],
                    matched_canonical_name=obj["canonical_name"],
                    matched_display_name=obj["display_name"],
                    matched_reserved_by=reserved_by,
                    match_type="AUTHORIZED_ASSIGNMENT",
                    similarity_score=1.0,
                    reason=f"Candidate '{candidate_name}' is authorized for assigned page '{requesting_page_id}'.",
                )

            return DuplicateCheckResult(
                is_duplicate=True,
                candidate_name=candidate_name,
                matched_object_id=obj["object_id"],
                matched_canonical_name=obj["canonical_name"],
                matched_display_name=obj["display_name"],
                matched_reserved_by=reserved_by,
                match_type="EXACT_CANONICAL",
                similarity_score=1.0,
                reason=f"Exact match with registered canonical object '{obj['canonical_name']}' (Reserved by {reserved_by}).",
            )

        # 2. Synonym Map Match
        if clean_name in self.synonym_map:
            canonical = self.synonym_map[clean_name]
            obj = self.objects_by_canonical[canonical]
            return DuplicateCheckResult(
                is_duplicate=True,
                candidate_name=candidate_name,
                matched_object_id=obj["object_id"],
                matched_canonical_name=obj["canonical_name"],
                matched_display_name=obj["display_name"],
                matched_reserved_by=obj.get("reserved_by"),
                match_type="SYNONYM",
                similarity_score=0.95,
                reason=f"Candidate '{candidate_name}' is a recognized synonym for canonical '{canonical}'.",
            )

        # 3. Compound Variant Match
        if clean_name in self.compound_map:
            canonical = self.compound_map[clean_name]
            obj = self.objects_by_canonical[canonical]
            return DuplicateCheckResult(
                is_duplicate=True,
                candidate_name=candidate_name,
                matched_object_id=obj["object_id"],
                matched_canonical_name=obj["canonical_name"],
                matched_display_name=obj["display_name"],
                matched_reserved_by=obj.get("reserved_by"),
                match_type="COMPOUND_VARIANT",
                similarity_score=0.90,
                reason=f"Candidate '{candidate_name}' is a compound variant of canonical '{canonical}'.",
            )

        # 4. Fuzzy Levenshtein Match on all canonicals (threshold >= 0.85)
        best_match = None
        highest_similarity = 0.0
        for canonical, obj in self.objects_by_canonical.items():
            sim = self._similarity_ratio(clean_name, canonical)
            if sim > highest_similarity:
                highest_similarity = sim
                best_match = obj

        if highest_similarity >= 0.85 and best_match:
            return DuplicateCheckResult(
                is_duplicate=True,
                candidate_name=candidate_name,
                matched_object_id=best_match["object_id"],
                matched_canonical_name=best_match["canonical_name"],
                matched_display_name=best_match["display_name"],
                matched_reserved_by=best_match.get("reserved_by"),
                match_type="FUZZY_STRING",
                similarity_score=round(highest_similarity, 3),
                reason=f"High string similarity ({round(highest_similarity * 100, 1)}%) to registered object '{best_match['canonical_name']}'.",
            )

        # No duplicate detected
        return DuplicateCheckResult(
            is_duplicate=False,
            candidate_name=candidate_name,
            matched_object_id=None,
            matched_canonical_name=None,
            matched_display_name=None,
            matched_reserved_by=None,
            match_type=None,
            similarity_score=round(highest_similarity, 3),
            reason=f"Candidate '{candidate_name}' is unique and does not collide with registered vocabulary.",
        )
