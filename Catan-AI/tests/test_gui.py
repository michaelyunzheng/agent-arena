import pygame
import pytest
from catanGame import catanGame
from gameView import Cancelled


@pytest.fixture
def app():
    app=catanGame(seed=7,ai_delay=0)
    yield app
    pygame.quit()


def test_render_and_quit_setup_dialog(app):
    app.view.displayGameScreen()
    assert app.view.screen.get_size()==(1240,850)
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    with pytest.raises(SystemExit):
        app.view.pick_location('SETTLE',app.engine.legal_builds(app.engine.current,'SETTLE'),optional=False)


def test_choose_cancel_and_quit(app):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    with pytest.raises(Cancelled):app.view.choose('Select', [('a','A')])
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    with pytest.raises(SystemExit):app.view.choose('Select',[('a','A')],optional=False)


def test_setup_click_builds_selected_vertex(app):
    game=app.engine; p=game.current
    v=next(iter(game.legal_builds(p,'SETTLE')))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(v.x,v.y)))
    chosen=app.view.pick_location('SETTLE',game.legal_builds(p,'SETTLE'),optional=False)
    game.build(p,'SETTLE',chosen)
    assert game.phase=='setup_road' and chosen in p.buildGraph['SETTLEMENTS']


def test_resource_dialog_handles_excluded_resource(app,monkeypatch):
    monkeypatch.setattr(app.view,'choose',lambda prompt,options:options[0][0])
    assert app.choose_resource('Choose',{'ORE':2})=='ORE'


def test_trade_requires_ai_acceptance(app,monkeypatch):
    game=app.engine;game.phase='main';p,q=game.players[:2]
    game.give(p,'WOOD',1);game.give(q,'ORE',1)
    replies=iter([q,'WOOD',1,'ORE',1,'ok'])
    monkeypatch.setattr(app.view,'choose',lambda *a,**k:next(replies))
    monkeypatch.setattr(q,'accept_trade',lambda *a:False)
    app.offer_trade(p)
    assert p.resources['WOOD']==1 and q.resources['ORE']==1


def test_main_loop_honors_quit(app):
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    with pytest.raises(SystemExit):app.playCatan()
    assert not pygame.get_init()


def test_large_choice_menu_paginates(app,monkeypatch):
    batches=iter([[pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(300,580))],
                  [pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(300,493))]])
    monkeypatch.setattr(app.view,'events',lambda:iter(next(batches)))
    assert app.view.choose('Amount',[(i,str(i)) for i in range(1,20)])==19


def test_finished_game_reveals_ai_points(app, monkeypatch):
    game = app.engine
    ai = game.players[1]
    ai.devCards['VP'] = 2
    rendered = []
    monkeypatch.setattr(app.view, 'text', lambda message, *args, **kwargs: rendered.append(message))
    app.view.displayGameScreen()
    assert '2 points · 0 cards' not in rendered
    rendered.clear()
    game.winner = ai
    game.phase = 'finished'
    app.view.displayGameScreen()
    assert '2 points · 0 cards' in rendered
