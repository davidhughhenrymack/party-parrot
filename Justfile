# Desktop GL app, venue editor on 4041 if needed; opens http://127.0.0.1:<web-port> (default 4040) in browser.
launch:
    poetry run python -m parrot.launch_stack $@


launch-profile:
    PROFILE_VJ=true PROFILE_VJ_INTERVAL=30 poetry run python -m parrot.main $@


launch-runtime-only:
    poetry run python -m parrot.main $@

# Headless PNG: golden sparkles + Muro dmack → test_output/prom_dmack_full.png
preview-prom:
    poetry run python -m parrot.vj.preview_prom_dmack

seed-venue-editor:
    poetry run python -c "from parrot_cloud.management import initialize_database; initialize_database()"

test:
    poetry run python -m pytest

coverage:
    poetry run coverage report
