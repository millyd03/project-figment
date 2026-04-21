import requests

try:
    r = requests.post('http://localhost:8003/_test/enable_mock_spotify', timeout=5)
    print('enable', r.status_code, r.text)
except Exception as e:
    print('enable error:', e)

try:
    s = requests.get('http://localhost:8003/auth/status', timeout=5)
    print('status', s.status_code, s.text)
except Exception as e:
    print('status error:', e)
