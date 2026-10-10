"""Unit tests for MeshManagerBot."""

from hath0r_cli.bots.mesh_manager_bot import MeshManagerBot


def test_mesh_bot_status():
    bot = MeshManagerBot()
    st = bot.status()
    assert st["status"] == "ONLINE"
    assert st["bot_name"] == "MeshManagerBot"
    assert "supported_intents" in st


def test_mesh_bot_list_peers():
    bot = MeshManagerBot()
    peers = bot.list_peers()
    assert len(peers) >= 2
    assert any(p["peer_id"] == "peer-poc" for p in peers)


def test_mesh_bot_ping_peer():
    bot = MeshManagerBot()
    res = bot.ping_peer("peer-poc")
    assert res["status"] == "ONLINE"
    assert res["signature_verified"] is True


def test_mesh_bot_route_query():
    bot = MeshManagerBot()
    res = bot.route_query(peer_id="peer-poc", topic_query="governance")
    assert res["status"] == "DELIVERED"
    assert res["resolved_peer"] == "peer-poc"


def test_mesh_bot_conversational_intents():
    bot = MeshManagerBot()
    r1 = bot.handle_conversational_intent("list peers")
    assert "peers" in r1

    r2 = bot.handle_conversational_intent("ping peer")
    assert r2["status"] == "ONLINE"
