import os
import time

import pytest

from ci_watson.resource_tracker import (
    ResourceTracker,
    _TrackPeakMemory,
    _TrackRuntime,
)


class FakeNode:
    def __init__(self):
        self.user_properties = []


class FakeRequest:
    def __init__(self):
        self.node = FakeNode()


def test_runtime():
    tracker = _TrackRuntime()
    with tracker:
        time.sleep(1.0)
    # a 1 second sleep is sometimes too much to ask
    # of CI runners. Use a wide margin to make this test
    # less brittle in those cases.
    threshold = 0.5 if "CI" in os.environ else 0.1
    assert abs(tracker.log()[1] - 1.0) < threshold


def test_memory():
    tracker = _TrackPeakMemory()
    N = 1024 * 1024
    with tracker:
        b = b"0" * N  # noqa: F841
    assert abs(tracker.log()[1] - N) / N < 0.01


def test_resource_tracker():
    tracker = ResourceTracker()
    with tracker.track():
        pass
    fake_request = FakeRequest()
    tracker.log(fake_request)
    keys = {log[0] for log in fake_request.node.user_properties}
    assert keys == {"tracked-time", "tracked-peakmem"}


def test_log():
    tracker = ResourceTracker()
    fake_request = FakeRequest()
    with tracker.track(log=fake_request):
        pass
    keys = {log[0] for log in fake_request.node.user_properties}
    assert keys == {"tracked-time", "tracked-peakmem"}


@pytest.fixture(scope="module")
def long_fixture(resource_tracker):
    with resource_tracker.track():
        pass


def test_fixture_log_tracked_resources(log_tracked_resources, long_fixture, request):
    log_tracked_resources()
    keys = {log[0] for log in request.node.user_properties}
    assert keys == {"tracked-time", "tracked-peakmem"}


def test_fixutre_log_in_test(resource_tracker, request):
    with resource_tracker.track(log=request):
        pass
    keys = {log[0] for log in request.node.user_properties}
    assert keys == {"tracked-time", "tracked-peakmem"}
