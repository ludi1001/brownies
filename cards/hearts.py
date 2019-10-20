import copy
from enum import Enum
import numpy as np
import time
from typing import List, NamedTuple, Set

from cards import cards


NUM_PLAYERS = 4
NUM_CARDS = 52

Hand = Set[cards.Card]


class PlayerState(NamedTuple(
    'PlayerState', [('hand', Hand), ('points', int),])):
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
    def update_state(self, state: GameState, ind: int):
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

        if state.game_action == GameAction.TRICK_END:
            print('===Trick End===')
            time.sleep(2)
        print()
        #time.sleep(0.5)

    def make_move(self, choices: List[cards.Card], state: GameState,
                  ind: int) -> cards.Card:
        hand_list = [(card, i) for i, card in enumerate(state.players[ind].hand)]
        hand_list = sorted(hand_list, key=lambda a: (a[0].suit.value, a[0].rank))
        hand_list = [str(a[0]) for a in hand_list]
        print(hand_list)
        def parse_card():
            legal = False
            while not legal:
                try:
                    card = input('Card: ')
                    suit, rank = card.split('_')

                    if suit == 'C':
                        suit = cards.Suit.CLUBS
                    elif suit == 'D':
                        suit = cards.Suit.DIAMONDS
                    elif suit == 'H':
                        suit = cards.Suit.HEARTS
                    elif suit == 'S':
                        suit = cards.Suit.SPADES

                    rank_mapping = {
                        'A': 14,
                        'K': 13,
                        'Q': 12,
                        'J': 11
                    }
                    if rank in rank_mapping:
                        rank = rank_mapping[rank]
                    else:
                        rank = int(rank)
                    card = cards.Card(rank, suit)
                    legal = True
                except KeyboardInterrupt:
                    raise
                except:
                    print('Bad')
            return card
        return parse_card()


class RandomPlayer(Player):

    def make_move(self, choices: List[cards.Card], state: GameState,
                  ind: int) -> cards.Card:
        import random
        card_ind = random.randint(0, len(choices) - 1)
        return choices[card_ind]


class MonteCarloPlayer(Player):

    def __init__(self, sims):
        self.sims = sims

    def make_move(self, choices: List[cards.Card], state: GameState,
                  ind: int) -> cards.Card:
        sim_time = self.sims

        choices_list = list(choices)
        sim_points = np.zeros(len(choices_list))
        num_sims = np.zeros_like(sim_points)

        start_time = time.time()

        class FakePlayer(RandomPlayer):
            def __init__(self):
                self.iter = 0

            def make_move(self, choices: List[cards.Card], state: GameState,
                          ind: int) -> cards.Card:
                if self.iter == 0:
                    self.iter += 1
                    return self.card
                self.iter += 1
                return super().make_move(choices, state, ind)

            def reset(self, card):
                self.iter = 0
                self.card = card

        players = [RandomPlayer()] * NUM_PLAYERS
        players[ind] = FakePlayer()

        keep_going = True

        while keep_going:
            for i, card in enumerate(choices_list):
                players[ind].reset(card)
                mc_state = state
                while mc_state.game_action != GameAction.GAME_END:
                    mc_state = next_state(players, mc_state)
                sim_points[i] += mc_state.players[ind].points
                num_sims[i] += 1

                if time.time() - start_time >= sim_time:
                    keep_going = False
                    break

        sim_points = sim_points / num_sims
        best_card = choices_list[np.argmin(sim_points)]
        print('DEBUG', num_sims)
        return best_card


def is_valid_play(card: cards.Card, current_trick: List[cards.Card],
                  hand: Hand, hearts_broken: bool,
                  hands_played: int) -> bool:
    """Checks whether `card` is a valid card to play."""
    # Check that card is in the hand.
    if card not in hand:
        return False

    if current_trick:
        if hands_played == 0:
            # No point cards in first hand.
            if (card.suit == cards.Suit.HEARTS or
                (card.suit == cards.Suit.SPADES and card.rank == 12)):
                return False

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
        PlayerState(set(deck[i:i + cards_per_player]), 0)
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
        # Compute all valid cards to play.
        valid_cards = []
        for card in game_state.players[player_ind].hand:
            if is_valid_play(
                card, game_state.current_trick,
                game_state.players[player_ind].hand,
                game_state.hearts_broken, game_state.hands_played):
                valid_cards.append(card)

        card = players[player_ind].make_move(valid_cards, game_state,
                                             player_ind)

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
    think_time = 6
    players = [CLIHumanPlayer(), MonteCarloPlayer(think_time),
               MonteCarloPlayer(think_time), MonteCarloPlayer(think_time)]
    import numpy as np
    cum_points = np.zeros(4)
    for i in range(1000):
        game_state = start_game(players)
        while game_state.game_action != GameAction.GAME_END:
            game_state = next_state(players, game_state)
        points = [game_state.players[i].points for i in range(4)]
        print('Game ', i, points)
        cum_points += np.array(points)
        print(cum_points/(i+1))
