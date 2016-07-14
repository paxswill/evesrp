from httmock import HTTMock
from evesrp import systems


def test_system_name(evesrp_app, crest):
    with evesrp_app.test_request_context():
        with HTTMock(crest):
            assert systems.system_names[99930000142] == 'Jita'

def test_constellation_name(evesrp_app, crest):
    with evesrp_app.test_request_context():
        with HTTMock(crest):
            assert systems.constellation_names[99920000020] == 'Kimotoro'

def test_region_name(evesrp_app, crest):
    with evesrp_app.test_request_context():
        with HTTMock(crest):
            assert systems.region_names[99910000002] == 'The Forge'

def test_systems_constellations(evesrp_app, crest):
    with evesrp_app.test_request_context():
        with HTTMock(crest):
            assert systems.systems_constellations[99930000142] == 20000020

def test_constellations_regions(evesrp_app, crest):
    with evesrp_app.test_request_context():
        with HTTMock(crest):
            assert systems.constellations_regions[99920000020] == 10000002
