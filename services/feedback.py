import re
from dataclasses import dataclass

RATING_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[:=-]\s*([1-5])(?!\d)")


@dataclass(frozen=True)
class ParsedGiftRating:
    gift_index: int
    rating: int


def parse_gift_ratings(feedback_text: str) -> list[ParsedGiftRating]:
    ratings = []

    for match in RATING_PATTERN.finditer(feedback_text):
        gift_index = int(match.group(1))
        rating = int(match.group(2))
        ratings.append(ParsedGiftRating(gift_index=gift_index, rating=rating))

    return ratings


def strip_rating_fragments(feedback_text: str) -> str:
    return RATING_PATTERN.sub("", feedback_text)
