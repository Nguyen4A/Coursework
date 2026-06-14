from dataclasses import dataclass
from difflib import SequenceMatcher

from django.db.models import Q

from .models import ShelfLifeRule


@dataclass(frozen=True)
class ShelfLifeSuggestion:
    days: int
    rule_name: str
    score: float


class ShelfLifeService:
    def __init__(self, user):
        self.user = user

    def suggest(self, product_name: str) -> ShelfLifeSuggestion | None:
        name = product_name.strip().lower()
        if not name:
            return None

        exact = self._exact_match(name)
        if exact:
            return ShelfLifeSuggestion(exact.shelf_life_days, exact.product_name, 1.0)

        candidates = list(
            ShelfLifeRule.objects.filter(Q(owner=self.user) | Q(owner__isnull=True), is_active=True)
            .order_by("-owner_id", "product_name")[:500]
        )
        scored = sorted(
            ((self._score(name, rule), rule) for rule in candidates),
            key=lambda item: item[0],
            reverse=True,
        )
        useful = [(score, rule) for score, rule in scored if score >= 0.34][:5]
        if not useful:
            return None

        score, best = useful[0]
        return ShelfLifeSuggestion(best.shelf_life_days, best.product_name, score)

    def _exact_match(self, name: str):
        user_rule = ShelfLifeRule.objects.filter(owner=self.user, is_active=True, product_name__iexact=name).first()
        if user_rule:
            return user_rule
        return ShelfLifeRule.objects.filter(owner__isnull=True, is_active=True, product_name__iexact=name).first()

    def _score(self, name: str, rule: ShelfLifeRule) -> float:
        haystack = " ".join([rule.product_name, rule.description, rule.category, rule.tags]).lower()
        direct = SequenceMatcher(None, name, rule.product_name.lower()).ratio()
        tokens = set(name.split())
        target_tokens = set(haystack.split())
        overlap = len(tokens & target_tokens) / max(len(tokens), 1)
        return max(direct, overlap)
