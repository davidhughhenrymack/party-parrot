
launch:
    poetry run python -m parrot.main $@

launch-vj:
    poetry run python parrot/main.py --no-gui --vj

launch-vj-fullscreen:
    poetry run python parrot/main.py --no-gui --vj --vj-fullscreen

test:
    poetry run python -m pytest

coverage:
    poetry run coverage report