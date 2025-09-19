
launch:
    poetry run python -m parrot.main $@

test:
    poetry run python -m pytest

coverage:
    poetry run coverage report