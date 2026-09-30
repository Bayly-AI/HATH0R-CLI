from hath0r_cli.factory_manager import FactoryManagerBot
from hath0r_cli.step_runner import BotRegistry, execute_workflow


def test_update_cli_factory_validation():
    manager = FactoryManagerBot()
    factories = manager.list_factories()
    factory_ids = [f["id"] for f in factories]
    assert "update-cli-factory" in factory_ids

    factory_data = manager.get_factory("update-cli-factory")
    assert factory_data is not None
    assert factory_data["name"] == "CLI Update, Validation, Knowledge Share & Release Factory"
    assert len(factory_data["workflows"]) == 1
    assert factory_data["workflows"][0]["id"] == "update-cli"


def test_update_cli_factory_dry_run():
    manager = FactoryManagerBot()
    factory_data = manager.get_factory("update-cli-factory")
    assert factory_data is not None

    registry = BotRegistry()
    workflow_def = factory_data["workflows"][0]
    wf_res = execute_workflow(workflow_def, registry=registry, dry_run=True)

    assert wf_res.workflow_id == "update-cli"
    assert wf_res.success is True
    assert len(wf_res.steps) == 11
    for step in wf_res.steps:
        assert step.success is True
