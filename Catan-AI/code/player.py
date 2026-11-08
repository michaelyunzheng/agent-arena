"""Player state. Rules and mutations belong to GameEngine, not the UI or policy."""
RESOURCES = ('ORE', 'BRICK', 'WHEAT', 'WOOD', 'SHEEP')
DEV_CARDS = ('KNIGHT', 'VP', 'MONOPOLY', 'ROADBUILDER', 'YEAROFPLENTY')


class player:
    def __init__(self, playerName, playerColor, is_ai=False):
        self.name, self.color, self.isAI = playerName, playerColor, is_ai
        self.resources = dict.fromkeys(RESOURCES, 0)
        self.devCards = dict.fromkeys(DEV_CARDS, 0)
        self.newDevCards = []
        self.playedDevCards = dict.fromkeys(DEV_CARDS, 0)
        self.devCardPlayedThisTurn = False
        self.buildGraph = {'ROADS': [], 'SETTLEMENTS': [], 'CITIES': []}
        self.portList = []
        self.knightsPlayed = 0
        self.maxRoadLength = 0
        self.longestRoadFlag = False
        self.largestArmyFlag = False

    @property
    def settlementsLeft(self):
        return 5 - len(self.buildGraph['SETTLEMENTS'])

    @property
    def citiesLeft(self):
        return 4 - len(self.buildGraph['CITIES'])

    @property
    def roadsLeft(self):
        return 15 - len(self.buildGraph['ROADS'])

    @property
    def visibleVictoryPoints(self):
        return (len(self.buildGraph['SETTLEMENTS']) + 2 * len(self.buildGraph['CITIES'])
                + 2 * self.longestRoadFlag + 2 * self.largestArmyFlag)

    @property
    def victoryPoints(self):
        return self.visibleVictoryPoints + self.devCards['VP']

    def updateDevCards(self):
        for card in self.newDevCards:
            self.devCards[card] += 1
        self.newDevCards.clear()

    def get_road_length(self, board):
        """Longest edge-simple trail; a junction may be revisited, an edge may not."""
        adjacency = {}
        for index, (a, b) in enumerate(self.buildGraph['ROADS']):
            adjacency.setdefault(a, []).append((index, b))
            adjacency.setdefault(b, []).append((index, a))

        def visit(vertex, used):
            if used and board.boardGraph[vertex].state['Player'] not in (None, self):
                return bin(used).count('1')
            return max([bin(used).count('1')] + [visit(other, used | (1 << index))
                       for index, other in adjacency[vertex] if not used & (1 << index)])

        return max((visit(vertex, 0) for vertex in adjacency), default=0)
