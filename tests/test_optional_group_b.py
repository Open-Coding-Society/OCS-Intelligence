"""An empty GROUP_B_MODEL_ALIAS drops Worker B (Rig 2 serves one model). No GPU / no network."""

import unittest
from unittest import mock

from gateway import lanes as gateway_lanes
from gateway.config import settings as gateway_settings
from orchestrator import main as orchestrator_main
from orchestrator.config import settings as orchestrator_settings


class GatewayLaneTests(unittest.TestCase):
    def test_default_has_both_lanes(self):
        self.assertEqual(
            set(gateway_lanes._lanes()),
            {gateway_settings.GROUP_A_MODEL_ALIAS, gateway_settings.GROUP_B_MODEL_ALIAS},
        )

    def test_empty_group_b_alias_has_only_group_a_lane(self):
        with mock.patch.object(gateway_settings, "GROUP_B_MODEL_ALIAS", ""):
            built = gateway_lanes._lanes()
        self.assertEqual(list(built), [gateway_settings.GROUP_A_MODEL_ALIAS])
        self.assertEqual(
            built[gateway_settings.GROUP_A_MODEL_ALIAS].inflight_limit,
            gateway_settings.GROUP_A_INFLIGHT,
        )


class OrchestratorWorkerTests(unittest.TestCase):
    def test_default_registers_both_workers(self):
        names = [w.name for w in orchestrator_main.configured_workers()]
        self.assertEqual(names, ["group-a", "group-b"])

    def test_empty_group_b_alias_registers_only_group_a(self):
        with mock.patch.object(orchestrator_settings, "GROUP_B_MODEL_ALIAS", ""):
            workers = orchestrator_main.configured_workers()
        self.assertEqual([w.name for w in workers], ["group-a"])
        self.assertEqual(workers[0].model_alias, orchestrator_settings.GROUP_A_MODEL_ALIAS)


if __name__ == "__main__":
    unittest.main()
