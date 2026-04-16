"""Tests for live fixture state serialization (Party Parrot Cloud preview)."""

from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.led_par import ParRGB
from parrot.runtime_fixture_state import (
    build_fixture_runtime_payload,
    fixture_runtime_entry,
)
from parrot.utils.colour import Color


def test_fixture_runtime_entry_skips_without_cloud_id():
    par = ParRGB(1)
    par.set_color(Color("red"))
    par.set_dimmer(128)
    assert fixture_runtime_entry(par) is None


def test_fixture_runtime_entry_par_with_cloud():
    par = ParRGB(1)
    par.cloud_spec_id = "fx-1"
    par.set_color(Color("red"))
    par.set_dimmer(255)
    row = fixture_runtime_entry(par)
    assert row is not None
    assert row["id"] == "fx-1"
    assert row["dimmer"] == 1.0
    assert row["rgb"] == [1.0, 0.0, 0.0]
    assert "pan_deg" not in row


def test_moving_head_angles():
    spot = ChauvetSpot160_12Ch(1)
    spot.cloud_spec_id = "mh-1"
    spot.set_pan_angle(90.0)
    spot.set_tilt_angle(45.0)
    spot.set_dimmer(255)
    spot.set_color(Color("blue"))
    row = fixture_runtime_entry(spot)
    assert row is not None
    assert row["pan_deg"] == 90.0
    assert row["tilt_deg"] == 45.0


def test_motionstrip_bar_pan():
    strip = Motionstrip38(1, 0, 255, invert_pan=False)
    strip.cloud_spec_id = "ms-1"
    strip.set_dimmer(255)
    row = fixture_runtime_entry(strip)
    assert row is not None
    assert "bar_pan_deg" in row


def test_build_payload_flattens_fixture_group():
    from parrot.fixtures.base import FixtureGroup

    a = ParRGB(1)
    a.cloud_spec_id = "a"
    b = ParRGB(8)
    b.cloud_spec_id = "b"
    g = FixtureGroup([a, b], "pair")
    payload = build_fixture_runtime_payload([g], None)
    ids = {f["id"] for f in payload["fixtures"]}
    assert ids == {"a", "b"}
