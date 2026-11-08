"""A deterministic-under-seed baseline policy, not a learned model."""
from collections import Counter
from player import player, RESOURCES
from engine import COSTS


class heuristicAIPlayer(player):
    def __init__(self, name, color):
        super().__init__(name, color, is_ai=True)

    def vertex_score(self, board, vertex):
        tiles = [board.hexTileDict[h] for h in board.boardGraph[vertex].adjacentHexList]
        diversity = {t.resource.type for t in tiles if t.resource.type in RESOURCES}
        owned = {board.hexTileDict[h].resource.type
                 for v in self.buildGraph['SETTLEMENTS'] + self.buildGraph['CITIES']
                 for h in board.boardGraph[v].adjacentHexList}
        production = sum(6 - abs(7 - t.resource.num) for t in tiles if t.resource.num)
        return production + 2 * len(diversity) + 2.5 * len(diversity - owned)

    def choose_vertex(self, board, choices):
        return max(choices, key=lambda v: (self.vertex_score(board, v), -board.boardGraph[v].vertexIndex))

    def choose_road(self, game, choices):
        # Prefer expansion towards productive vertices, with a seeded tie-break.
        scores = []
        for edge in choices:
            value = max(self.vertex_score(game.board, v) for v in edge
                        if v in game.board.boardGraph)
            value += float(game.rng.random()) * 5
            scores.append((value, edge))
        return max(scores, key=lambda item: item[0])[1]

    def choose_player_to_rob(self, board):
        candidates = []
        for h, tile in board.get_robber_spots().items():
            score = 0
            for node in board.boardGraph.values():
                if h not in node.adjacentHexList:
                    continue
                owner = node.state['Player']
                if owner is self:
                    score -= 12
                elif owner is not None:
                    score += 2 + owner.visibleVictoryPoints
            victims = board.get_players_to_rob(h, self)
            victim = max(victims, key=lambda p: p.visibleVictoryPoints, default=None)
            candidates.append((score + (2 if victim else 0), h, victim))
        _, h, victim = max(candidates, key=lambda item: (item[0], -item[1]))
        return h, victim

    def discard_choice(self, amount):
        hand = self.resources.copy()
        cards = Counter()
        for _ in range(amount):
            resource = max(RESOURCES, key=lambda r: hand[r])
            hand[resource] -= 1
            cards[resource] += 1
        return dict(cards)

    def accept_trade(self, offered, requested):
        # Never concede more cards than received; value scarce resources higher.
        gain = sum(n * (2 if self.resources[r] < 2 else 1) for r, n in offered.items())
        loss = sum(n * (2 if self.resources[r] - n < 2 else 1) for r, n in requested.items())
        return (all(self.resources[r] >= n for r, n in requested.items())
                and sum(offered.values()) >= sum(requested.values()) and gain >= loss)

    def resources_needed_for_city(self):
        return {r: n - self.resources[r] for r, n in COSTS['CITY'].items() if self.resources[r] < n}

    def play_card(self, game):
        if self.devCardPlayedThisTurn:
            return False
        for card in ('KNIGHT', 'YEAROFPLENTY', 'MONOPOLY', 'ROADBUILDER'):
            if not self.devCards[card]:
                continue
            resources = ()
            if card == 'ROADBUILDER' and (not self.roadsLeft or not game.board.get_potential_roads(self)):
                continue
            if card == 'YEAROFPLENTY':
                bank = game.bank.copy()
                hand = self.resources.copy()
                selected = []
                for _ in range(min(2, sum(bank.values()))):
                    r = min((r for r in RESOURCES if bank[r]), key=lambda r: hand[r])
                    selected.append(r)
                    hand[r] += 1
                    bank[r] -= 1
                resources = tuple(selected)
            if card == 'MONOPOLY':
                # Only use public information: resource production on opponents' tiles.
                estimates = dict.fromkeys(RESOURCES, 0)
                for other in game.players:
                    if other is self:
                        continue
                    for v in other.buildGraph['SETTLEMENTS'] + other.buildGraph['CITIES']:
                        for h in game.board.boardGraph[v].adjacentHexList:
                            tile = game.board.hexTileDict[h]
                            if tile.resource.type in estimates:
                                estimates[tile.resource.type] += 6 - abs(7 - tile.resource.num)
                resources = (max(estimates, key=estimates.get),)
            game.play_dev(self, card, resources)
            return True
        return False

    def step(self, game):
        """Make one decision. Engine phases handle mandatory multi-step actions."""
        if game.phase == 'discard' and self in game.pending_discards:
            game.discard(self, self.discard_choice(game.pending_discards[self]))
            return
        if game.current is not self:
            return
        phase = game.phase
        if phase == 'setup_settlement':
            game.build(self, 'SETTLE', self.choose_vertex(game.board, game.legal_builds(self, 'SETTLE')))
        elif phase in ('setup_road', 'free_roads'):
            game.build(self, 'ROAD', self.choose_road(game, game.legal_builds(self, 'ROAD')))
        elif phase == 'robber':
            game.move_robber(self, *self.choose_player_to_rob(game.board))
        elif phase == 'roll':
            game.roll(self)
        elif phase == 'main':
            if self.play_card(game):
                return
            for kind in ('CITY', 'SETTLE', 'ROAD'):
                choices = game.legal_builds(self, kind)
                if choices and game.can_pay(self, COSTS[kind]):
                    location = self.choose_road(game, choices) if kind == 'ROAD' else self.choose_vertex(game.board, choices)
                    game.build(self, kind, location)
                    return
            # Trade only toward a concrete affordable goal, avoiding exchange cycles.
            for kind in ('CITY', 'SETTLE', 'ROAD', 'DEV'):
                if kind != 'DEV' and not game.legal_builds(self, kind):
                    continue
                if kind == 'DEV' and not sum(game.board.devCardStack.values()):
                    continue
                cost = COSTS[kind]
                missing = [r for r, n in cost.items() if self.resources[r] < n and game.bank[r] > 0]
                for receive in missing:
                    for give in RESOURCES:
                        if give != receive and self.resources[give] - cost.get(give, 0) >= game.trade_ratio(self, give):
                            game.trade_bank(self, give, receive)
                            return
            if game.can_pay(self, COSTS['DEV']) and sum(game.board.devCardStack.values()):
                game.buy_dev(self)
            else:
                game.end_turn(self)
