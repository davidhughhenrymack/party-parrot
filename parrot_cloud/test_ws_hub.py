from unittest.mock import Mock

from parrot_cloud.ws_hub import VenueUpdateHub


def test_broadcast_sends_payload_to_all_clients():
    hub = VenueUpdateHub()
    first = Mock()
    second = Mock()
    hub.add_client(first)
    hub.add_client(second)

    hub.broadcast({"type": "bootstrap", "data": {"venues": []}})

    first.send.assert_called_once()
    second.send.assert_called_once()
