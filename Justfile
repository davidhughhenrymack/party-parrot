
launch:
    poetry run python -m parrot.launch_stack $@

launch-fullscreen:
    poetry run python -m parrot.launch_stack --vj-fullscreen $@

launch-legacy:
    poetry run python -m parrot.main --legacy-gui $@

launch-profile:
    PROFILE_VJ=true PROFILE_VJ_INTERVAL=30 poetry run python -m parrot.main $@

launch-rave:
    poetry run python -m parrot.launch_stack --rave $@

launch-fixture:
    poetry run python -m parrot.launch_stack --fixture-mode $@

launch-runtime-only:
    poetry run python -m parrot.main $@

cloud:
    poetry run python -m parrot_cloud.main $@

launch-venue-editor:
    poetry run python -m parrot_cloud.main $@

seed-venue-editor:
    poetry run python -c "from parrot_cloud.management import initialize_database; initialize_database()"

test:
    poetry run python -m pytest

coverage:
    poetry run coverage report
