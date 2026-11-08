"""Headless, seeded Catan rules shared by the GUI and simulations.

Public actions validate before mutating. Clients select decisions; they never pay
costs, award points, or edit board occupancy themselves.
"""
from collections import Counter
from numbers import Integral
import numpy as np
from board import catanBoard
from player import RESOURCES

COSTS = {
    'ROAD': {'BRICK': 1, 'WOOD': 1},
    'SETTLE': {'BRICK': 1, 'WOOD': 1, 'WHEAT': 1, 'SHEEP': 1},
    'CITY': {'ORE': 3, 'WHEAT': 2},
    'DEV': {'ORE': 1, 'WHEAT': 1, 'SHEEP': 1},
}


class RuleError(ValueError):
    """An action was rejected without changing game state."""


class GameEngine:
    def __init__(self, players, seed=None, target=10):
        if len(players) not in (3, 4) or len({id(p) for p in players}) != len(players):
            raise ValueError('Use three or four distinct players.')
        if target < 3:
            raise ValueError('Victory target must be at least three.')
        self.players = list(players)
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.board = catanBoard(self.rng)
        self.bank = dict.fromkeys(RESOURCES, 19)
        self.target = target
        self.turn = 0
        self.current_index = 0
        self.phase = 'setup_settlement'
        self.setup_order = list(range(len(players))) + list(reversed(range(len(players))))
        self.setup_index = 0
        self.pending_discards = {}
        self.free_roads = 0
        self.resume_phase = 'main'
        self.last_roll = None
        self.winner = None
        self.events = []

    @property
    def current(self):
        return self.players[self.current_index]

    def require(self, condition, message):
        if not condition:
            raise RuleError(message)

    def actor(self, p, phases):
        self.require(p is self.current and self.phase in phases, 'Action not allowed in this turn/phase.')

    def can_pay(self, p, cost):
        return all(p.resources[r] >= n for r, n in cost.items())

    def pay(self, p, cost):
        for r, n in cost.items():
            p.resources[r] -= n
            self.bank[r] += n

    def give(self, p, resource, amount):
        self.bank[resource] -= amount
        p.resources[resource] += amount

    def legal_builds(self, p, kind):
        if p is not self.current:
            return {}
        if kind == 'SETTLE' and p.settlementsLeft:
            if self.phase == 'setup_settlement':
                return self.board.get_setup_settlements(p)
            if self.phase == 'main':
                return self.board.get_potential_settlements(p)
        if kind == 'CITY' and p.citiesLeft and self.phase == 'main':
            return self.board.get_potential_cities(p)
        if kind == 'ROAD' and p.roadsLeft:
            if self.phase == 'setup_road':
                return self.board.get_setup_roads(p)
            if self.phase in ('main', 'free_roads'):
                return self.board.get_potential_roads(p)
        return {}

    def build(self, p, kind, location):
        self.actor(p, ('setup_settlement', 'setup_road', 'main', 'free_roads'))
        choices = self.legal_builds(p, kind)
        if kind == 'ROAD' and location not in choices and isinstance(location, tuple):
            location = tuple(reversed(location))
        self.require(location in choices, 'Illegal building location or no pieces remaining.')
        setup = self.phase.startswith('setup')
        free = setup or self.phase == 'free_roads'
        self.require(free or self.can_pay(p, COSTS[kind]), 'Insufficient resources.')
        if not free:
            self.pay(p, COSTS[kind])
        if kind == 'ROAD':
            p.buildGraph['ROADS'].append(location)
            self.board.updateBoardGraph_road(*location, p)
        elif kind == 'SETTLE':
            p.buildGraph['SETTLEMENTS'].append(location)
            self.board.updateBoardGraph_settlement(location, p)
            port = self.board.boardGraph[location].port
            if port and port not in p.portList:
                p.portList.append(port)
        else:
            p.buildGraph['CITIES'].append(location)
            self.board.updateBoardGraph_city(location, p)
        self.events.append(f'{p.name} built {kind.lower()}.')
        self.update_awards()
        if setup:
            if kind == 'SETTLE':
                self.phase = 'setup_road'
                if self.setup_index >= len(self.players):
                    for h in self.board.boardGraph[location].adjacentHexList:
                        resource = self.board.hexTileDict[h].resource.type
                        if resource in self.bank:
                            self.give(p, resource, 1)
            else:
                self.setup_index += 1
                if self.setup_index == len(self.setup_order):
                    self.current_index = 0
                    self.phase = 'roll'
                    self.turn = 1
                else:
                    self.current_index = self.setup_order[self.setup_index]
                    self.phase = 'setup_settlement'
        elif self.phase == 'free_roads':
            self.free_roads -= 1
            if not self.free_roads or not self.legal_builds(p, 'ROAD'):
                self.free_roads = 0
                self.phase = self.resume_phase
        self.check_winner()

    def update_awards(self):
        for p in self.players:
            p.maxRoadLength = p.get_road_length(self.board)
        for value, flag, minimum in [('maxRoadLength', 'longestRoadFlag', 5),
                                     ('knightsPlayed', 'largestArmyFlag', 3)]:
            holder = next((p for p in self.players if getattr(p, flag)), None)
            maximum = max(getattr(p, value) for p in self.players)
            leaders = [p for p in self.players if getattr(p, value) == maximum]
            winner = None
            if maximum >= minimum:
                winner = holder if holder in leaders else leaders[0] if len(leaders) == 1 else None
            for p in self.players:
                setattr(p, flag, p is winner)

    def check_winner(self):
        if not self.phase.startswith('setup') and self.current.victoryPoints >= self.target:
            self.winner = self.current
            self.phase = 'finished'
        return self.winner

    def roll(self, p):
        self.actor(p, ('roll',))
        self.last_roll = int(self.rng.integers(1, 7) + self.rng.integers(1, 7))
        self.events.append(f'{p.name} rolled {self.last_roll}.')
        self.resolve_roll(self.last_roll)
        return self.last_roll

    def resolve_roll(self, number):
        """Resolve a supplied dice result (also useful for deterministic scenarios)."""
        self.require(self.phase == 'roll' and isinstance(number, Integral) and not isinstance(number, bool) and 2 <= number <= 12,
                     'Invalid roll or phase.')
        if number == 7:
            self.pending_discards = {p: sum(p.resources.values()) // 2 for p in self.players
                                     if sum(p.resources.values()) > 7}
            self.phase = 'discard' if self.pending_discards else 'robber'
            self.resume_phase = 'main'
            return
        claims = {r: {} for r in RESOURCES}
        for p in self.players:
            for kind, count in [('SETTLEMENTS', 1), ('CITIES', 2)]:
                for v in p.buildGraph[kind]:
                    for h in self.board.boardGraph[v].adjacentHexList:
                        tile = self.board.hexTileDict[h]
                        if tile.resource.num == number and not tile.robber:
                            amounts = claims[tile.resource.type]
                            amounts[p] = amounts.get(p, 0) + count
        for r, amounts in claims.items():
            if sum(amounts.values()) <= self.bank[r]:
                for p, n in amounts.items():
                    self.give(p, r, n)
            elif len(amounts) == 1:
                self.give(next(iter(amounts)), r, self.bank[r])
        self.phase = 'main'

    def discard(self, p, cards):
        self.require(self.phase == 'discard' and p in self.pending_discards, 'No discard due.')
        self.validate_bundle(cards)
        self.require(sum(cards.values()) == self.pending_discards[p] and self.can_pay(p, cards),
                     'Discard exactly half your cards, rounded down, from your hand.')
        self.pay(p, cards)
        del self.pending_discards[p]
        if not self.pending_discards:
            self.phase = 'robber'

    def move_robber(self, p, hex_index, victim=None):
        self.actor(p, ('robber',))
        self.require(hex_index in self.board.get_robber_spots(), 'Move to a different hex.')
        victims = self.board.get_players_to_rob(hex_index, p)
        self.require(victim in victims if victims else victim is None, 'Choose an eligible opponent.')
        self.board.updateBoardGraph_robber(hex_index)
        if victim is not None:
            hand = [r for r, n in victim.resources.items() for _ in range(n)]
            resource = hand[int(self.rng.integers(len(hand)))]
            victim.resources[resource] -= 1
            p.resources[resource] += 1
        self.phase = self.resume_phase
        self.events.append(f'{p.name} moved the robber' + (f' and robbed {victim.name}.' if victim else '.'))
        self.check_winner()

    def buy_dev(self, p):
        self.actor(p, ('main',))
        deck = [c for c, n in self.board.devCardStack.items() for _ in range(n)]
        self.require(bool(deck) and self.can_pay(p, COSTS['DEV']), 'No cards left or insufficient resources.')
        card = deck[int(self.rng.integers(len(deck)))]
        self.pay(p, COSTS['DEV'])
        self.board.devCardStack[card] -= 1
        if card == 'VP':
            p.devCards[card] += 1
        else:
            p.newDevCards.append(card)
        self.events.append(f'{p.name} bought a development card.')
        self.check_winner()
        return card

    def play_dev(self, p, card, resources=()):
        self.actor(p, ('roll', 'main'))
        self.require(card in p.devCards and card != 'VP' and p.devCards[card] > 0
                     and not p.devCardPlayedThisTurn, 'No eligible development card.')
        if card == 'YEAROFPLENTY':
            self.require(len(resources) == min(2, sum(self.bank.values())), 'Choose two available bank cards (or all if fewer).')
            counts = Counter(resources)
            self.require(all(r in self.bank and self.bank[r] >= n for r, n in counts.items()), 'Resources unavailable in bank.')
        elif card == 'MONOPOLY':
            self.require(len(resources) == 1 and resources[0] in RESOURCES, 'Choose one resource.')
        elif card == 'ROADBUILDER':
            self.require(p.roadsLeft > 0 and bool(self.board.get_potential_roads(p)), 'No road can be built.')
        p.devCards[card] -= 1
        p.playedDevCards[card] += 1
        p.devCardPlayedThisTurn = True
        self.events.append(f'{p.name} played {card}.')
        self.resume_phase = self.phase
        if card == 'KNIGHT':
            p.knightsPlayed += 1
            self.phase = 'robber'
            self.update_awards()
        elif card == 'ROADBUILDER':
            self.free_roads = min(2, p.roadsLeft)
            self.phase = 'free_roads'
        elif card == 'YEAROFPLENTY':
            for r, n in counts.items():
                self.give(p, r, n)
        elif card == 'MONOPOLY':
            r = resources[0]
            for other in self.players:
                if other is not p:
                    p.resources[r] += other.resources[r]
                    other.resources[r] = 0
        self.check_winner()

    def trade_ratio(self, p, resource):
        return 2 if '2:1 ' + resource in p.portList else 3 if '3:1 PORT' in p.portList else 4

    def trade_bank(self, p, give, receive):
        self.actor(p, ('main',))
        self.require(give in RESOURCES and receive in RESOURCES and give != receive, 'Choose different resources.')
        ratio = self.trade_ratio(p, give)
        self.require(p.resources[give] >= ratio and self.bank[receive] > 0, 'Insufficient hand or bank supply.')
        self.pay(p, {give: ratio})
        self.give(p, receive, 1)
        self.events.append(f'{p.name} traded {ratio} {give} for {receive}.')

    def validate_bundle(self, bundle):
        self.require(isinstance(bundle, dict) and bool(bundle) and
                     all(r in RESOURCES and type(n) is int and n > 0 for r, n in bundle.items()),
                     'Specify positive integer amounts of valid resources.')

    def trade_players(self, p, other, give, receive, accepted=False):
        self.actor(p, ('main',))
        self.require(other in self.players and other is not p, 'Choose another player.')
        self.validate_bundle(give)
        self.validate_bundle(receive)
        self.require(not set(give) & set(receive), 'Do not exchange the same resource both ways.')
        self.require(self.can_pay(p, give) and self.can_pay(other, receive), 'Trade exceeds available cards.')
        if not accepted:
            return False
        for r, n in give.items():
            p.resources[r] -= n
            other.resources[r] += n
        for r, n in receive.items():
            other.resources[r] -= n
            p.resources[r] += n
        self.events.append(f'{p.name} and {other.name} agreed to a trade.')
        return True

    def end_turn(self, p):
        self.actor(p, ('main',))
        if self.check_winner():
            return
        self.current_index = (self.current_index + 1) % len(self.players)
        self.turn += 1
        self.current.updateDevCards()
        self.current.devCardPlayedThisTurn = False
        self.last_roll = None
        self.phase = 'roll'
        self.check_winner()

    def assert_invariants(self):
        """Detect resource, piece, deck, and graph drift during tests/simulation."""
        for r in RESOURCES:
            assert self.bank[r] >= 0
            assert all(p.resources[r] >= 0 for p in self.players)
            assert self.bank[r] + sum(p.resources[r] for p in self.players) == 19
        totals = {'KNIGHT': 14, 'VP': 5, 'MONOPOLY': 2, 'ROADBUILDER': 2, 'YEAROFPLENTY': 2}
        for c, total in totals.items():
            assert self.board.devCardStack[c] >= 0
            assert self.board.devCardStack[c] + sum(p.devCards[c] + p.newDevCards.count(c)
                     + p.playedDevCards[c] for p in self.players) == total
        for p in self.players:
            assert p.roadsLeft >= 0 and p.citiesLeft >= 0 and p.settlementsLeft >= 0
            assert len({frozenset(e) for e in p.buildGraph['ROADS']}) == len(p.buildGraph['ROADS'])
            for a, b in p.buildGraph['ROADS']:
                for v, w in [(a, b), (b, a)]:
                    node = self.board.boardGraph[v]
                    assert node.edgeState[node.edgeList.index(w)] == [p, True]
            for kind, flag in [('SETTLEMENTS', 'Settlement'), ('CITIES', 'City')]:
                for v in p.buildGraph[kind]:
                    state = self.board.boardGraph[v].state
                    assert state['Player'] is p and state[flag]
        assert sum(p.longestRoadFlag for p in self.players) <= 1
        assert sum(p.largestArmyFlag for p in self.players) <= 1
        assert sum(t.robber for t in self.board.hexTileDict.values()) == 1
