from services.qmultiagent_runtime import execute_team
from services.qskill_orchestrator import AgentSpec, DelegationPlan


def _plan():
    agents=[
        AgentSpec("research","research",["read"],3,"low"),
        AgentSpec("review","review",["read"],3,"low"),
    ]
    return DelegationPlan(agents,True,2,"test")


def test_parallel_team_success_and_final_verification():
    def worker(spec, task):
        return {"ok":True,"result":task["value"],"evidence":{"agent":spec.name},"claims":{"status":"ok"}}
    receipt=execute_team(_plan(),[{"value":1},{"value":2}],worker=worker,parent_capabilities=["read"],verifier=lambda agg:(agg["successful_agents"]==2,"all_evidence_present"))
    assert receipt.ok
    assert receipt.stage=="complete"
    assert receipt.verification["passed"]


def test_only_failed_agent_is_retried():
    calls={"research":0,"review":0}
    def worker(spec, task):
        calls[spec.name]+=1
        if spec.name=="review" and calls[spec.name]==1:
            return {"ok":False,"error":"transient"}
        return {"ok":True,"result":spec.name,"claims":{"status":"ok"}}
    receipt=execute_team(_plan(),[{},{}],worker=worker,parent_capabilities=["read"],max_retries_per_agent=1)
    assert receipt.ok
    assert calls["research"]==1
    assert calls["review"]==2
    assert receipt.retried_agents==["review"]


def test_conflict_blocks_team_completion():
    def worker(spec, task):
        return {"ok":True,"result":spec.name,"claims":{"answer":task["answer"]}}
    receipt=execute_team(_plan(),[{"answer":"A"},{"answer":"B"}],worker=worker,parent_capabilities=["read"])
    assert not receipt.ok
    assert receipt.stage=="conflict"
    assert receipt.conflicts


def test_child_cannot_expand_parent_authority():
    plan=DelegationPlan([AgentSpec("net","network",["network"],2,"low")],False,1,"test")
    try:
        execute_team(plan,[{}],worker=lambda *_:{"ok":True},parent_capabilities=["read"])
        assert False
    except PermissionError:
        pass
