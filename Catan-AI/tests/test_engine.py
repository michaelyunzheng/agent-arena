import copy
import importlib
import subprocess
import sys
from collections import Counter
from types import SimpleNamespace
import pytest
from engine import GameEngine, RuleError
from heuristicAIPlayer import heuristicAIPlayer
from player import player, RESOURCES
from catanGame import default_players
from modelState import modelState
from AIGame import simulate


def new_game(seed=42):
    return GameEngine([heuristicAIPlayer(str(i), 'black') for i in range(4)], seed)


def ready(seed=42):
    g = new_game(seed)
    while g.phase.startswith('setup'):
        g.current.step(g)
    return g


def grant(g, p, **resources):
    for r, n in resources.items():
        g.give(p, r, n)


def card(g, p, name):
    g.board.devCardStack[name] -= 1
    p.devCards[name] += 1


def snapshot(g):
    return repr((g.phase, g.bank, [(p.resources, p.devCards, p.newDevCards, p.buildGraph,
                  p.victoryPoints) for p in g.players], g.rng.bit_generator.state))


def test_default_is_one_human_three_ai():
    players = default_players('Michael')
    assert [p.isAI for p in players] == [False, True, True, True]
    assert players[0].name == 'Michael'
    assert all(sum(p.resources.values()) == 0 for p in players)


def test_setup_geometry_supply_and_snake_order():
    g = new_game()
    seen = []
    while g.phase.startswith('setup'):
        if g.phase == 'setup_settlement':
            seen.append(g.current.name)
        g.current.step(g)
        g.assert_invariants()
    assert seen == ['0', '1', '2', '3', '3', '2', '1', '0']
    assert len(g.board.hexTileDict) == 19
    assert len(g.board.boardGraph) == 54
    assert sum(len(v.edgeList) for v in g.board.boardGraph.values()) // 2 == 72
    assert sum(g.board.devCardStack.values()) == 25
    for p in g.players:
        assert p.victoryPoints == p.visibleVictoryPoints == 2
        assert p.roadsLeft == 13 and p.settlementsLeft == 3
        second = p.buildGraph['SETTLEMENTS'][1]
        expected = Counter(g.board.hexTileDict[h].resource.type for h in g.board.boardGraph[second].adjacentHexList
                           if g.board.hexTileDict[h].resource.type != 'DESERT')
        assert {r: n for r, n in p.resources.items() if n} == expected


def test_seeded_board_and_no_adjacent_red_numbers():
    g, other = new_game(7), new_game(7)
    assert [t.resource for t in g.board.hexTileDict.values()] == [t.resource for t in other.board.hexTileDict.values()]
    for tile in g.board.hexTileDict.values():
        for node in g.board.boardGraph.values():
            if tile.index in node.adjacentHexList and tile.resource.num in (6, 8):
                for h in node.adjacentHexList:
                    if h != tile.index:
                        assert g.board.hexTileDict[h].resource.num not in (6, 8)


def test_invalid_actions_are_atomic():
    g = ready(); p = g.current
    before = snapshot(g)
    with pytest.raises(RuleError):
        g.trade_bank(p, 'WOOD', 'ORE')
    assert snapshot(g) == before
    with pytest.raises(RuleError):
        g.build(p, 'CITY', p.buildGraph['SETTLEMENTS'][0])
    assert snapshot(g) == before
    g.phase = 'main'
    for kind, loc in [('SETTLE', p.buildGraph['SETTLEMENTS'][0]), ('CITY', next(v for v in g.board.boardGraph if v not in p.buildGraph['SETTLEMENTS'])), ('ROAD', p.buildGraph['ROADS'][0])]:
        before = snapshot(g)
        with pytest.raises(RuleError):
            g.build(p, kind, loc)
        assert snapshot(g) == before
    with pytest.raises(RuleError):
        g.end_turn(g.players[1])


def test_city_updates_points_pieces_and_graph():
    g = ready(); p = g.current; g.phase = 'main'
    grant(g, p, ORE=3, WHEAT=2)
    v = p.buildGraph['SETTLEMENTS'][0]
    g.build(p, 'CITY', v)
    assert p.visibleVictoryPoints == p.victoryPoints == 3
    assert p.citiesLeft == 3 and p.settlementsLeft == 4
    assert v not in p.buildGraph['SETTLEMENTS']
    g.assert_invariants()


def test_seven_discards_each_player_and_returns_cards():
    g = ready()
    for p in g.players:
        for r in RESOURCES:
            if g.bank[r] >= 2:
                grant(g, p, **{r: 2})
    before = {p: sum(p.resources.values()) for p in g.players}
    g.resolve_roll(7)
    assert g.phase == 'discard'
    p = next(iter(g.pending_discards))
    state = snapshot(g)
    with pytest.raises(RuleError):
        g.discard(p, {'WOOD': 1})
    assert snapshot(g) == state
    for p in list(g.pending_discards):
        p.step(g)
        assert sum(p.resources.values()) == before[p] - before[p] // 2
    assert g.phase == 'robber'
    g.current.step(g)
    assert g.phase == 'main'
    g.assert_invariants()


def test_robber_no_victims_and_empty_hands():
    g = ready(); p = g.current
    for other in g.players:
        g.pay(other, other.resources.copy())
    g.phase = 'robber'
    h, victim = p.choose_player_to_rob(g.board)
    assert victim is None
    g.move_robber(p, h, victim)
    assert g.phase == 'main'
    g.assert_invariants()


def test_robber_rejects_self_empty_victim_and_current_hex():
    g = ready(); p = g.current; g.phase = 'robber'
    h = next(iter(g.board.get_robber_spots()))
    before = snapshot(g)
    with pytest.raises(RuleError):
        g.move_robber(p, h, p)
    assert snapshot(g) == before
    occupied = next(h for h,t in g.board.hexTileDict.items() if t.robber)
    with pytest.raises(RuleError):
        g.move_robber(p, occupied)


def test_stealing_conserves_cards():
    g = ready(); p, other = g.players[:2]; g.phase = 'robber'
    grant(g, other, ORE=1)
    h = next(h for h in g.board.get_robber_spots() if other in g.board.get_players_to_rob(h,p))
    before = sum(p.resources.values()), sum(other.resources.values())
    g.move_robber(p,h,other)
    assert (sum(p.resources.values()),sum(other.resources.values())) == (before[0]+1,before[1]-1)
    g.assert_invariants()


def test_free_road_card_no_resources_and_only_one_piece():
    g = ready(); p = g.current; g.phase = 'main'
    g.pay(p, p.resources.copy()); card(g,p,'ROADBUILDER')
    g.play_dev(p,'ROADBUILDER')
    for _ in range(2):
        g.build(p,'ROAD',next(iter(g.legal_builds(p,'ROAD'))))
    assert len(p.buildGraph['ROADS']) == 4
    assert sum(p.resources.values()) == 0 and g.phase == 'main'
    g.assert_invariants()
    # Build a legal 14-road network, then spend the final piece with a card.
    p.devCardPlayedThisTurn = False
    while len(p.buildGraph['ROADS']) < 14:
        g.phase = 'free_roads'; g.free_roads = 1; g.resume_phase = 'main'
        g.build(p,'ROAD',next(iter(g.legal_builds(p,'ROAD'))))
    card(g,p,'ROADBUILDER'); g.play_dev(p,'ROADBUILDER')
    g.build(p,'ROAD',next(iter(g.legal_builds(p,'ROAD'))))
    assert p.roadsLeft == 0 and g.phase == 'main' and g.free_roads == 0


def test_no_legal_road_ai_ends_safely(monkeypatch):
    g=ready(); p=g.current; g.phase='main'
    grant(g,p,WOOD=1,BRICK=1)
    monkeypatch.setattr(g.board,'get_potential_roads',lambda p:{})
    monkeypatch.setattr(g.board,'get_potential_settlements',lambda p:{})
    monkeypatch.setattr(g.board,'get_potential_cities',lambda p:{})
    for _ in range(30):
        if g.current is not p:
            break
        p.step(g)
    assert g.current is not p


def test_longest_road_review_regression_and_empty_network():
    g=new_game(); p=g.current
    assert p.get_road_length(g.board)==0
    indices=[(20,21),(20,19),(23,19),(43,21),(43,44),(45,20),(23,22),(48,23),(49,48),(44,40),(50,22),(40,41),(50,53),(49,45),(53,27)]
    p.buildGraph['ROADS']=[tuple(g.board.vertex_index_to_pixel_dict[i] for i in edge) for edge in indices]
    assert p.get_road_length(g.board)==13


def chain(g, p, length):
    def visit(v, path):
        if len(path)==length+1: return path
        for w in g.board.boardGraph[v].edgeList:
            if w not in path:
                result=visit(w,path+[w])
                if result:return result
    path=visit(next(iter(g.board.boardGraph)),[next(iter(g.board.boardGraph))])
    for a,b in zip(path,path[1:]):
        p.buildGraph['ROADS'].append((a,b));g.board.updateBoardGraph_road(a,b,p)
    return path


def test_settlement_interrupt_recomputes_and_revokes_award():
    g=new_game(); owner, builder=g.players[:2]
    path=chain(g,owner,6)
    g.update_awards(); assert owner.longestRoadFlag
    g.current_index=1;g.phase='setup_settlement'
    g.build(builder,'SETTLE',path[3])
    assert owner.maxRoadLength==3 and not owner.longestRoadFlag


def test_largest_army_ties_preserve_holder_then_transfer():
    g=new_game(); p,q=g.players[:2]
    p.knightsPlayed=3;g.update_awards();assert p.largestArmyFlag
    q.knightsPlayed=3;g.update_awards();assert p.largestArmyFlag
    q.knightsPlayed=4;g.update_awards();assert q.largestArmyFlag and not p.largestArmyFlag


def test_longest_road_tie_and_revocation(monkeypatch):
    g=new_game();p,q=g.players[:2]
    lengths={p:5,q:0}
    for person in g.players:
        monkeypatch.setattr(person,'get_road_length',lambda board,p=person:lengths.get(p,0))
    g.update_awards();assert p.longestRoadFlag
    lengths[q]=5;g.update_awards();assert p.longestRoadFlag
    lengths[p]=3;g.update_awards();assert q.longestRoadFlag
    lengths[q]=3;g.update_awards();assert not any(x.longestRoadFlag for x in g.players)
    lengths[p]=lengths[q]=5;g.update_awards();assert not any(x.longestRoadFlag for x in g.players)


def test_trade_acceptance_amounts_and_bank_limits():
    g=ready(); p,q=g.players[:2];g.phase='main'
    grant(g,p,WOOD=4);grant(g,q,ORE=2)
    before=snapshot(g)
    assert not g.trade_players(p,q,{'WOOD':1},{'ORE':1})
    assert snapshot(g)==before
    assert g.trade_players(p,q,{'WOOD':1},{'ORE':1},accepted=True)
    for invalid in ({'WOOD':0},{'WOOD':-1},{'WOOD':True},{'X':1}):
        before=snapshot(g)
        with pytest.raises(RuleError):g.trade_players(p,q,invalid,{'ORE':1},True)
        assert snapshot(g)==before
    with pytest.raises(RuleError):g.trade_players(p,q,{'WOOD':1},{'ORE':99},True)
    g.assert_invariants()


@pytest.mark.parametrize('port,ratio',[(None,4),('3:1 PORT',3),('2:1 WOOD',2)])
def test_bank_trade_ratios(port,ratio):
    g=ready();p=g.current;g.phase='main';p.portList=[port] if port else []
    grant(g,p,WOOD=4)
    before=p.resources.copy()
    g.trade_bank(p,'WOOD','ORE')
    assert p.resources['WOOD']==before['WOOD']-ratio and p.resources['ORE']==before['ORE']+1
    g.assert_invariants()


def test_bank_empty_trade_rejected():
    g=ready();p,q=g.players[:2];g.phase='main';grant(g,p,WOOD=4)
    grant(g,q,ORE=g.bank['ORE'])
    before=snapshot(g)
    with pytest.raises(RuleError):g.trade_bank(p,'WOOD','ORE')
    assert snapshot(g)==before


def test_development_card_age_one_per_turn_and_knight_before_roll():
    g=ready();p=g.current
    g.board.devCardStack['KNIGHT']-=1;p.newDevCards.append('KNIGHT')
    with pytest.raises(RuleError):g.play_dev(p,'KNIGHT')
    p.updateDevCards();g.play_dev(p,'KNIGHT')
    assert g.phase=='robber' and p.knightsPlayed==1
    p.step(g);assert g.phase=='roll'
    card(g,p,'MONOPOLY')
    with pytest.raises(RuleError):g.play_dev(p,'MONOPOLY',('ORE',))
    g.assert_invariants()


def test_monopoly_transfers_and_year_of_plenty_validates_before_spending():
    g=ready();p,q=g.players[:2];g.phase='main'
    card(g,p,'YEAROFPLENTY');grant(g,q,ORE=g.bank['ORE'])
    before=snapshot(g)
    with pytest.raises(RuleError):g.play_dev(p,'YEAROFPLENTY',('ORE','ORE'))
    assert snapshot(g)==before
    g.play_dev(p,'YEAROFPLENTY',('WOOD','WOOD'))
    p.devCardPlayedThisTurn=False;card(g,p,'MONOPOLY')
    g.play_dev(p,'MONOPOLY',('ORE',))
    assert p.resources['ORE']==19
    assert all(q.resources['ORE']==0 for q in g.players if q is not p)
    g.assert_invariants()


def test_vp_card_wins_immediately_and_stays_private():
    g=ready();p=g.current;g.phase='main';g.target=3
    # Force a one-card deck while preserving conservation of the others.
    for c,n in g.board.devCardStack.items():
        p.playedDevCards[c]=n
        g.board.devCardStack[c]=0
    p.playedDevCards['VP']-=1;g.board.devCardStack['VP']=1
    grant(g,p,ORE=1,WHEAT=1,SHEEP=1)
    g.buy_dev(p)
    assert g.winner is p and p.victoryPoints==3 and p.visibleVictoryPoints==2


def test_production_shortage_shared_and_single_claimant():
    g=new_game();p,q=g.players[:2]
    h=next(t for t in g.board.hexTileDict.values() if t.resource.num)
    vertices=[v for v,n in g.board.boardGraph.items() if h.index in n.adjacentHexList]
    p.buildGraph['CITIES']=[vertices[0]];q.buildGraph['CITIES']=[vertices[3]]
    r=h.resource.type
    # Isolate the production fixture from other tiles with the same number.
    for t in g.board.hexTileDict.values():t.robber=t is not h
    g.bank[r]=1;g.phase='roll';g.resolve_roll(h.resource.num)
    assert p.resources[r]==q.resources[r]==0 and g.bank[r]==1
    q.buildGraph['CITIES']=[];g.phase='roll';g.resolve_roll(h.resource.num)
    assert p.resources[r]==1 and g.bank[r]==0


def test_observation_dimensions_and_no_opponent_private_cards():
    g=ready();p,q=g.players[:2];card(g,q,'VP')
    state=modelState(g,p)
    assert len(state.vertexState)==54 and len(state.edgeState)==72
    assert state.publicPoints[1]==2
    assert state.devCards==[0]*5
    assert state.handSizes[1]==sum(q.resources.values())
    assert 'VP' not in repr(state.__dict__)


def test_imports_do_not_start_games_or_import_pygame():
    result=subprocess.run([sys.executable,'-c',
        "import catanGame,AIGame,modelState,tensorflowTest,sys; assert 'pygame' not in sys.modules; assert 'tensorflow' not in sys.modules"],
        cwd=str(__import__('pathlib').Path(__file__).resolve().parents[1]/'code'),capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('seed',range(10))
def test_seeded_matches_finish_without_invariant_failures(seed):
    result=simulate(seed,max_turns=1000)
    assert result['status']=='won',result
    assert max(result['points'])>=10


def test_match_reproducibility_and_three_player_support():
    assert simulate(31,3)==simulate(31,3)


def test_road_card_before_roll_resumes_roll():
    g=ready();p=g.current;card(g,p,'ROADBUILDER')
    g.play_dev(p,'ROADBUILDER')
    while g.phase=='free_roads':p.step(g)
    assert g.phase=='roll'
    with pytest.raises(RuleError):g.end_turn(p)
    g.assert_invariants()


def test_city_resource_helper_and_ai_trade_policy():
    p=heuristicAIPlayer('AI','black')
    assert p.resources_needed_for_city()=={'ORE':3,'WHEAT':2}
    p.resources['ORE']=1
    assert not p.accept_trade({'WOOD':1},{'ORE':2})
    assert p.accept_trade({'WOOD':2},{'ORE':1})


def test_discard_cannot_happen_twice():
    g=ready();p=g.current;grant(g,p,ORE=10)
    g.resolve_roll(7)
    g.discard(p,p.discard_choice(g.pending_discards[p]))
    before=snapshot(g)
    with pytest.raises(RuleError):g.discard(p,{'ORE':1})
    assert snapshot(g)==before


def test_old_cards_mature_only_on_owners_next_turn():
    g=ready();p=g.current
    g.board.devCardStack['KNIGHT']-=1;p.newDevCards.append('KNIGHT')
    for index in range(4):
        g.phase='main';g.end_turn(g.current)
        if index<3:assert p.devCards['KNIGHT']==0
    assert g.current is p and p.devCards['KNIGHT']==1 and not p.newDevCards
