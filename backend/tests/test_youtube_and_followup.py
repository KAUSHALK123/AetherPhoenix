import uuid
from app.agents.planner.agent import PlannerAgent
from shared.contracts.planner import PlannerRequest

def test_youtube_play_decomposition():
    agent = PlannerAgent()
    session_id = str(uuid.uuid4())
    req = PlannerRequest(session_id=session_id, message="open utube and play lofi music")
    res = agent.process_request(req)
    assert res.status == "ready"
    assert "lofi" in res.reply.lower()
    assert "play" in res.reply.lower()

def test_multi_turn_followup_context_retention():
    agent = PlannerAgent()
    session_id = str(uuid.uuid4())
    
    # Turn 1: Initial request
    req1 = PlannerRequest(session_id=session_id, message="open utube and play lofi music")
    res1 = agent.process_request(req1)
    assert res1.status == "ready"
    
    # Turn 2: Follow-up prompt like "play it" or "play the music"
    req2 = PlannerRequest(session_id=session_id, message="play the music")
    res2 = agent.process_request(req2)
    # The agent should retain context that the session is about YouTube / lofi music
    assert res2.status == "ready"
    assert "lofi" in res2.reply.lower() or "youtube" in res2.reply.lower()
