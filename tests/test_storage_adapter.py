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
