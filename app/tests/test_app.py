import json
import os
import sys
import pytest

# Ensure app/src is on sys.path so tests can import the application module
TEST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_PATH = os.path.join(TEST_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import importlib
application = importlib.import_module('app')


@pytest.fixture
def client():
    application.app.config.update({"TESTING": True})
    with application.app.test_client() as c:
        yield c


def test_healthz(client):
    r = client.get('/healthz')
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('status') == 'ok'


def test_root_serves_index(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'GitHub Profile Metrics' in r.data
