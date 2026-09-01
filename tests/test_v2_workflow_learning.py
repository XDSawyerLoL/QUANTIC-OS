from services.qworkflow_learning import build_candidate, propose_compression, evaluate_candidate, promotion_gate


def episodes(n=4):
    steps=[
        {"tool":"inspect","arguments":{"path":"x"},"capability":"read","risk":"low","reversible":True},
        {"tool":"analyze","arguments":{"mode":"safe"},"capability":"read","risk":"low","reversible":True},
        {"tool":"write","arguments":{"path":"out"},"capability":"write","risk":"medium","reversible":True},
    ]
    return [{"ok":True,"verified":True,"receipt_id":f"r{i}","steps":steps} for i in range(n)]


def test_build_and_compress_without_authority_expansion():
    c=build_candidate("project_fix",episodes())
    assert len(c.steps)==3 and c.max_risk=="medium"
    c2=propose_compression(c,lambda s:[s[0],s[2]])
    assert len(c2.steps)==2


def test_compression_rejects_new_capability():
    c=build_candidate("project_fix",episodes())
    try:
        propose_compression(c,lambda s:[{"tool":"net","arguments":{},"capability":"network","risk":"low","reversible":True}])
        assert False
    except PermissionError:
        pass


def test_benchmark_and_promotion_gate():
    c=build_candidate("project_fix",episodes())
    c2=propose_compression(c,lambda s:[s[0],s[2]])
    ev=evaluate_candidate(c2,lambda:{"ok":True,"actions":3},lambda:{"ok":True,"actions":2},trials=5)
    assert ev.accepted
    assert promotion_gate(c2,ev,simulation_passed=True,regression_passed=True)["promote"]
    assert not promotion_gate(c2,ev,simulation_passed=False,regression_passed=True)["promote"]
