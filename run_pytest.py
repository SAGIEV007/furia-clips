import pytest
exit_code = pytest.main(['--tb=short', '-q', '--color=no'])
print(f"EXIT_CODE={exit_code}")
