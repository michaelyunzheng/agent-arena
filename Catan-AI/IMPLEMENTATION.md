# Gameplay repair notes

The human game now starts with one human and three heuristic AI players. All
participants share a 10-point target, free snake-order setup, and resources from
only their second settlement. Launch with `python code/catanGame.py --name Michael`.

## Changes

- Added a shared headless rules engine with explicit setup, roll, discard, robber,
  main, free-road, and finished phases. Invalid gameplay actions are validated
  before costs or board changes are applied.
- Added a finite 19-per-resource bank and corrected the 25-card development deck.
- Fixed robber fallback and victim eligibility, empty-road decisions, seven-roll
  discards, score derivation, and longest-road traversal and interruption handling.
- Replaced unilateral trades with AI acceptance and phase-checked bank trades.
- Implemented free Road Building, usable AI development cards, and resource-helper
  corrections. Newly bought action cards wait for their owner's next turn.
- Replaced terminal prompts with Pygame dialogs; added your hand, public player
  scores, bank counts, card inventory, and consistent close/cancel handling.
- Added seeded bounded simulations, a public-information observation encoder,
  dependency files, regression tests, and a GitHub Actions Python matrix.
- Removed tracked bytecode, notebook checkpoints, and the machine-specific editor
  setting. Imports no longer start gameplay or MNIST training.

## Validation performed

- 48 pytest cases passed on Python 3.9.0, NumPy 2.0.2, Pygame 2.6.1,
  and pytest 8.4.2 on macOS.
- 100 four-player seeded simulations (seeds 0–99, limit 1,000 individual turns)
  all finished with a winner; 57–169 turns per match. Resource, development-card,
  piece, occupancy, award, and robber checks ran after every decision.
- Three-player simulation and repeat-seed reproducibility are covered by tests.
- The original longest-road fixture now returns 13 rather than 11.
- SDL dummy-driver GUI tests cover rendering, setup clicks, cancellation, quit,
  paginated choice menus, and declined trades. A rendered board was visually checked.
- `git diff --check` passed.

The local GUI tests use real Pygame with a dummy display, not a mocked renderer.
They do not substitute for a full manual playthrough on the user's physical display.
The CI matrix is configured for Python 3.9, 3.11, and 3.12; the original local validation used 3.9. Subsequent container checks
also passed all 48 original tests on Linux ARM64 with Python 3.12.11, verified
the noVNC page and password authentication, and opened the game on the X11 desktop. The 100-match completion result is a stability check, not a measure of AI
strength or proof that every Catan edge case is covered.

## Compatibility and remaining scope

This is a structural repair: old `player.build_*` mutation methods are replaced
by `GameEngine` actions, and `catanGame` is now a GUI controller. External scripts
using the old internal API must migrate. The board geometry helpers and original
license attribution are retained.

The AI remains heuristic. It accepts/rejects human offers but does not initiate
negotiations. The state encoder is usable, but no RL training, MCTS, action-space
index, reward API, saved models, network multiplayer, or save/load was added.

## Final usability review

- Added the user's actual winning-game screenshot and separate macOS/Linux,
  Windows, and container installation instructions.
- Setup prefers Python 3.12, rejects unsupported interpreters before creating an
  environment, preserves incompatible existing environments, and requires binary
  NumPy/Pygame wheels. The launcher detects incomplete dependency installations.
- Documented parent-container configuration, port forwarding, Python 3.14 / SDL
  failures, and non-destructive environment recovery; backup environments are ignored.
- Finished games reveal AI victory-point totals. Trade requests allow 1–19 cards
  without exposing opponents' resource composition. Improved event/card labels.
- Added regressions for unsupported Python, existing-environment preservation,
  failed installation reporting, and end-game score visibility.
- All 52 tests passed locally after these changes. Full container rebuilding was
  not repeated for this documentation/setup follow-up.
