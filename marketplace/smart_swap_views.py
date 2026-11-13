
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Product
import re


def get_keywords(product):
    text = f"{product.title} {product.description}".lower()
    return set(re.findall(r"[a-z0-9]+", text))


def calculate_match(offer, requested):
    score = 0
    reasons = []

    # Category compatibility: 30 points
    if offer.category == requested.category:
        score += 30
        reasons.append("Same product category")

    # Price similarity: 30 points
    if offer.price == 0 and requested.price == 0:
        price_score = 30
    else:
        highest = max(float(offer.price), float(requested.price), 1)
        difference = abs(float(offer.price) - float(requested.price))
        price_score = max(0, 30 * (1 - difference / highest))

    score += price_score
    if price_score >= 20:
        reasons.append("Similar price range")

    # Condition compatibility: 15 points
    condition_values = {
        "new": 4,
        "like_new": 3,
        "good": 2,
        "used": 1,
    }

    first = condition_values.get(offer.condition, 1)
    second = condition_values.get(requested.condition, 1)
    condition_score = 15 * (1 - abs(first - second) / 3)

    score += condition_score
    if condition_score >= 10:
        reasons.append("Similar product condition")

    # Keyword similarity: 25 points
    first_words = get_keywords(offer)
    second_words = get_keywords(requested)

    common = first_words.intersection(second_words)
    total = first_words.union(second_words)

    keyword_score = (len(common) / len(total) * 25) if total else 0
    score += keyword_score

    if common:
        reasons.append("Matching product keywords")

    return {
        "score": round(score),
        "reasons": reasons,
        "offer": offer,
        "requested": requested,
    }


@login_required
def smart_swap(request):
    my_products = Product.objects.filter(
        owner=request.user,
        is_available=True,
        listing_type__in=["swap", "both"]
    )

    matches = []

    for my_product in my_products:
        other_products = Product.objects.filter(
            is_available=True,
            listing_type__in=["swap", "both"]
        ).exclude(owner=request.user)

        for other_product in other_products:
            result = calculate_match(my_product, other_product)

            if result["score"] >= 25:
                matches.append(result)

    matches.sort(key=lambda item: item["score"], reverse=True)

    return render(
        request,
        "marketplace/smart_swap.html",
        {
            "matches": matches,
            "my_products": my_products,
        }
    )
