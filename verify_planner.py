import json
import os
import sys
from uuid import uuid4

# Add both to sys.path
sys.path.insert(0, os.path.abspath('backend'))
sys.path.insert(0, os.path.abspath('.'))

from app.agents.planner.agent import PlannerAgent

from shared.contracts.planner import PlannerRequest


def test_planner(goal: str, clarification: str | None = None):
    print(f"\n--- Testing Goal: '{goal}' ---")
    agent = PlannerAgent()
    request = PlannerRequest(
        session_id=str(uuid4()),
        message=goal,
        context={}
    )
    
    response = agent.process_request(request)
    if response.status == "clarifying" and clarification:
        print("STATUS: clarifying. Providing clarification:", clarification)
        request2 = PlannerRequest(
            session_id=request.session_id,
            message=clarification,
            context={}
        )
        response = agent.process_request(request2)

    print("STATUS:", response.status)
    if response.status == "ready":
        plan = json.loads(response.reply)
        
        print("\nOverall Execution Summary:")
        print(plan.get("execution_summary"))
        
        print("\nRisks Array:")
        for r in plan.get("risks", []):
            print(f"  - {r}")
            
    elif response.status == "clarifying":
        print("Planner asked for clarification:", response.reply)
        
if __name__ == "__main__":
    test_planner("Create a Presentation on cars")
    test_planner(
        "organize my files",
        clarification=(
            "Create a powershell script to organize my files into folders"
            " based on extensions."
        ),
    )
