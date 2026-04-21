import pytest
import sys

if __name__ == '__main__':
    rc = pytest.main(['test_e2e.py::TestFigmentE2E::test_playlist_creation', '-q'])
    print('pytest rc=', rc)
    sys.exit(rc)
