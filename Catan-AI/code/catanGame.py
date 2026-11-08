"""Play one human against three heuristic AI opponents in the Pygame window."""
import argparse
from collections import Counter
from engine import GameEngine, RuleError, COSTS
from player import player, RESOURCES
from heuristicAIPlayer import heuristicAIPlayer


def default_players(name='You'):
    return [player(name, '#25252d'), heuristicAIPlayer('AI 1', '#6247aa'),
            heuristicAIPlayer('AI 2', '#ce3975'), heuristicAIPlayer('AI 3', '#df852d')]


class catanGame:
    def __init__(self, name='You', seed=None, ai_delay=350):
        from gameView import catanGameView
        self.engine = GameEngine(default_players(name), seed)
        self.view = catanGameView(self.engine.board, self.engine)
        self.ai_delay = max(0, ai_delay)

    def choose_resource(self, prompt, amounts):
        return self.view.choose(prompt, [(r, f'{r} ({amounts[r]} available)') for r in RESOURCES if amounts.get(r, 0) > 0])

    def human_discard(self, p):
        game = self.engine
        available = p.resources.copy()
        selected = Counter()
        due = game.pending_discards[p]
        for i in range(due):
            r = self.view.choose(f'Discard {due - i} more cards',
                                [(r, f'{r} ({n})') for r, n in available.items() if n], optional=False)
            available[r] -= 1
            selected[r] += 1
        game.discard(p, dict(selected))

    def play_card(self, p):
        game = self.engine
        game.actor(p, ('roll', 'main'))
        game.require(not p.devCardPlayedThisTurn, 'You have already played a card this turn.')
        choices = [(c, f'{c} ({n})') for c, n in p.devCards.items() if n and c != 'VP']
        game.require(bool(choices), 'No playable cards; new cards wait until your next turn.')
        card = self.view.choose('Play development card', choices)
        resources = []
        if card == 'YEAROFPLENTY':
            bank = game.bank.copy()
            for _ in range(min(2, sum(bank.values()))):
                r = self.choose_resource('Take a bank resource', bank)
                resources.append(r)
                bank[r] -= 1
        elif card == 'MONOPOLY':
            resources = [self.view.choose('Choose a resource', [(r, r) for r in RESOURCES])]
        game.play_dev(p, card, tuple(resources))

    def offer_trade(self, p):
        game = self.engine
        game.actor(p, ('main',))
        other = self.view.choose('Choose an AI opponent', [(o, o.name) for o in game.players if o is not p])
        give = self.choose_resource('Resource to offer', p.resources)
        amount = self.view.choose('How many to offer?', [(i, str(i)) for i in range(1, p.resources[give] + 1)])
        receive = self.view.choose('Resource to request', [(r, r) for r in RESOURCES if r != give])
        # Do not expose opponents' private resource counts in this dialog.
        wanted = self.view.choose('How many to request?', [(i, str(i)) for i in range(1, 20)])
        offer, request = {give: amount}, {receive: wanted}
        accepted = other.accept_trade(offer, request)
        if accepted:
            game.trade_players(p, other, offer, request, accepted=True)
        self.view.message = f'{other.name} ' + ('accepted your offer.' if accepted else 'declined your offer.')
        self.view.choose('Trade response', [('ok', self.view.message)], optional=False)

    def handle_action(self, action):
        game, p = self.engine, self.engine.current
        if action == 'roll':
            game.roll(p)
        elif action in ('ROAD', 'SETTLE', 'CITY'):
            game.actor(p, ('main',))
            game.require(game.can_pay(p, COSTS[action]), 'Insufficient resources.')
            choices = game.legal_builds(p, action)
            game.require(bool(choices), 'No legal locations or no pieces remaining.')
            game.build(p, action, self.view.pick_location(action, choices))
        elif action == 'buy':
            game.buy_dev(p)
        elif action == 'play':
            self.play_card(p)
        elif action == 'bank':
            game.actor(p, ('main',))
            give = self.view.choose('Trade away a resource', [(r, f'{r} ({game.trade_ratio(p, r)}:1)')
                       for r in RESOURCES if p.resources[r] >= game.trade_ratio(p, r)])
            receive = self.choose_resource('Receive from bank', {r: n for r, n in game.bank.items() if r != give})
            game.trade_bank(p, give, receive)
        elif action == 'trade':
            self.offer_trade(p)
        elif action == 'end':
            game.end_turn(p)

    def playCatan(self):
        import pygame
        from gameView import Cancelled
        game = self.engine
        next_ai = 0
        try:
            while True:
                self.view.displayGameScreen()
                events = list(self.view.events())
                if game.winner:
                    self.view.message = f'{game.winner.name} wins with {game.winner.victoryPoints} points! Close the window to exit.'
                    continue
                actor = next(iter(game.pending_discards)) if game.phase == 'discard' else game.current
                if actor.isAI:
                    self.view.message = f'{actor.name} is thinking…'
                    if pygame.time.get_ticks() >= next_ai:
                        actor.step(game)
                        next_ai = pygame.time.get_ticks() + self.ai_delay
                    continue
                try:
                    if game.phase == 'discard':
                        self.human_discard(actor)
                    elif game.phase in ('setup_settlement', 'setup_road', 'free_roads'):
                        kind = 'SETTLE' if game.phase == 'setup_settlement' else 'ROAD'
                        game.build(actor, kind, self.view.pick_location(kind, game.legal_builds(actor, kind), optional=False))
                    elif game.phase == 'robber':
                        game.move_robber(actor, *self.view.choose_robber(actor))
                    else:
                        self.view.message = 'Your turn. Roll dice first; you may play a development card before rolling.' if game.phase == 'roll' else 'Build, trade, play a card, or end your turn.'
                        for event in events:
                            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                for key, rect in self.view.buttons.items():
                                    if rect.collidepoint(event.pos):
                                        self.handle_action(key)
                                        # Discard remaining clicks after a phase/turn transition.
                                        break
                                break
                except Cancelled:
                    self.view.message = 'Cancelled.'
                except RuleError as error:
                    self.view.message = str(error)
                    # Acknowledge errors in-window, without blocking event handling.
                    self.view.choose('Action unavailable', [('ok', str(error))], optional=False)
        finally:
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='You')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--ai-delay', type=int, default=350, help='Milliseconds between AI decisions')
    args = parser.parse_args()
    try:
        catanGame(args.name, args.seed, args.ai_delay).playCatan()
    except (SystemExit, KeyboardInterrupt):
        pass


if __name__ == '__main__':
    main()
