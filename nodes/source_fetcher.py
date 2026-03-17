import logging
import os

import httpx

from gen.axiom_official_axiom_agent_messages_messages_pb2 import PackageSpec

logger = logging.getLogger(__name__)


def handle(spec: PackageSpec, context) -> PackageSpec:
    """Fetch source code for each node from the registry."""

    registry_url = os.environ.get("REGISTRY_URL", "http://axiom-registry:8082")
    axiom_api_key = os.environ.get("AXIOM_API_KEY", "")
    headers = {"Authorization": f"Bearer {axiom_api_key}"}

    pkg_short = spec.name.split("/")[-1] if "/" in spec.name else spec.name

    for node in spec.nodes:
        if node.source_code:
            continue
        try:
            resp = httpx.get(
                f"{registry_url}/packages/{pkg_short}/nodes/{node.name}/source",
                headers=headers,
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                node.source_code = data.get("source_code", "")
            else:
                logger.warning(f"Failed to fetch source for {node.name}: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Error fetching source for {node.name}: {e}")

    return spec
