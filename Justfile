
launch:
    poetry run python -m parrot.main $@

launch-fullscreen:
    poetry run python -m parrot.main --vj-fullscreen $@

launch-legacy:
    poetry run python -m parrot.main --legacy-gui $@

launch-profile:
    PROFILE_VJ=true PROFILE_VJ_INTERVAL=30 poetry run python -m parrot.main $@

launch-rave:
    poetry run python -m parrot.main --rave $@

test:
    poetry run python -m pytest

coverage:
    poetry run coverage report
