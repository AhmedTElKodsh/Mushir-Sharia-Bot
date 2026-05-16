"""StorageAdapter pattern tests.

Validates that the StorageAdapter abstraction behaves correctly using a
Python mock that mirrors the Web Storage API (same as MockStorage in JS).
The StorageAdapter itself is a thin wrapper — the same logic works
identically in JavaScript and Python, so this test proves the pattern.

Also checks that ``src/static/js/storage.js`` contains the expected class
definitions so structural regressions are caught at CI time.
"""

import pytest


# ===================================================================
# Python equivalent of the JS MockStorage (Map-backed)
# ===================================================================


class _MockStorage:
    """In-memory key-value store implementing the Web Storage API subset.

    Mirrors the ``MockStorage`` class in ``src/static/js/storage.js``.
    """

    def __init__(self):
        self._data: dict[str, str] = {}

    def getItem(self, key: str) -> str | None:  # noqa: N802
        return self._data.get(key)

    def setItem(self, key: str, value: str) -> None:  # noqa: N802
        self._data[key] = str(value)

    def removeItem(self, key: str) -> None:  # noqa: N802
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> set[str]:
        """Expose stored keys for introspection (not part of Web Storage API)."""
        return set(self._data.keys())


# ===================================================================
# Python equivalent of the JS StorageAdapter
# ===================================================================


class _StorageAdapter:
    """Port of the JS ``StorageAdapter`` for pattern validation.

    Same logic — the real implementation is in JavaScript at
    ``src/static/js/storage.js``.
    """

    def __init__(self, storage=None, schema_version: int = 1):
        self._storage = storage or _MockStorage()
        self.schema_version = schema_version

    def get(self, key: str) -> str | None:
        try:
            return self._storage.getItem(key)
        except Exception:
            return None

    def set(self, key: str, value: str) -> None:
        try:
            self._storage.setItem(key, str(value))
        except Exception:
            pass

    def remove(self, key: str) -> None:
        try:
            self._storage.removeItem(key)
        except Exception:
            pass

    def clear(self) -> None:
        try:
            self._storage.clear()
        except Exception:
            pass

    def migrate(self, from_version: int, to_version: int) -> bool:
        """Placeholder — override in subclasses for real migrations."""
        return True

    def setObject(self, key: str, value) -> None:  # noqa: N802
        """Store a JSON-serializable value."""
        try:
            import json
            self._storage.setItem(key, json.dumps(value))
        except Exception as e:
            import warnings
            warnings.warn(f"StorageAdapter: quota exceeded — {e}")

    def getObject(self, key: str):  # noqa: N802
        """Retrieve and parse a JSON value from storage."""
        try:
            import json
            raw = self._storage.getItem(key)
            return json.loads(raw) if raw is not None else None
        except Exception:
            return None

    CONVERSATION_KEY = "mushir_conversation"

    def saveConversation(self, session_id: str, messages: list) -> None:  # noqa: N802
        """Persist the full conversation array."""
        import time
        data = {
            "messages": messages,
            "session_id": session_id,
            "timestamp": int(time.time() * 1000),
        }
        self.setObject(self.CONVERSATION_KEY, data)

    def restoreConversation(self, session_id: str):  # noqa: N802
        """Restore the persisted conversation object."""
        return self.getObject(self.CONVERSATION_KEY)

    def clearConversation(self) -> None:  # noqa: N802
        """Remove the conversation data from storage."""
        try:
            self._storage.removeItem(self.CONVERSATION_KEY)
        except Exception:
            pass


# ===================================================================
# Tests
# ===================================================================


@pytest.mark.unit
class TestMockStorage:
    """Verify the mock storage itself works correctly."""

    def test_get_returns_none_for_missing_key(self):
        store = _MockStorage()
        assert store.getItem("missing") is None

    def test_set_and_get_round_trip(self):
        store = _MockStorage()
        store.setItem("key1", "value1")
        assert store.getItem("key1") == "value1"

    def test_set_coerces_to_string(self):
        store = _MockStorage()
        store.setItem("num", 42)
        assert store.getItem("num") == "42"
        assert isinstance(store.getItem("num"), str)

    def test_remove_deletes_key(self):
        store = _MockStorage()
        store.setItem("tmp", "data")
        store.removeItem("tmp")
        assert store.getItem("tmp") is None

    def test_clear_removes_all_keys(self):
        store = _MockStorage()
        store.setItem("a", "1")
        store.setItem("b", "2")
        store.clear()
        assert store.getItem("a") is None
        assert store.getItem("b") is None
        assert len(store) == 0

    def test_remove_nonexistent_key_does_not_raise(self):
        store = _MockStorage()
        store.removeItem("never_set")  # should not raise


@pytest.mark.unit
class TestStorageAdapter:
    """Verify the adapter layer on top of MockStorage."""

    def test_default_storage_is_mock(self):
        adapter = _StorageAdapter()
        assert adapter._storage is not None

    def test_default_schema_version(self):
        adapter = _StorageAdapter()
        assert adapter.schema_version == 1

    def test_custom_schema_version(self):
        adapter = _StorageAdapter(schema_version=3)
        assert adapter.schema_version == 3

    def test_get_returns_none_for_missing_key(self):
        adapter = _StorageAdapter()
        assert adapter.get("missing") is None

    def test_set_and_get_round_trip(self):
        adapter = _StorageAdapter()
        adapter.set("pref", "dark-mode")
        assert adapter.get("pref") == "dark-mode"

    def test_set_coerces_to_string(self):
        adapter = _StorageAdapter()
        adapter.set("count", 100)
        assert adapter.get("count") == "100"

    def test_remove_deletes_key(self):
        adapter = _StorageAdapter()
        adapter.set("tmp", "value")
        adapter.remove("tmp")
        assert adapter.get("tmp") is None

    def test_remove_missing_key_does_not_raise(self):
        adapter = _StorageAdapter()
        adapter.remove("nonexistent")  # should not raise

    def test_clear_removes_all_keys(self):
        adapter = _StorageAdapter()
        adapter.set("a", "1")
        adapter.set("b", "2")
        adapter.clear()
        assert adapter.get("a") is None
        assert adapter.get("b") is None

    def test_get_handles_storage_error_gracefully(self):
        """Simulate a broken storage that raises on getItem."""
        class BrokenStorage:
            @staticmethod
            def getItem(_key):
                raise RuntimeError("storage unavailable")
            @staticmethod
            def setItem(_key, _value):
                pass
            @staticmethod
            def removeItem(_key):
                pass
            @staticmethod
            def clear():
                pass

        adapter = _StorageAdapter(storage=BrokenStorage())
        assert adapter.get("any") is None

    def test_set_handles_storage_error_gracefully(self):
        """Simulate a broken storage that raises on setItem."""
        class BrokenStorage:
            @staticmethod
            def getItem(key):
                return None
            @staticmethod
            def setItem(_key, _value):
                raise RuntimeError("quota exceeded")
            @staticmethod
            def removeItem(_key):
                pass
            @staticmethod
            def clear():
                pass

        adapter = _StorageAdapter(storage=BrokenStorage())
        adapter.set("key", "value")  # should not raise

    def test_migrate_noop_returns_true(self):
        adapter = _StorageAdapter()
        assert adapter.migrate(1, 2) is True


@pytest.mark.unit
class TestDisclaimerKeyConvention:
    """Ensure the disclaimer dismissal key constant is defined in storage.js."""

    STORAGE_JS_PATH = "src/static/js/storage.js"

    def test_disclaimer_key_constant_exists(self):
        import os
        assert os.path.exists(self.STORAGE_JS_PATH), (
            f"{self.STORAGE_JS_PATH} not found"
        )
        with open(self.STORAGE_JS_PATH, encoding="utf-8") as fh:
            content = fh.read()
        assert "STORAGE_KEY_DISCLAIMER_DISMISSED" in content
        assert "mushir_disclaimer_dismissed" in content

    def test_storage_adapter_class_exists(self):
        import os
        with open(self.STORAGE_JS_PATH, encoding="utf-8") as fh:
            content = fh.read()
        assert "function StorageAdapter" in content or (
            "class StorageAdapter" in content
        ), "StorageAdapter must be defined in storage.js"

    def test_mock_storage_class_exists(self):
        import os
        with open(self.STORAGE_JS_PATH, encoding="utf-8") as fh:
            content = fh.read()
        assert "function MockStorage" in content or (
            "class MockStorage" in content
        ), "MockStorage must be defined in storage.js"


@pytest.mark.unit
class TestConversationPersistence:
    """Verify conversation persistence methods (setObject, getObject,
    saveConversation, restoreConversation, clearConversation)."""

    CONVERSATION_KEY = "mushir_conversation"

    def test_set_object_get_object_round_trip(self):
        adapter = _StorageAdapter()
        data = {"role": "user", "content": "hello", "status": None}
        adapter.setObject("test_key", data)
        result = adapter.getObject("test_key")
        assert result == data

    def test_get_object_returns_none_for_missing_key(self):
        adapter = _StorageAdapter()
        assert adapter.getObject("nonexistent") is None

    def test_get_object_handles_corrupt_data(self):
        adapter = _StorageAdapter()
        adapter._storage.setItem("corrupt", "not-json{{{")
        result = adapter.getObject("corrupt")
        assert result is None

    def test_save_and_restore_conversation(self):
        adapter = _StorageAdapter()
        session_id = "session_test_123"
        msgs = [
            {"role": "user", "content": "Is this halal?", "timestamp": 1000},
            {"role": "assistant", "content": "Yes it is.", "timestamp": 2000,
             "status": "COMPLIANT", "citations": []},
        ]
        adapter.saveConversation(session_id, msgs)

        restored = adapter.restoreConversation(session_id)
        assert restored is not None
        assert restored["session_id"] == session_id
        assert len(restored["messages"]) == 2
        assert restored["messages"][0]["role"] == "user"
        assert restored["messages"][0]["content"] == "Is this halal?"
        assert restored["messages"][1]["role"] == "assistant"
        assert restored["messages"][1]["status"] == "COMPLIANT"
        assert "timestamp" in restored

    def test_restore_conversation_no_data(self):
        adapter = _StorageAdapter()
        result = adapter.restoreConversation("session_ghost")
        assert result is None

    def test_clear_conversation_removes_data(self):
        adapter = _StorageAdapter()
        adapter.saveConversation("sess_1", [{"role": "user", "content": "hi"}])
        assert adapter.getObject(self.CONVERSATION_KEY) is not None
        adapter.clearConversation()
        assert adapter.getObject(self.CONVERSATION_KEY) is None

    def test_clear_conversation_when_empty_does_not_raise(self):
        adapter = _StorageAdapter()
        adapter.clearConversation()  # should not raise

    def test_save_conversation_overwrites_previous(self):
        adapter = _StorageAdapter()
        adapter.saveConversation("sess_a", [{"role": "user", "content": "first"}])
        adapter.saveConversation("sess_b", [{"role": "user", "content": "second"}])
        restored = adapter.restoreConversation("sess_b")
        assert restored["messages"][0]["content"] == "second"
        # Same fixed key was overwritten
        assert len(restored["messages"]) == 1

    def test_quota_error_does_not_raise(self):
        """Simulate a storage that raises on setItem (quota exceeded)."""
        class QuotaLimitedStorage:
            def __init__(self):
                self._data = {}
            def getItem(self, key):
                return self._data.get(key)
            def setItem(self, key, value):
                if len(self._data) >= 1:
                    raise Exception("QuotaExceededError")
                self._data[key] = str(value)
            def removeItem(self, key):
                self._data.pop(key, None)
            def clear(self):
                self._data.clear()

        adapter = _StorageAdapter(storage=QuotaLimitedStorage())
        # First save should work
        adapter.saveConversation("s1", [{"role": "user", "content": "ok"}])
        # Second save should trigger quota error but not crash
        adapter.saveConversation("s1", [
            {"role": "user", "content": "this message pushes over quota"},
            {"role": "assistant", "content": "and another one..."},
        ])
        # App continues — no exception raised

    def test_js_storage_has_conversation_methods(self):
        """Structural guard: verify storage.js defines the methods used by app.js."""
        import os
        js_path = "src/static/js/storage.js"
        assert os.path.exists(js_path), f"{js_path} not found"
        with open(js_path, encoding="utf-8") as fh:
            content = fh.read()
        assert "StorageAdapter.prototype.setObject" in content
        assert "StorageAdapter.prototype.getObject" in content
        assert "StorageAdapter.prototype.saveConversation" in content
        assert "StorageAdapter.prototype.restoreConversation" in content
        assert "StorageAdapter.prototype.clearConversation" in content
        assert "CONVERSATION_KEY" in content
        assert "mushir_conversation" in content

    def test_js_restoreMessages_renders_badges(self):
        """Structural guard: verify renderer.js restoreMessages checks status for badges."""
        import os
        js_path = "src/static/js/renderer.js"
        assert os.path.exists(js_path), f"{js_path} not found"
        with open(js_path, encoding="utf-8") as fh:
            content = fh.read()
        assert "function restoreMessages" in content
        assert "VALID_COMPLIANCE" in content
        assert "renderBadge" in content
