"""Local checks for admission lanes (no GPU / no network)."""

import asyncio
import unittest

from gateway.lanes import ClientGone, Lane, LaneFull


class FakeRequest:
    def __init__(self, disconnected: bool = False):
        self._disconnected = disconnected

    async def is_disconnected(self) -> bool:
        return self._disconnected


class LaneTests(unittest.IsolatedAsyncioTestCase):
    async def test_fifth_waiter_is_rejected_when_inflight_full(self):
        lane = Lane("t", inflight=1, max_waiters=4)
        await lane.enter_line()
        await lane.wait_blocking(FakeRequest())
        self.assertEqual(lane.occupancy, 1)

        wait_tasks = []
        for _ in range(4):
            await lane.enter_line()
            wait_tasks.append(
                asyncio.create_task(lane.wait_blocking(FakeRequest()))
            )
            await asyncio.sleep(0)

        with self.assertRaises(LaneFull):
            await lane.enter_line()

        lane.release()
        await wait_tasks[0]
        for task in wait_tasks[1:]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        lane.release()

    async def test_burst_fills_inflight_plus_waiters(self):
        lane = Lane("t", inflight=1, max_waiters=4)
        for _ in range(5):
            await lane.enter_line()
        with self.assertRaises(LaneFull):
            await lane.enter_line()
        self.assertEqual(lane.waiting, 5)
        self.assertEqual(lane.occupancy, 5)

    async def test_disconnect_frees_waiter_slot(self):
        lane = Lane("t", inflight=1, max_waiters=4)
        await lane.enter_line()
        await lane.wait_blocking(FakeRequest())

        await lane.enter_line()
        with self.assertRaises(ClientGone):
            await lane.wait_blocking(FakeRequest(disconnected=True))
        self.assertEqual(lane.waiting, 0)

        await lane.enter_line()
        self.assertEqual(lane.waiting, 1)
        with self.assertRaises(ClientGone):
            await lane.wait_blocking(FakeRequest(disconnected=True))
        self.assertEqual(lane.waiting, 0)
        lane.release()


if __name__ == "__main__":
    unittest.main()
