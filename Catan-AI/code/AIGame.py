"""Bounded, reproducible AI matches using the same engine as the human game."""
import argparse
import json
from engine import GameEngine
from heuristicAIPlayer import heuristicAIPlayer


def simulate(seed=0, num_players=4, max_turns=2000):
    colors = ['black', 'darkslateblue', 'magenta4', 'orange1']
    game = GameEngine([heuristicAIPlayer(f'AI {i + 1}', colors[i]) for i in range(num_players)], seed)
    decisions = 0
    while not game.winner and game.turn <= max_turns and decisions < max_turns * 100:
        actor = next(iter(game.pending_discards)) if game.phase == 'discard' else game.current
        actor.step(game)
        game.assert_invariants()
        decisions += 1
    return {'seed': seed, 'status': 'won' if game.winner else 'turn_limit',
            'winner': game.winner.name if game.winner else None, 'turns': game.turn,
            'decisions': decisions, 'points': [p.victoryPoints for p in game.players]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--games', type=int, default=1)
    parser.add_argument('--players', type=int, choices=(3, 4), default=4)
    parser.add_argument('--max-turns', type=int, default=2000)
    args = parser.parse_args()
    if args.games < 1 or args.max_turns < 1:
        parser.error('games and max-turns must be positive')
    for seed in range(args.seed, args.seed + args.games):
        print(json.dumps(simulate(seed, args.players, args.max_turns)))


if __name__ == '__main__':
    main()
