from enum import Enum
import random
from typing import List, NamedTuple


class Suit(Enum):
    NONE = 0
    CLUBS = 1
    DIAMONDS = 2
    HEARTS = 3
    SPADES = 4
    JOKERS = 5


class Card(NamedTuple('Card', [('rank', int), ('suit', Suit)])):
    """Represents a single card."""

    def __str__(self) -> str:
        suit_prefix = ''
        if self.suit == Suit.CLUBS:
            suit_prefix = 'C'
        elif self.suit == Suit.DIAMONDS:
            suit_prefix = 'D'
        elif self.suit == Suit.HEARTS:
            suit_prefix = 'H'
        elif self.suit == Suit.SPADES:
            suit_prefix = 'S'
        else:
            suit_prefix = '?'

        rank_suffix = ''
        rank_mapping = {
            1: 'A',
            11: 'J',
            12: 'Q',
            13: 'K',
            14: 'A',
        }
        if self.rank in rank_mapping:
            rank_suffix = rank_mapping[self.rank]
        else:
            rank_suffix = str(self.rank)

        return suit_prefix + '_' + rank_suffix


Hand = List[Card]
Deck = List[Card]


def standard_deck(include_jokers: bool = False) -> Deck:
    """Creates a standard 52 or 54 card deck.

    """
    deck = []
    for suit in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        for rank in range(2, 15):
            deck.append(Card(suit=suit, rank=rank))

    if include_jokers:
        deck += [Card(suit=Suit.JOKERS, rank=i + 1) for i in range(2)]

    random.shuffle(deck)

    return deck
