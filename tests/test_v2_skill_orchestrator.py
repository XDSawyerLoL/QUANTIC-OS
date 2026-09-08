from services.qskill_orchestrator import SkillProfile, choose_skill, build_delegation, orchestrate


def test_reuses_reliable_matching_skill():
    s=SkillProfile("repo-fix","1.0.0",["repo.read","repo.write"],["repo","fix","project"],success_rate=.96,samples=20,latency_ms=300)
    d=choose_skill("fix repo project",[s],required_capabilities=["repo.read"])
    assert d.mode=="reuse" and d.skill_name=="repo-fix"


def test_creates_when_no_compatible_skill():
    s=SkillProfile("read-only","1",["files.read"],["read"],success_rate=.99,samples=30)
    d=choose_skill("deploy application",[s],required_capabilities=["deploy.write"])
    assert d.mode=="create"


def test_delegation_never_expands_parent_authority():
    tasks=[{"role":"research","capabilities":["web.read"],"independent":True,"risk":"low"}]
    try:
        build_delegation(tasks,parent_capabilities=["files.read"])
        assert False
    except PermissionError:
        pass


def test_parallel_specialists_are_bounded():
    tasks=[
        {"agent":"researcher","role":"research","capabilities":["web.read"],"independent":True,"risk":"low","budget_actions":100},
        {"agent":"coder","role":"code","capabilities":["repo.write"],"independent":True,"risk":"medium","budget_actions":5},
        {"agent":"tester","role":"test","capabilities":["repo.read"],"independent":True,"risk":"low","budget_actions":5},
    ]
    plan=build_delegation(tasks,parent_capabilities=["web.read","repo.write","repo.read"],max_agents=3,per_agent_budget=8)
    assert plan.parallel and plan.max_parallel==3
    assert plan.agents[0].budget_actions==8


def test_orchestrator_chooses_skill_and_agents():
    skills=[SkillProfile("project-work","2",["repo.read","repo.write"],["project","fix"],success_rate=.95,samples=15)]
    tasks=[
        {"role":"inspect","capabilities":["repo.read"],"independent":True,"risk":"low"},
        {"role":"tests","capabilities":["repo.read"],"independent":True,"risk":"low"},
    ]
    out=orchestrate("fix project",skills,tasks,required_capabilities=["repo.read"],parent_capabilities=["repo.read","repo.write"],estimated_actions=6)
    assert out["skill"]["mode"]=="reuse"
    assert out["use_multi_agent"] is True
