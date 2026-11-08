"""Public-information observation encoder; no learning algorithm is claimed."""
from player import RESOURCES, DEV_CARDS


class modelState:
    def __init__(self, game, observer=None):
        observer = game.current if observer is None else observer
        if observer not in game.players:
            raise ValueError('Observer must belong to the game.')
        ordered = game.players[game.players.index(observer):] + game.players[:game.players.index(observer)]
        ids = {p: i + 1 for i, p in enumerate(ordered)}
        board = game.board
        vertices = list(board.vertex_index_to_pixel_dict.values())
        self.vertexState = [(ids.get(board.boardGraph[v].state['Player'], 0),
                             2 if board.boardGraph[v].state['City'] else int(board.boardGraph[v].state['Settlement']))
                            for v in vertices]
        edges = [(a, b) for a in vertices for b in board.boardGraph[a].edgeList
                 if board.boardGraph[a].vertexIndex < board.boardGraph[b].vertexIndex]
        self.edgeState = [ids.get(board.boardGraph[a].edgeState[board.boardGraph[a].edgeList.index(b)][0], 0)
                          for a, b in edges]
        self.resources = [observer.resources[r] for r in RESOURCES]
        self.devCards = [observer.devCards[c] for c in DEV_CARDS]
        self.newDevCards = [observer.newDevCards.count(c) for c in DEV_CARDS]
        self.publicPoints = [p.visibleVictoryPoints for p in ordered]
        self.handSizes = [sum(p.resources.values()) for p in ordered]
        self.developmentCardCounts = [sum(p.devCards.values()) + len(p.newDevCards) for p in ordered]
        self.tiles = [(t.resource.type, t.resource.num, t.robber) for t in board.hexTileDict.values()]
        self.ports = [board.boardGraph[v].port for v in vertices]
        self.bank = [game.bank[r] for r in RESOURCES]
        self.currentPlayer = ids[game.current]
        self.phase = game.phase
        self.freeRoads = game.free_roads
        self.playedDevelopmentCard = observer.devCardPlayedThisTurn
        self.discardDue = game.pending_discards.get(observer, 0)
