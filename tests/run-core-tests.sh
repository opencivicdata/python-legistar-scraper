# Just runs the core tests without coverage or network access.
export PYTHONPATH=.; py.test -k test_core -s -v tests/
