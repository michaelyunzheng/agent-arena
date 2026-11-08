"""Pygame presentation and responsive choice dialogs; no game-rule mutations."""
import math
import pygame
from hexLib import polygon_corners, hex_to_pixel
from player import RESOURCES


class Cancelled(Exception):
    pass


class catanGameView:
    def __init__(self, board, game):
        pygame.init()
        self.board, self.game = board, game
        self.screen = pygame.display.set_mode((1240, 850))
        pygame.display.set_caption('CATAN — You vs three AI opponents')
        self.font = pygame.font.SysFont('arial', 17)
        self.small = pygame.font.SysFont('arial', 14)
        self.title = pygame.font.SysFont('arial', 24, bold=True)
        self.clock = pygame.time.Clock()
        self.message = 'Place your first settlement.'
        self.buttons = {}

    def text(self, message, pos, color='white', font=None):
        self.screen.blit((font or self.font).render(str(message), True, color), pos)

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            yield event
        self.clock.tick(60)

    def displayGameScreen(self):
        game = self.game
        self.screen.fill('#17354a')
        colors = {'BRICK': '#b76144', 'ORE': '#929baf', 'WHEAT': '#e8ca68',
                  'WOOD': '#327956', 'SHEEP': '#98bb65', 'DESERT': '#d5bd94'}
        for tile in self.board.hexTileDict.values():
            corners = polygon_corners(self.board.flat, tile.hex)
            pygame.draw.polygon(self.screen, colors[tile.resource.type], corners)
            pygame.draw.polygon(self.screen, '#243d43', corners, 2)
            center = hex_to_pixel(self.board.flat, tile.hex)
            tile.pixelCenter = center
            self.text(tile.resource.type, (center.x - 28, center.y - 20), '#142327', self.small)
            if tile.resource.num:
                self.text(tile.resource.num, (center.x - 6, center.y + 2), '#142327')
            if tile.robber:
                pygame.draw.circle(self.screen, '#20202a', (int(center.x), int(center.y + 32)), 12)
        for (a, b), port in self.board.port_edges:
            x, y = (a.x + b.x) / 2, (a.y + b.y) / 2
            dx, dy = x - self.board.flat.origin.x, y - self.board.flat.origin.y
            length = math.hypot(dx, dy)
            label = self.small.render(port, True, '#ffffff')
            self.screen.blit(label, (x + dx / length * 26 - label.get_width() / 2,
                                     y + dy / length * 26 - label.get_height() / 2))
        for p in game.players:
            for a, b in p.buildGraph['ROADS']:
                pygame.draw.line(self.screen, 'white', a, b, 10)
                pygame.draw.line(self.screen, p.color, a, b, 6)
            for kind in ('SETTLEMENTS', 'CITIES'):
                for v in p.buildGraph[kind]:
                    rect = pygame.Rect(v.x - 9, v.y - 9, 18, 18)
                    if kind == 'CITIES':
                        rect.inflate_ip(8, 8)
                    pygame.draw.rect(self.screen, p.color, rect)
                    pygame.draw.rect(self.screen, 'white', rect, 2)
        self.text('CATAN', (24, 24), font=self.title)
        self.text(f'Turn {game.turn} · {game.current.name}', (220, 24), font=self.title)
        self.text(f'Phase: {game.phase.replace("_", " ")}', (220, 58))
        if game.last_roll:
            self.text(f'Dice: {game.last_roll}', (640, 58))
        labels = [('roll', 'Roll dice'), ('ROAD', 'Build road'), ('SETTLE', 'Settlement'),
                  ('CITY', 'Upgrade city'), ('buy', 'Buy dev card'), ('play', 'Play dev card'),
                  ('bank', 'Bank / port trade'), ('trade', 'Offer AI trade'), ('end', 'End turn')]
        self.buttons = {}
        for i, (key, label) in enumerate(labels):
            rect = pygame.Rect(16, 120 + i * 53, 160, 41)
            pygame.draw.rect(self.screen, '#34566c', rect, border_radius=6)
            self.text(label, (25, rect.y + 11))
            self.buttons[key] = rect
        for i, p in enumerate(game.players):
            y = 120 + i * 95
            self.text(p.name, (965, y), font=self.title)
            points = p.victoryPoints if not p.isAI else p.visibleVictoryPoints
            self.text(f'{points} points · {sum(p.resources.values())} cards', (965, y + 30))
            awards = ('Road ' if p.longestRoadFlag else '') + ('Army' if p.largestArmyFlag else '')
            self.text(awards, (965, y + 52), '#e8ca68')
        human = next((p for p in game.players if not p.isAI), game.players[0])
        self.text('Your hand', (965, 530), font=self.title)
        for i, r in enumerate(RESOURCES):
            self.text(f'{r}: {human.resources[r]}   bank: {game.bank[r]}', (965, 568 + i * 25))
        self.text('Your development cards', (965, 710))
        for i, (card, count) in enumerate(human.devCards.items()):
            fresh = human.newDevCards.count(card)
            self.text(f'{card}: {count}' + (f' (+{fresh} new)' if fresh else ''),
                      (965, 736 + i * 18), font=self.small)
        self.text(self.message[:125], (20, 760))
        if game.events:
            self.text(game.events[-1][:125], (20, 793), '#bdd5df')
        pygame.display.flip()

    def choose(self, prompt, options, optional=True):
        """Choose from (value, label) pairs. Empty mandatory menus fail explicitly."""
        if not options:
            if optional:
                raise Cancelled
            raise ValueError('No choices available: ' + prompt)
        page = 0
        page_size = 10
        while True:
            self.displayGameScreen()
            shown = options[page * page_size:(page + 1) * page_size]
            navigation = []
            if page:
                navigation.append(("__previous__", "Previous page"))
            if (page + 1) * page_size < len(options):
                navigation.append(("__next__", "Next page"))
            panel = pygame.Rect(260, 110, 650, 90 + 39 * (len(shown) + len(navigation) + int(optional)))
            pygame.draw.rect(self.screen, '#112735', panel, border_radius=10)
            self.text(prompt, (280, 128), font=self.title)
            rows = []
            entries = shown + navigation + ([(None, 'Cancel (Esc)')] if optional else [])
            for i, (value, label) in enumerate(entries):
                rect = pygame.Rect(280, 175 + i * 39, 610, 33)
                pygame.draw.rect(self.screen, '#34566c', rect, border_radius=4)
                self.text(label, (290, rect.y + 7))
                rows.append((rect, value))
            pygame.display.flip()
            for event in self.events():
                if optional and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    raise Cancelled
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, value in rows:
                        if rect.collidepoint(event.pos):
                            if value is None and optional:
                                raise Cancelled
                            if value == "__next__":
                                page += 1
                                break
                            if value == "__previous__":
                                page -= 1
                                break
                            return value

    def pick_location(self, kind, choices, optional=True):
        if not choices:
            raise Cancelled
        self.message = 'Click a highlighted location.' + (' Esc to cancel.' if optional else '')
        while True:
            self.displayGameScreen()
            for location in choices:
                if kind == 'ROAD':
                    pygame.draw.line(self.screen, '#fff39b', *location, 5)
                else:
                    pygame.draw.circle(self.screen, '#fff39b', location, 15, 3)
            pygame.display.flip()
            for event in self.events():
                if optional and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    raise Cancelled
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for location in choices:
                        if kind == 'ROAD':
                            a, b = location
                            dx, dy = b.x - a.x, b.y - a.y
                            t = max(0, min(1, ((event.pos[0]-a.x)*dx + (event.pos[1]-a.y)*dy)/(dx*dx+dy*dy)))
                            distance = math.hypot(event.pos[0]-a.x-t*dx, event.pos[1]-a.y-t*dy)
                        else:
                            distance = math.dist(event.pos, location)
                        if distance < 16:
                            return location

    def choose_robber(self, p):
        # Centers are calculated by drawing, independent of the rule engine.
        self.displayGameScreen()
        choices = {tile.pixelCenter: h for h, tile in self.board.get_robber_spots().items()}
        h = choices[self.pick_location('HEX', choices, optional=False)]
        victims = self.board.get_players_to_rob(h, p)
        victim = self.choose('Choose whom to rob', [(v, v.name) for v in victims], optional=False) if victims else None
        return h, victim
