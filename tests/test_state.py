"""Tests for state backends."""

from concierge.state.memory import InMemoryBackend


class TestInMemoryBackend:
    def setup_method(self):
        self.backend = InMemoryBackend()

    def test_session_stage_roundtrip(self):
        self.backend.set_session_stage("s1", "onboarding")
        assert self.backend.get_session_stage("s1") == "onboarding"

    def test_session_stage_returns_none_when_unset(self):
        assert self.backend.get_session_stage("nonexistent") is None

    def test_session_stage_overwrite(self):
        self.backend.set_session_stage("s1", "stage_a")
        self.backend.set_session_stage("s1", "stage_b")
        assert self.backend.get_session_stage("s1") == "stage_b"

    def test_delete_session_stage(self):
        self.backend.set_session_stage("s1", "active")
        self.backend.delete_session_stage("s1")
        assert self.backend.get_session_stage("s1") is None

    def test_delete_nonexistent_stage_is_safe(self):
        self.backend.delete_session_stage("nonexistent")

    def test_state_roundtrip(self):
        self.backend.set_state("s1", "user_name", "Alice")
        assert self.backend.get_state("s1", "user_name") == "Alice"

    def test_state_returns_none_when_unset(self):
        assert self.backend.get_state("s1", "missing_key") is None

    def test_state_isolation_between_sessions(self):
        self.backend.set_state("s1", "key", "value_1")
        self.backend.set_state("s2", "key", "value_2")
        assert self.backend.get_state("s1", "key") == "value_1"
        assert self.backend.get_state("s2", "key") == "value_2"

    def test_clear_session_removes_stage_and_state(self):
        self.backend.set_session_stage("s1", "active")
        self.backend.set_state("s1", "counter", 42)
        self.backend.clear_session("s1")
        assert self.backend.get_session_stage("s1") is None
        assert self.backend.get_state("s1", "counter") is None

    def test_clear_session_does_not_affect_other_sessions(self):
        self.backend.set_state("s1", "key", "val1")
        self.backend.set_state("s2", "key", "val2")
        self.backend.clear_session("s1")
        assert self.backend.get_state("s2", "key") == "val2"
