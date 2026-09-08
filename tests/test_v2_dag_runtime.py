from services.qdag_runtime import DagNode, DagState, execute_dag, replan_from_change, validate_dag


def _nodes():
    return [
        DagNode("a",{"work":"inspect"},[],["read"]),
        DagNode("b",{"work":"analyze"},["a"],["read"]),
        DagNode("c",{"work":"independent"},[],["read"]),
        DagNode("d",{"work":"write"},["b"],["write"],risk="medium"),
    ]


def test_dag_executes_dependencies_and_parallel_roots():
    seen=[]
    def worker(node,ctx):
        seen.append(node["id"])
        return {"ok":True,"result":node["task"]["work"]}
    out=execute_dag(_nodes(),worker=worker,parent_capabilities=["read","write"])
    assert out["ok"]
    assert out["state"]["status"]["d"]=="done"
    assert set(seen)=={"a","b","c","d"}


def test_replan_preserves_unaffected_branch():
    counts={k:0 for k in "abcd"}
    def worker(node,ctx):
        counts[node["id"]]+=1
        return {"ok":True,"result":f"{node['id']}:{counts[node['id']]}"}
    first=execute_dag(_nodes(),worker=worker,parent_capabilities=["read","write"])
    state=DagState(**first["state"])
    out=replan_from_change(_nodes(),state,changed_nodes=["a"],worker=worker,parent_capabilities=["read","write"])
    assert out["ok"]
    assert set(out["replanned_nodes"])=={"a","b","d"}
    assert out["preserved_nodes"]==["c"]
    assert counts["c"]==1
    assert counts["a"]==2 and counts["b"]==2 and counts["d"]==2


def test_failure_invalidates_descendants_only():
    def worker(node,ctx):
        if node["id"]=="b": return {"ok":False,"error":"bad assumption"}
        return {"ok":True,"result":node["id"]}
    out=execute_dag(_nodes(),worker=worker,parent_capabilities=["read","write"])
    assert not out["ok"] and out["failed"]==["b"]
    assert out["invalidated"]==["d"]
    assert out["state"]["status"]["c"]=="done"


def test_rejects_cycle_and_authority_expansion():
    cyc=[DagNode("a",{},["b"],["read"]),DagNode("b",{},["a"],["read"])]
    try:
        validate_dag(cyc); assert False
    except ValueError:
        pass
    try:
        execute_dag([DagNode("x",{},[],["admin"])],worker=lambda n,c:{"ok":True},parent_capabilities=["read"])
        assert False
    except PermissionError:
        pass
