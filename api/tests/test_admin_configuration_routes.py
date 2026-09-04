from app.main import create_app


def test_admin_configuration_routes_are_registered() -> None:
    schema = create_app().openapi()

    expected_paths = {
        "/api/v1/admin/source-credentials",
        "/api/v1/admin/source-credentials/{credential_id}",
        "/api/v1/admin/sources",
        "/api/v1/admin/sources/{source_id}",
        "/api/v1/admin/llm-providers",
        "/api/v1/admin/llm-providers/{provider_id}",
        "/api/v1/admin/llm-providers/{provider_id}/set-default",
        "/api/v1/admin/jobs",
        "/api/v1/admin/jobs/{job_run_id}",
        "/api/v1/admin/jobs/{job_run_id}/retry",
        "/api/v1/admin/jobs/collect",
        "/api/v1/admin/jobs/daily-pipeline",
        "/api/v1/admin/jobs/generate-digest",
        "/api/v1/admin/jobs/normalize",
        "/api/v1/admin/jobs/rank",
        "/api/v1/admin/jobs/dedupe",
        "/api/v1/admin/jobs/summarize",
        "/api/v1/admin/scheduler/configs",
        "/api/v1/admin/scheduler/configs/{config_id}",
        "/api/v1/digests/today",
        "/api/v1/digests/{digest_date}",
        "/api/v1/library/items",
        "/api/v1/library/items/{item_id}",
        "/api/v1/following/preferences",
        "/api/v1/following/items",
        "/api/v1/following/saved-searches",
        "/api/v1/following/feedback",
    }

    assert expected_paths.issubset(schema["paths"].keys())
