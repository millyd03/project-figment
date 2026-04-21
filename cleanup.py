import os
import sys

files_to_remove = [
    'scripts/run_e2e.py',
    'scripts/run_playlist_test.ps1',
    'scripts/check_mock.py',
    'scripts/kill_ports.ps1',
    'run_test.py'
]

for f in files_to_remove:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f"removed {f}")
        else:
            print(f"not found {f}")
    except Exception as e:
        print(f"error removing {f}: {e}")

print("cleanup done")
