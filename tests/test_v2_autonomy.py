from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

import qautonomy
from qcontracts import Action, Goal, Plan


def test_goal_plan_survive_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(qautonomy, "ROOT", tmp_path)
    monkeypatch.setattr(qautonomy, "GOALS", tmp_path / "goals")
    monkeypatch.setattr(qautonomy, "PLANS", tmp_path / "plans")

    goal = Goal("Persist after reboot", "intent_test", ["state survives"])
    action = Action("noop", {}, "test.noop", reversible=True)
    plan = Plan(goal.id, [action])

    qautonomy.save_goal(goal, active_plan_id=plan.id)
    qautonomy.save_plan(plan)

    loaded_goal = qautonomy.load_goal(goal.id)
    loaded_plan = qautonomy.load_plan(plan.id)

    assert loaded_goal.goal["id"] == goal.id
    assert loaded_goal.active_plan_id == plan.id
    assert loaded_plan.plan["id"] == plan.id
    assert loaded_plan.plan["actions"][0]["id"] == action.id


def test_resume_cursor_is_durable(tmp_path, monkeypatch):
    monkeypatch.setattr(qautonomy, "ROOT", tmp_path)
    monkeypatch.setattr(qautonomy, "GOALS", tmp_path / "goals")
    monkeypatch.setattr(qautonomy, "PLANS", tmp_path / "plans")

    goal = Goal("Resume", "intent_resume", ["continue from checkpoint"])
    actions = [
        Action("noop", {"n": 1}, "test.noop", reversible=True),
        Action("noop", {"n": 2}, "test.noop", reversible=True),
    ]
    plan = Plan(goal.id, actions)
    qautonomy.save_goal(goal, state="running", active_plan_id=plan.id)
    qautonomy.save_plan(plan, state="running")
    qautonomy.update_plan(plan.id, next_action=1, completed_action_ids=[actions[0].id])
    qautonomy.update_goal(goal.id, current_action=1)

    resumed = qautonomy.load_plan(plan.id)
    assert resumed.next_action == 1
    assert resumed.completed_action_ids == [actions[0].id]
    assert qautonomy.resumable_goals()[0].active_plan_id == plan.id


def test_atomic_state_rejects_invalid_transition(tmp_path, monkeypatch):
    monkeypatch.setattr(qautonomy, "ROOT", tmp_path)
    monkeypatch.setattr(qautonomy, "GOALS", tmp_path / "goals")
    monkeypatch.setattr(qautonomy, "PLANS", tmp_path / "plans")

    goal = Goal("Safe state", "intent_safe", ["valid state only"])
    qautonomy.save_goal(goal)
    try:
        qautonomy.update_goal(goal.id, state="teleported")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid goal state must be rejected")
