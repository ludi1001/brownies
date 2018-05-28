import copy
from enum import Enum
from typing import List, NamedTuple

from cards import cards


NUM_PLAYERS = 4
NUM_CARDS = 52


class PlayerState(NamedTuple(
    'PlayerState', [('hand', cards.Hand), ('points', int),])):
    pass


class GameAction(Enum):
    NONE = 0
    GAME_START = 1
    GAME_END = 2
    TRICK_END = 3
    PLAYER_MOVE = 4


class GameState(NamedTuple(
    'GameState', [('players', List[PlayerState]),
                  ('current_trick', List[cards.Card]),
                  ('active_player', int),
                  ('hearts_broken', bool),
                  ('game_action', GameAction),
                  ('hands_played', int),])):
    pass


class Player:
    pass


class CLIHumanPlayer(Player):
    def update_state(self, state: GameState, ind: int):
        first_ind = state.active_player - len(state.current_trick)
        if first_ind > 0:
            first_ind += 4

        card_list = [None]*4
        for i, card in enumerate(state.current_trick):
            card_list[(first_ind + i) % 4] = card

        print('==Table==')
        for i, card in enumerate(card_list):
            print('Player {}'.format(i), card)
        print('Points: ', [player.points for player in state.players])

        import time
        if state.game_action == GameAction.TRICK_END:
            print('===Trick End===')
            time.sleep(2)
        print()
        time.sleep(0.5)

    def make_move(self, state: GameState, ind: int) -> cards.Card:
        hand_list = [(str(card), i) for i, card in enumerate(state.players[ind].hand)]
        hand_list = sorted(hand_list)
        print(hand_list)
        #print(hand_list)
        a = input('Card: ')
        return state.players[ind].hand[int(a)]


class RandomPlayer(Player):
    def update_state(self, state: GameState, ind: int):
        pass

    def make_move(self, state: GameState, ind: int) -> cards.Card:
        import random
        card_ind = random.randint(0, len(state.players[ind].hand) - 1)
        return state.players[ind].hand[card_ind]


def is_valid_play(card: cards.Card, current_trick: List[cards.Card],
                  hand: cards.Hand, hearts_broken: bool,
                  hands_played: int) -> bool:
    """Checks whether `card` is a valid card to play."""
    # Check that card is in the hand.
    if card not in hand:
        return False

    if current_trick:
        # Make sure player follows suit if possible.
        if card.suit != current_trick[0].suit:
            for card in hand:
                if card.suit == current_trick[0].suit:
                    return False
    else:
        # Player leads in current trick.

        # At the start of the game, must lead with 2 of clubs.
        if hands_played == 0:
            if card.suit != cards.Suit.CLUBS or card.rank != 2:
                return False

        # Any card is allowed unless hearts is played and hearts has not
        # been broken (unless no other valid plays).
        if card.suit == cards.Suit.HEARTS and not hearts_broken:
            # Check that player has a valid play.
            for card in hand:
                if card.suit != cards.Suit.HEARTS:
                    return False
    return True


def get_winning_card_index(trick: List[cards.Card]) -> int:
    """Determines index of the card that is currently winning."""
    best_index = 0
    for i, card in enumerate(trick):
        if card.suit == trick[0].suit and card.rank > trick[best_index].rank:
            best_index = i
    return best_index


def count_trick_points(trick: List[cards.Card]) -> int:
    """Count the number of points present in trick."""
    points = 0
    for card in trick:
        if card.suit == cards.Suit.HEARTS:
            points += 1
        elif card.suit == cards.Suit.SPADES and card.rank == 12:
            points += 13
    return points


def start_game(players: List[Player]) -> GameState:
    deck = cards.standard_deck()
    cards_per_player = NUM_CARDS // NUM_PLAYERS
    player_states = [
        PlayerState(deck[i:i + cards_per_player], 0)
        for i in range(0, NUM_CARDS, cards_per_player)]

    return GameState(player_states, [], active_player=0, hearts_broken=False,
                     game_action=GameAction.GAME_START, hands_played=0)


def next_state(players: List[Player], game_state: GameState) -> GameState:
    if game_state.game_action == GameAction.GAME_START:
        game_state = _game_start_state(players, game_state)
    elif game_state.game_action == GameAction.PLAYER_MOVE:
        game_state = _player_move_state(players, game_state)
    elif game_state.game_action == GameAction.TRICK_END:
        game_state = _end_trick_state(players, game_state)
    else:
        raise ValueError('Invalid game state.')

    for i, player in enumerate(players):
        # TODO: Mask the state.
        player.update_state(game_state, i)
    return game_state


def _game_start_state(players: List[Player],
                      game_state: GameState) -> GameState:
    """Starts a new game."""
    for i, player in enumerate(game_state.players):
        for card in player.hand:
            if card.suit == cards.Suit.CLUBS and card.rank == 2:
                active_player = i
    return GameState(game_state.players, [], active_player=active_player,
                     hearts_broken=False, game_action=GameAction.PLAYER_MOVE,
                     hands_played=0)


def _player_move_state(players: List[Player],
                       game_state: GameState) -> GameState:
    player_ind = game_state.active_player

    valid_card = False
    while not valid_card:
        card = players[player_ind].make_move(game_state, player_ind)

        # Verify card choice.
        valid_card = is_valid_play(
            card, game_state.current_trick, game_state.players[player_ind].hand,
            game_state.hearts_broken, game_state.hands_played)

    # Check for </3.
    hearts_broken = game_state.hearts_broken or card.suit == cards.Suit.HEARTS

    # Form new trick.
    current_trick = game_state.current_trick + [card]

    # Create new player states.
    player_states = []
    for i, player in enumerate(game_state.players):
        if i == player_ind:
            # Update the player hand.
            new_hand = copy.deepcopy(game_state.players[player_ind].hand)
            new_hand.remove(card)
            player_states.append(PlayerState(new_hand, player.points))
        else:
            player_states.append(player)

    # Update the active player.
    player_ind += 1
    if player_ind >= NUM_PLAYERS:
        player_ind = 0

    # Set action.
    if len(current_trick) == NUM_PLAYERS:
        next_action = GameAction.TRICK_END
    else:
        next_action = GameAction.PLAYER_MOVE

    return GameState(player_states, current_trick, active_player=player_ind,
                     hearts_broken=hearts_broken, game_action=next_action,
                     hands_played=game_state.hands_played)


def _end_trick_state(players: List[Player],
                     game_state: GameState) -> GameState:
    # Figure out who won the trick.
    winning_ind = get_winning_card_index(game_state.current_trick)
    active_player = (game_state.active_player + winning_ind) % NUM_PLAYERS

    # Update points.
    new_points = game_state.players[active_player].points + count_trick_points(
        game_state.current_trick)

    # Check for moonshooting.
    if new_points == 26:
        player_points = [26] * NUM_PLAYERS
        player_points[active_player] = 0
    else:
        player_points = [player.points for player in game_state.players]
        player_points[active_player] = new_points


    # Create new game state.
    player_states = [PlayerState(player.hand, points)
                     for player, points in zip(game_state.players,
                                               player_points)]

    if game_state.hands_played + 1 == NUM_CARDS // NUM_PLAYERS:
        action = GameAction.GAME_END
    else:
        action = GameAction.PLAYER_MOVE

    return GameState(player_states, [], active_player=active_player,
                     hearts_broken=game_state.hearts_broken,
                     game_action=action,
                     hands_played=game_state.hands_played + 1)



if __name__ == '__main__':
    players = [CLIHumanPlayer()] + [RandomPlayer()] * 3
    game_state = start_game(players)
    while game_state.game_action != GameAction.GAME_END:
        game_state = next_state(players, game_state)
