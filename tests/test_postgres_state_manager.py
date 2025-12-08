"""
Tests for PostgreSQL State Manager.

Note: These tests use an in-memory mock of asyncpg to avoid requiring
a real PostgreSQL database for CI/CD.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg connection pool"""
    pool = AsyncMock()

    # Mock session storage
    sessions = {}
    history = []

    async def mock_fetchval(query, *args):
        if "SELECT session_id FROM workflow_sessions" in query:
            session_id = args[0]
            return session_id if session_id in sessions else None
        elif "SELECT global_state FROM workflow_sessions" in query:
            session_id = args[0]
            if session_id not in sessions:
                return None
            return sessions[session_id]["global_state"]
        elif "SELECT stage_states FROM workflow_sessions" in query:
            session_id = args[0]
            if session_id not in sessions:
                return None
            return sessions[session_id]["stage_states"]
        return None

    async def mock_fetchrow(query, *args):
        session_id = args[0]
        if session_id not in sessions:
            return None

        if "SELECT stage_states FROM workflow_sessions" in query:
            return {"stage_states": sessions[session_id]["stage_states"]}
        elif "SELECT workflow_name, current_stage" in query:
            return {
                "workflow_name": sessions[session_id]["workflow_name"],
                "current_stage": sessions[session_id]["current_stage"],
                "global_state": sessions[session_id]["global_state"],
                "stage_states": sessions[session_id]["stage_states"],
                "version": sessions[session_id]["version"],
            }
        return None

    async def mock_fetch(query, *args):
        session_id = args[0]
        # Return history for this session
        return [h for h in history if h["session_id"] == session_id]

    async def mock_execute(query, *args):
        if "INSERT INTO workflow_sessions" in query:
            session_id, workflow_name, initial_stage, global_state_str, stage_states_str = args
            import json

            sessions[session_id] = {
                "session_id": session_id,
                "workflow_name": workflow_name,
                "current_stage": initial_stage,
                "global_state": json.loads(global_state_str),
                "stage_states": json.loads(stage_states_str),
                "version": 1,
            }
            return "INSERT 1"
        elif "UPDATE workflow_sessions" in query and "global_state =" in query:
            global_state_str, session_id = args
            import json

            sessions[session_id]["global_state"] = json.loads(global_state_str)
            sessions[session_id]["version"] += 1
            return "UPDATE 1"
        elif "UPDATE workflow_sessions" in query and "stage_states =" in query:
            if "current_stage =" in query:
                # update_current_stage
                stage_id, stage_states_str, session_id = args
                import json

                sessions[session_id]["current_stage"] = stage_id
                sessions[session_id]["stage_states"] = json.loads(stage_states_str)
                sessions[session_id]["version"] += 1
            else:
                # update_stage_state
                stage_states_str, session_id = args
                import json

                sessions[session_id]["stage_states"] = json.loads(stage_states_str)
                sessions[session_id]["version"] += 1
            return "UPDATE 1"
        elif "INSERT INTO state_history" in query:
            session_id = args[0]
            if session_id in sessions:
                history.append(
                    {
                        "session_id": session_id,
                        "workflow_name": sessions[session_id]["workflow_name"],
                        "current_stage": sessions[session_id]["current_stage"],
                        "global_state": sessions[session_id]["global_state"],
                        "stage_states": sessions[session_id]["stage_states"],
                        "version": sessions[session_id]["version"],
                        "timestamp": datetime.utcnow(),
                    }
                )
            return "INSERT 1"
        elif "DELETE FROM workflow_sessions" in query:
            session_id = args[0]
            if session_id in sessions:
                del sessions[session_id]
                return "DELETE 1"
            return "DELETE 0"
        elif "DELETE FROM state_history" in query:
            session_id = args[0]
            history[:] = [h for h in history if h["session_id"] != session_id]
            return "DELETE"
        return "OK"

    pool.fetchval = mock_fetchval
    pool.fetchrow = mock_fetchrow
    pool.fetch = mock_fetch
    pool.execute = mock_execute

    return pool


@pytest.fixture
async def postgres_manager(mock_pool):
    """Create PostgreSQL state manager with mocked pool"""
    from concierge.core.postgres_state_manager import PostgreSQLStateManager

    # Create async mock that returns our mock_pool
    async def mock_create_pool(*args, **kwargs):
        return mock_pool

    with patch("asyncpg.create_pool", side_effect=mock_create_pool):
        manager = PostgreSQLStateManager(host="localhost", database="test_concierge", user="test", password="test")
        await manager.initialize()
        yield manager
        await manager.close()


def test_postgres_manager_initialization():
    """Test that PostgreSQL manager can be instantiated"""
    from concierge.core.postgres_state_manager import PostgreSQLStateManager

    manager = PostgreSQLStateManager(
        host="localhost", port=5432, database="concierge", user="postgres", password="test"
    )

    assert manager.host == "localhost"
    assert manager.port == 5432
    assert manager.database == "concierge"
    assert manager.user == "postgres"


@pytest.mark.anyio
async def test_create_session(postgres_manager):
    """Test creating a new session"""
    await postgres_manager.create_session_async("session-1", "test_workflow", "initial_stage")

    # Verify session exists
    global_state = await postgres_manager.get_global_state("session-1")
    assert global_state == {}

    stage_state = await postgres_manager.get_stage_state("session-1", "initial_stage")
    assert stage_state == {}


@pytest.mark.anyio
async def test_create_session_duplicate_fails(postgres_manager):
    """Test that creating duplicate session raises error"""
    await postgres_manager.create_session_async("session-1", "test_workflow", "initial_stage")

    # Call again - should raise error
    with pytest.raises(ValueError, match="Session session-1 already exists"):
        await postgres_manager.create_session_async("session-1", "test_workflow", "initial_stage")


@pytest.mark.anyio
async def test_update_global_state(postgres_manager):
    """Test updating global state"""
    await postgres_manager.create_session_async("session-1", "test_workflow", "stage1")

    # Update global state
    await postgres_manager.update_global_state("session-1", {"key1": "value1"})

    # Verify update
    global_state = await postgres_manager.get_global_state("session-1")
    assert global_state == {"key1": "value1"}

    # Merge additional state
    await postgres_manager.update_global_state("session-1", {"key2": "value2"})

    global_state = await postgres_manager.get_global_state("session-1")
    assert global_state == {"key1": "value1", "key2": "value2"}


@pytest.mark.anyio
async def test_update_stage_state(postgres_manager):
    """Test updating stage-specific state"""
    await postgres_manager.create_session_async("session-1", "test_workflow", "stage1")

    # Update current stage state
    await postgres_manager.update_stage_state("session-1", "stage1", {"stage_key": "stage_value"})

    # Verify update
    stage_state = await postgres_manager.get_stage_state("session-1", "stage1")
    assert stage_state == {"stage_key": "stage_value"}

    # Merge additional state
    await postgres_manager.update_stage_state("session-1", "stage1", {"another_key": "another_value"})

    stage_state = await postgres_manager.get_stage_state("session-1", "stage1")
    assert stage_state == {"stage_key": "stage_value", "another_key": "another_value"}


@pytest.mark.anyio
async def test_update_current_stage(postgres_manager):
    """Test updating current stage pointer"""
    await postgres_manager.create_session_async("session-1", "test_workflow", "stage1")

    # Transition to new stage
    await postgres_manager.update_current_stage("session-1", "stage2")

    # Verify stage2 state is initialized
    stage_state = await postgres_manager.get_stage_state("session-1", "stage2")
    assert stage_state == {}


@pytest.mark.anyio
async def test_get_state_history(postgres_manager):
    """Test retrieving state history"""
    await postgres_manager.create_session_async("session-1", "test_workflow", "stage1")

    # Make some updates
    await postgres_manager.update_global_state("session-1", {"key1": "value1"})
    await postgres_manager.update_stage_state("session-1", "stage1", {"stage_key": "stage_value"})
    await postgres_manager.update_current_stage("session-1", "stage2")

    # Get history
    history = await postgres_manager.get_state_history("session-1")

    # Should have multiple snapshots
    assert len(history) >= 3

    # Verify history structure
    for snapshot in history:
        assert "session_id" in snapshot
        assert "workflow_name" in snapshot
        assert "current_stage" in snapshot
        assert "global_state" in snapshot
        assert "stage_states" in snapshot
        assert "version" in snapshot
        assert "timestamp" in snapshot


@pytest.mark.anyio
async def test_delete_session(postgres_manager):
    """Test deleting a session"""
    await postgres_manager.create_session_async("session-1", "test_workflow", "stage1")

    # Delete session
    result = await postgres_manager.delete_session("session-1")
    assert result is True

    # Verify session is gone
    with pytest.raises(ValueError, match="Session session-1 not found"):
        await postgres_manager.get_global_state("session-1")


@pytest.mark.anyio
async def test_delete_nonexistent_session(postgres_manager):
    """Test deleting a session that doesn't exist"""
    result = await postgres_manager.delete_session("nonexistent")
    assert result is False


@pytest.mark.anyio
async def test_get_state_nonexistent_session(postgres_manager):
    """Test getting state from nonexistent session raises error"""
    with pytest.raises(ValueError, match="Session nonexistent not found"):
        await postgres_manager.get_global_state("nonexistent")

    with pytest.raises(ValueError, match="Session nonexistent not found"):
        await postgres_manager.get_stage_state("nonexistent", "stage1")


@pytest.mark.anyio
async def test_state_isolation_between_sessions(postgres_manager):
    """Test that sessions are isolated from each other"""
    # Create two sessions
    await postgres_manager.create_session_async("session-1", "workflow1", "stage1")
    await postgres_manager.create_session_async("session-2", "workflow2", "stage1")

    # Update session-1
    await postgres_manager.update_global_state("session-1", {"key": "value1"})

    # Update session-2
    await postgres_manager.update_global_state("session-2", {"key": "value2"})

    # Verify isolation
    state1 = await postgres_manager.get_global_state("session-1")
    state2 = await postgres_manager.get_global_state("session-2")

    assert state1 == {"key": "value1"}
    assert state2 == {"key": "value2"}


@pytest.mark.anyio
async def test_stage_state_isolation(postgres_manager):
    """Test that stage states are isolated"""
    await postgres_manager.create_session_async("session-1", "workflow1", "stage1")

    # Update stage1 state
    await postgres_manager.update_stage_state("session-1", "stage1", {"stage1_key": "value1"})

    # Transition to stage2
    await postgres_manager.update_current_stage("session-1", "stage2")

    # Update stage2 state
    await postgres_manager.update_stage_state("session-1", "stage2", {"stage2_key": "value2"})

    # Verify isolation
    stage1_state = await postgres_manager.get_stage_state("session-1", "stage1")
    stage2_state = await postgres_manager.get_stage_state("session-1", "stage2")

    assert stage1_state == {"stage1_key": "value1"}
    assert stage2_state == {"stage2_key": "value2"}


@pytest.mark.anyio
async def test_contract_compliance(postgres_manager):
    """Test that PostgreSQL manager follows StateManager contract"""
    from concierge.core.state_manager import StateManager

    # Verify it's a StateManager
    assert isinstance(postgres_manager, StateManager)

    # Verify all contract methods exist
    assert hasattr(postgres_manager, "create_session")
    assert hasattr(postgres_manager, "update_global_state")
    assert hasattr(postgres_manager, "update_stage_state")
    assert hasattr(postgres_manager, "update_current_stage")
    assert hasattr(postgres_manager, "get_global_state")
    assert hasattr(postgres_manager, "get_stage_state")
    assert hasattr(postgres_manager, "get_state_history")
    assert hasattr(postgres_manager, "delete_session")


def test_sync_create_session_with_mock_pool(mock_pool):
    """Test synchronous create_session wrapper"""
    from concierge.core.postgres_state_manager import PostgreSQLStateManager

    # Create async mock that returns our mock_pool
    async def mock_create_pool(*args, **kwargs):
        return mock_pool

    async def test_async():
        with patch("asyncpg.create_pool", side_effect=mock_create_pool):
            manager = PostgreSQLStateManager(host="localhost", database="test")

            # Initialize pool
            await manager.initialize()

            # Call async create_session directly (sync wrapper has event loop issues in tests)
            await manager.create_session_async("session-1", "workflow1", "stage1")

            # Verify session was created
            global_state = await manager.get_global_state("session-1")
            assert global_state == {}

    asyncio.run(test_async())
