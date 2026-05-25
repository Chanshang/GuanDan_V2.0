import unittest

from services import runtime_store
from services import runtime_view_refresh_service
from services import runtime_views
from tests.fakes import FakeRedis


class RuntimeViewRefreshServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.original_store_require_redis = runtime_store.require_redis
        self.original_service_require_redis = runtime_view_refresh_service.require_redis
        self.original_rebuild_dashboard = runtime_views.rebuild_dashboard_view
        self.original_rebuild_matches = runtime_views.rebuild_admin_matches_view
        self.original_rebuild_overview = runtime_views.rebuild_admin_overview_view
        runtime_store.require_redis = lambda: self.redis
        runtime_view_refresh_service.require_redis = lambda: self.redis
        runtime_store.initialize_empty_state()

    def tearDown(self):
        runtime_store.require_redis = self.original_store_require_redis
        runtime_view_refresh_service.require_redis = self.original_service_require_redis
        runtime_views.rebuild_dashboard_view = self.original_rebuild_dashboard
        runtime_views.rebuild_admin_matches_view = self.original_rebuild_matches
        runtime_views.rebuild_admin_overview_view = self.original_rebuild_overview

    def test_refresh_dirty_views_once_skips_when_no_dirty_turns(self):
        calls = []
        runtime_views.rebuild_dashboard_view = lambda turn: calls.append(("dashboard", turn))

        result = runtime_view_refresh_service.refresh_dirty_views_once()

        self.assertEqual({"ok": True, "dirty_count": 0}, result)
        self.assertEqual([], calls)

    def test_refresh_dirty_views_once_rebuilds_dirty_turns_and_admin_views(self):
        calls = []
        runtime_store.mark_dashboard_dirty(2)
        runtime_views.rebuild_dashboard_view = lambda turn: calls.append(("dashboard", turn))
        runtime_views.rebuild_admin_matches_view = lambda: calls.append("matches")
        runtime_views.rebuild_admin_overview_view = lambda: calls.append("overview")

        result = runtime_view_refresh_service.refresh_dirty_views_once()

        self.assertTrue(result["ok"])
        self.assertEqual([2, 3], result["rebuilt_dashboard_turns"])
        self.assertEqual(
            [("dashboard", 2), ("dashboard", 3), "matches", "overview"],
            calls,
        )
        self.assertEqual(set(), self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY))

    def test_refresh_dirty_views_once_keeps_dirty_turns_when_rebuild_fails(self):
        runtime_store.mark_dashboard_dirty(1)

        def fail_rebuild(turn):
            raise RuntimeError("refresh failed")

        runtime_views.rebuild_dashboard_view = fail_rebuild

        result = runtime_view_refresh_service.refresh_dirty_views_once()

        self.assertFalse(result["ok"])
        self.assertEqual(
            {"1", "2", "3"},
            self.redis.smembers(runtime_store.DIRTY_DASHBOARD_KEY),
        )


if __name__ == "__main__":
    unittest.main()
