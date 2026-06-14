from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
import re

from django.db.models import Count, Q
from django.utils import timezone

from receipts.models import ProductKeyword

from .models import Product, ProductUsageEvent, RecipeTemplate


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("ё", "е"))


@dataclass(frozen=True)
class ProductPriority:
    product: Product
    score: int
    reasons: tuple[str, ...]


class ProductPriorityService:
    def rank(self, products) -> list[ProductPriority]:
        priorities = [self.evaluate(product) for product in products]
        return sorted(
            priorities,
            key=lambda item: (-item.score, item.product.expiration_date or date.max, item.product.name.lower()),
        )

    def evaluate(self, product: Product) -> ProductPriority:
        today = timezone.localdate()
        score = 0
        reasons: list[str] = []

        if product.expiration_date:
            days_left = (product.expiration_date - today).days
            if days_left < 0:
                score += 120 + min(abs(days_left), 30)
                reasons.append("Срок уже истек")
            elif days_left == 0:
                score += 110
                reasons.append("Истекает сегодня")
            elif days_left == 1:
                score += 100
                reasons.append("Истекает завтра")
            elif days_left <= 3:
                score += 85
                reasons.append("Скоро истекает")
            elif days_left <= 7:
                score += 45
                reasons.append("Срок близко")
        else:
            score += 55
            reasons.append("Нужно уточнить срок")

        if product.status == Product.STATUS_NEEDS_REVIEW:
            score += 35
            if "Нужно уточнить срок" not in reasons:
                reasons.append("Нужно уточнить срок")

        age_days = max((today - product.purchase_date).days, 0)
        if age_days >= 30:
            score += 35
            reasons.append("Давно лежит")
        elif age_days >= 14:
            score += 20
            reasons.append("Давно лежит")

        if product.quantity >= Decimal("5"):
            score += 25
            reasons.append("Много в наличии")
        elif product.quantity >= Decimal("3"):
            score += 12
            reasons.append("Много в наличии")

        return ProductPriority(product=product, score=score, reasons=tuple(reasons[:3]))


@dataclass(frozen=True)
class RecipeSuggestion:
    template: RecipeTemplate
    available: tuple[str, ...]
    expiring: tuple[str, ...]
    missing: tuple[str, ...]
    score: int

    @property
    def can_cook(self) -> bool:
        return not self.missing


class RecipeSuggestionService:
    def __init__(self, user):
        self.user = user

    def suggest(self, include_almost: bool = True) -> list[RecipeSuggestion]:
        products = list(
            Product.objects.filter(user=self.user)
            .select_related("category")
            .exclude(status=Product.STATUS_EXPIRED)
        )
        product_index = self._product_index(products)
        suggestions = []
        for template in RecipeTemplate.objects.filter(is_active=True):
            available, expiring, missing = self._match_template(template, product_index)
            if missing and (not include_almost or len(missing) > 1):
                continue
            if not available:
                continue
            score = len(available) * 20 - len(missing) * 12 + len(expiring) * 35
            if template.prioritize_expiring and expiring:
                score += 25
            suggestions.append(
                RecipeSuggestion(
                    template=template,
                    available=tuple(available),
                    expiring=tuple(expiring),
                    missing=tuple(missing),
                    score=score,
                )
            )
        return sorted(suggestions, key=lambda item: (-item.score, bool(item.missing), item.template.title.lower()))

    def _product_index(self, products: list[Product]) -> list[tuple[Product, str]]:
        keywords = list(ProductKeyword.objects.filter(Q(owner=self.user) | Q(owner__isnull=True), is_food=True))
        index = []
        for product in products:
            pieces = [product.name]
            if product.category:
                pieces.append(product.category.name)
            normalized_product = normalize_name(" ".join(pieces))
            matched_keywords = [keyword.word for keyword in keywords if keyword.word and keyword.word in normalized_product]
            index.append((product, normalize_name(" ".join([normalized_product, *matched_keywords]))))
        return index

    def _match_template(self, template: RecipeTemplate, product_index: list[tuple[Product, str]]):
        today = timezone.localdate()
        available = []
        expiring = []
        missing = []
        for ingredient in template.required_ingredients:
            normalized = normalize_name(str(ingredient))
            matched_product = next((product for product, haystack in product_index if normalized in haystack), None)
            if matched_product:
                available.append(str(ingredient))
                if matched_product.expiration_date and matched_product.expiration_date <= today + timedelta(days=3):
                    expiring.append(str(ingredient))
            else:
                missing.append(str(ingredient))
        return available, expiring, missing


class ProductUsageService:
    def mark(self, product: Product, action: str, quantity: Decimal | None = None) -> ProductUsageEvent:
        if action not in {ProductUsageEvent.ACTION_USED, ProductUsageEvent.ACTION_WASTED}:
            raise ValueError("Unknown usage action.")
        quantity = quantity or product.quantity
        event = ProductUsageEvent.objects.create(
            product=product,
            user=product.user,
            action=action,
            quantity=quantity,
            category_snapshot=product.category.name if product.category else "",
            product_name_snapshot=product.name,
            expiration_date_snapshot=product.expiration_date,
            wasted_expired=action == ProductUsageEvent.ACTION_WASTED
            and product.expiration_date is not None
            and product.expiration_date < timezone.localdate(),
        )
        product.delete()
        return event


class WasteStatsService:
    def __init__(self, user):
        self.user = user

    def build(self) -> dict:
        events = ProductUsageEvent.objects.filter(user=self.user)
        used_count = events.filter(action=ProductUsageEvent.ACTION_USED).count()
        wasted_count = events.filter(action=ProductUsageEvent.ACTION_WASTED).count()
        total = used_count + wasted_count
        waste_percent = round((wasted_count / total) * 100, 1) if total else 0
        wasted_expired_count = events.filter(action=ProductUsageEvent.ACTION_WASTED, wasted_expired=True).count()
        wasted_categories = list(
            events.filter(action=ProductUsageEvent.ACTION_WASTED)
            .exclude(category_snapshot="")
            .values("category_snapshot")
            .annotate(count=Count("id"))
            .order_by("-count", "category_snapshot")[:5]
        )
        top_category = wasted_categories[0]["category_snapshot"] if wasted_categories else ""
        recommendation = ""
        if top_category:
            recommendation = f"Чаще всего выбрасывается категория: {top_category}. Возможно, стоит покупать меньше."
        return {
            "used_count": used_count,
            "wasted_count": wasted_count,
            "wasted_expired_count": wasted_expired_count,
            "waste_percent": waste_percent,
            "wasted_categories": wasted_categories,
            "latest_events": events[:10],
            "recommendation": recommendation,
        }
