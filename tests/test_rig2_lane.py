"""The gateway's optional Rig 2 lane: own upstream, own stored key. No GPU / no network."""

import unittest
from unittest import mock

from fastapi.testclient import TestClient

from gateway import lanes as gateway_lanes
from gateway import main as gateway_main
from gateway.config import settings

STUDENT_KEY = "student-key"
RIG2_KEY = "rig2-key"
RIG2_URL = "http://rig2.test:9000"
RIG2_MODEL = "qwen3.6:35b-a3b"


def rig2_settings():
    return mock.patch.multiple(
        settings,
        PUBLIC_API_KEYS=[STUDENT_KEY],
        RIG2_MODEL_ALIAS=RIG2_MODEL,
        RIG2_UPSTREAM_URL=RIG2_URL,
        RIG2_UPSTREAM_API_KEY=RIG2_KEY,
        RIG2_INFLIGHT=2,
    )


class Rig2LaneTests(unittest.TestCase):
    def test_no_rig2_lane_by_default(self):
        with mock.patch.object(settings, "RIG2_MODEL_ALIAS", ""):
            self.assertNotIn(RIG2_MODEL, gateway_lanes._lanes())

    def test_rig2_lane_has_its_own_upstream_and_key(self):
        with rig2_settings():
            built = gateway_lanes._lanes()
        lane = built[RIG2_MODEL]
        self.assertEqual((lane.upstream_url, lane.upstream_key), (RIG2_URL, RIG2_KEY))
        self.assertEqual(lane.inflight_limit, 2)
        rig1 = built[settings.GROUP_A_MODEL_ALIAS]
        self.assertEqual((rig1.upstream_url, rig1.upstream_key), (settings.UPSTREAM_URL, None))


class Rig2RoutingTests(unittest.TestCase):
    def setUp(self):
        patcher = rig2_settings()
        patcher.start()
        self.addCleanup(patcher.stop)
        lanes_patch = mock.patch.dict(gateway_main.lanes, gateway_lanes._lanes(), clear=True)
        lanes_patch.start()
        self.addCleanup(lanes_patch.stop)
        self.client = TestClient(gateway_main.app)
        self.auth = {"Authorization": f"Bearer {STUDENT_KEY}"}

    def _chat(self, model):
        calls = []

        async def fake_blocking(path, body, api_key, base_url=None):
            calls.append((api_key, base_url))
            return 200, {"ok": True}

        with mock.patch.object(gateway_main, "proxy_blocking", fake_blocking):
            resp = self.client.post(
                "/v1/chat/completions", json={"model": model}, headers=self.auth
            )
        self.assertEqual(resp.status_code, 200)
        return calls

    def test_rig2_model_goes_to_rig2_with_stored_key(self):
        self.assertEqual(self._chat(RIG2_MODEL), [(RIG2_KEY, RIG2_URL)])

    def test_rig1_model_keeps_callers_key(self):
        self.assertEqual(
            self._chat(settings.GROUP_A_MODEL_ALIAS), [(STUDENT_KEY, settings.UPSTREAM_URL)]
        )

    def test_rig2_key_alone_is_not_accepted_from_callers(self):
        resp = self.client.post(
            "/v1/chat/completions",
            json={"model": RIG2_MODEL},
            headers={"Authorization": f"Bearer {RIG2_KEY}"},
        )
        self.assertEqual(resp.status_code, 401)

    def _models(self, rig2_result):
        async def fake_get(path, api_key, base_url=None):
            if base_url == RIG2_URL:
                self.assertEqual(api_key, RIG2_KEY)
                if isinstance(rig2_result, Exception):
                    raise rig2_result
                return rig2_result
            return 200, {"object": "list", "data": [{"id": "qwen3.8:27b"}]}

        with mock.patch.object(gateway_main, "proxy_get", fake_get):
            resp = self.client.get("/v1/models", headers=self.auth)
        self.assertEqual(resp.status_code, 200)
        return [m["id"] for m in resp.json()["data"]]

    def test_models_lists_both_rigs(self):
        ids = self._models((200, {"data": [{"id": RIG2_MODEL}]}))
        self.assertEqual(ids, ["qwen3.8:27b", RIG2_MODEL])

    def test_models_survives_rig2_down(self):
        self.assertEqual(self._models(OSError("down")), ["qwen3.8:27b"])


if __name__ == "__main__":
    unittest.main()
