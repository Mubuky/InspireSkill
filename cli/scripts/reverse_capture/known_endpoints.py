"""Closed or explicitly characterized Browser API endpoints for diffing captures.

Update this list only when an endpoint is added to `references/dev/browser-api.md`
or wrapped by the CLI. The diffing tool (`analyze.py`) compares freshly
captured traffic against this set to surface newly appeared or newly dead
endpoints.

Observed-only paths stay out of this file until their request body, response
shape, Referer, and destructive semantics are verified. Restricted endpoints
may be listed only when their regular-user failure mode is also verified and
documented.
"""

from __future__ import annotations

import re

# (METHOD, path_template) — path templates use `{id}` for any variable segment.
KNOWN: set[tuple[str, str]] = {
    # --- User / Permissions ---
    ("GET", "/api/v1/user/detail"),
    ("GET", "/api/v1/user/{id}"),
    ("GET", "/api/v1/user/routes/{id}"),
    ("GET", "/api/v1/user/permissions/{id}"),
    ("GET", "/api/v1/user/my-api-key/list"),
    ("GET", "/api/v1/user/quota"),
    ("POST", "/api/v1/user/list"),
    ("POST", "/api/v1/ssh/list"),
    ("POST", "/api/v1/ssh/create"),
    ("DELETE", "/api/v1/ssh/{id}"),

    # --- Project ---
    ("POST", "/api/v1/project/list"),
    ("POST", "/api/v1/project/list_v2"),
    ("POST", "/api/v1/project/list_for_page"),
    ("GET", "/api/v1/project/{id}"),
    ("GET", "/api/v1/project/owners"),

    # --- Notebook ---
    ("POST", "/api/v1/notebook/create"),
    ("POST", "/api/v1/notebook/users"),
    ("POST", "/api/v1/notebook/operate"),
    ("DELETE", "/api/v1/notebook/{id}"),
    ("POST", "/api/v1/notebook/list"),
    ("GET", "/api/v1/notebook/{id}"),
    ("POST", "/api/v1/notebook/events"),
    ("POST", "/api/v1/lifecycle/list"),
    ("POST", "/api/v1/run_index/list"),
    ("POST", "/api/v1/resource_prices/logic_compute_groups/"),
    ("GET", "/api/v1/notebook/schedule/{id}"),
    ("GET", "/api/v1/notebook/schedule"),

    # --- Image ---
    ("POST", "/api/v1/image/list"),
    ("GET", "/api/v1/image/{id}"),
    ("POST", "/api/v1/image/create"),
    ("DELETE", "/api/v1/image/{id}"),
    ("POST", "/api/v1/mirror/save"),
    ("POST", "/api/v1/image/update"),

    # --- Train Job ---
    ("POST", "/api/v1/train_job/list"),
    ("POST", "/api/v1/train_job/delete"),
    ("POST", "/api/v1/train_job/detail"),
    ("POST", "/api/v1/train_job/users"),
    ("POST", "/api/v1/train_job/workdir"),
    ("POST", "/api/v1/train_job/job_event_list"),
    ("POST", "/api/v1/train_job/instance_list"),
    ("POST", "/api/v1/train_job/events/list"),
    ("POST", "/api/v1/logs/train"),

    # --- HPC Jobs ---
    ("POST", "/api/v1/hpc_jobs/list"),
    ("GET", "/api/v1/hpc_jobs/{id}"),
    ("DELETE", "/api/v1/hpc_jobs/{id}"),
    ("POST", "/api/v1/hpc_jobs/events/list"),
    ("POST", "/api/v1/hpc_jobs/instances/list"),
    ("POST", "/api/v1/logs/hpc"),

    # --- Ray Jobs ---
    ("POST", "/api/v1/ray_job/list"),
    ("POST", "/api/v1/ray_job/users"),
    ("POST", "/api/v1/ray_job/detail"),
    ("POST", "/api/v1/ray_job/stop"),
    ("POST", "/api/v1/ray_job/delete"),
    ("POST", "/api/v1/ray_job/create"),
    ("POST", "/api/v1/ray_job/events/list"),
    ("POST", "/api/v1/ray_job/instances/list"),
    ("POST", "/api/v1/ray_job/scaling_histories/list"),

    # --- Metrics ---
    ("POST", "/api/v1/cluster_metric/resource_metric_by_time"),

    # --- Resources / Compute groups ---
    ("POST", "/api/v1/workspace/list"),
    ("POST", "/api/v1/logic_compute_groups/list"),
    ("GET", "/api/v1/logic_compute_groups/{id}"),
    ("POST", "/api/v1/compute_groups/list"),
    ("POST", "/api/v1/compute_resources/cluster_basic_info"),
    ("GET", "/api/v1/compute_resources/cluster_basic_info"),
    ("POST", "/api/v1/cluster_basic_info"),
    ("GET", "/api/v1/compute_resources/logic_compute_groups/{id}"),
    ("POST", "/api/v1/compute_resources/list_node_dimension"),
    ("POST", "/api/v1/compute_resources/node_dimension/list"),
    ("GET", "/api/v1/compute_resources/node_specs/logic_compute_groups/{id}"),
    ("POST", "/api/v1/cluster_nodes/list"),
    ("GET", "/api/v1/cluster_nodes/workspace/{id}"),

    # --- Model (registry) ---
    ("POST", "/api/v1/model/list"),
    ("POST", "/api/v1/model/detail"),
    ("GET", "/api/v1/model/{id}"),
    ("GET", "/api/v1/model/{id}/versions"),
    ("POST", "/api/v1/model/create"),
    ("POST", "/api/v1/model/inference_serving/pending"),
    ("POST", "/api/v1/model/inference_servings"),
    ("GET", "/api/v1/model/{id}/version/{id}/publish/prefill"),
    ("GET", "/api/v1/model/{id}/version/{id}/publish/status"),
    ("POST", "/api/v1/model/users"),
    ("POST", "/api/v1/model/{id}/versions"),
    ("PUT", "/api/v1/model/edit/{id}"),
    ("POST", "/api/v1/model/delete"),
    ("PUT", "/api/v1/model/tryAgain/{id}"),
    ("POST", "/api/v1/model/{id}/version/{id}/publish"),

    # --- Model plaza ---
    ("POST", "/api/v1/model_plaza/list"),
    ("GET", "/api/v1/model_plaza/filters"),
    ("GET", "/api/v1/model_plaza/detail/{id}"),
    ("GET", "/api/v1/model_plaza/related_workspace/{id}"),
    ("GET", "/api/v1/model_plaza/deploy_serving_config/{id}"),

    # --- Inference servings ---
    ("POST", "/api/v1/inference_servings/list"),
    ("POST", "/api/v1/inference_servings/user_project/list"),
    ("GET", "/api/v1/inference_servings/configs/workspace/{id}"),
    ("GET", "/api/v1/inference_servings/{id}"),
    ("GET", "/api/v1/inference_servings/{id}/versions"),
    ("POST", "/api/v1/inference_servings/instances/list"),
    ("POST", "/api/v1/inference_servings/events/list"),
    ("POST", "/api/v1/logs/inference_serving"),
    ("POST", "/api/v1/inference_servings/scale_history/list"),
    ("GET", "/api/v1/inference_servings/{id}/terms"),
    ("POST", "/api/v1/inference_servings/create"),
    ("DELETE", "/api/v1/inference_servings/{id}"),
    ("POST", "/api/v2/inference_serving"),
}

# Endpoints that used to exist but were retired by the platform. Listed here
# so that `analyze.py` can call them out if a new capture unexpectedly
# resurrects one (signal for a rollback on the platform side).
STALE_SINCE_2026_04: set[tuple[str, str]] = {
    ("GET", "/api/v1/notebook/{id}/events"),
    ("GET", "/api/v1/notebook/event/{id}"),
    ("POST", "/api/v1/notebook/compute_groups"),
}


_PREFIXED_ID = re.compile(
    r"/(?:ws|job|hpc-job|sv|project|lcg|cg|image|img|nb|notebook|mdl|model|mp|spec|tk|quota|ssh|usr|user|tag|team|org)"
    r"-[0-9a-zA-Z_-]{4,}(?=/|$|\?)"
)
_UUID = re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$|\?)")
_NUM = re.compile(r"/\d{4,}(?=/|$|\?)")
_HEX = re.compile(r"/[0-9a-f]{16,}(?=/|$|\?)")
_VERSION_NUM = re.compile(r"(?<=/version)/\d+(?=/|$|\?)")


def normalize_path(path: str) -> str:
    """Collapse id-bearing path segments to `{id}` so paths group cleanly."""
    p = path.split("?")[0]
    p = _PREFIXED_ID.sub("/{id}", p)
    p = _UUID.sub("/{id}", p)
    p = _VERSION_NUM.sub("/{id}", p)
    p = _NUM.sub("/{id}", p)
    p = _HEX.sub("/{id}", p)
    return p


def is_known(method: str, path: str) -> bool:
    return (method.upper(), normalize_path(path)) in KNOWN


if __name__ == "__main__":
    tests = [
        ("GET", "/api/v1/user/detail", True),
        ("GET", "/api/v1/user/routes/ws-1177d2a5-aef0-40d3-8777-fed9af13affc", True),
        ("DELETE", "/api/v1/ssh/ssh-0e7e2c07-2d16-4148-bc07-6803371de7e8", True),
        ("GET", "/api/v1/notebook/facfdc82-b52d-414f-8a9f-cc918c26acbd", True),
        ("POST", "/api/v1/notebook/events", True),
        ("GET", "/api/v1/notebook/event/facfdc82-b52d-414f-8a9f-cc918c26acbd", False),
        ("POST", "/api/v1/completely_new_endpoint", False),
    ]
    for method, path, want in tests:
        got = is_known(method, path)
        mark = "✓" if got == want else "✗"
        print(f"{mark} {method:6s} {path:70s} → known={got} (want={want})")
