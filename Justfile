
launch:
    poetry run python -m parrot.main $@

launch-profile:
    PROFILE_VJ=true PROFILE_VJ_INTERVAL=30 poetry run python -m parrot.main $@

test:
    poetry run python -m pytest

coverage:
    poetry run coverage report

render-lasers out="test_output/laser_array.png":
    poetry run python -m parrot.vj.nodes.laser_array_render --out {{out}}

analyze-lasers img="test_output/laser_array.png":
    poetry run python -m parrot.vj.nodes.beam_image_analyzer {{img}}