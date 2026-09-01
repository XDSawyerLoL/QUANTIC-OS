from pathlib import Path

from services.qquantum_broker import decide, benchmark
from services.qmemory_reasoner import CausalMemory, route


def test_quantum_requires_supported_problem_and_backend():
    assert not decide('chat',backend_available=True,estimated_size=100).use_quantum
    assert not decide('search',backend_available=False,estimated_size=100).use_quantum
    assert decide('search',backend_available=True,estimated_size=100).use_quantum


def test_quantum_result_is_rejected_without_measured_advantage():
    def classical(_): return 'c', 1.0
    def quantum(_): return 'q', 0.5
    result, receipt=benchmark('search',{},classical=classical,quantum=quantum)
    assert result == 'c'
    assert not receipt.accepted


def test_temporal_supersession_and_causal_chain(tmp_path: Path):
    mem=CausalMemory(tmp_path/'reason.sqlite3')
    a=mem.assert_fact('project','status','prototype',memory_id='m1',provenance={'source':'user'},ts=1)
    b=mem.assert_fact('project','status','production',memory_id='m2',provenance={'source':'verified_receipt'},ts=2)
    mem.link_cause(a,b,relation='evolved_to',provenance={'source':'runtime'})
    assert mem.current_fact('project','status')['object']=='production'
    assert len(mem.history('project','status'))==2
    chain=mem.causal_chain(b)
    assert len(chain['facts'])==2
    mem.close()


def test_system_routes():
    assert route('Quel est le statut du projet ?').mode=='system1'
    assert route('Pourquoi le projet a changé après le test ?').mode=='system2'
