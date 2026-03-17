import json
import os
import re

import anthropic
import httpx

from gen.axiom_official_axiom_agent_messages_messages_pb2 import AgentRequest, PackageSpec, NodeSpec
from gen.axiom_logger import AxiomLogger, AxiomSecrets


SYSTEM_PROMPT = """You are an expert at identifying Axiom packages from user descriptions.
Extract the package name and refactoring goal from the user's request."""


def refactor_intent_classifier(log: AxiomLogger, secrets: AxiomSecrets, input: AgentRequest) -> PackageSpec:
    """Parse refactoring goal and look up the target package in the registry."""
    api_key = secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Extract from: "{input.goal}"

Return JSON: {{"package_name": "axiom-official/<name>", "refactor_goal": "<what to change>"}}"""
        }]
    )

    content = message.content[0].text
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.index("```") + 3
        end = content.index("```", start)
        content = content[start:end].strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {"package_name": "axiom-official/unknown", "refactor_goal": input.goal}

    # Fetch the package from the registry to get node list.
    registry_url = os.environ.get("REGISTRY_URL", "http://axiom-registry:8082")
    axiom_api_key = os.environ.get("AXIOM_API_KEY", "")

    spec = PackageSpec(
        name=data.get("package_name", "axiom-official/unknown"),
        fix_instructions=data.get("refactor_goal", input.goal),
    )

    try:
        pkg_short = spec.name.split("/")[-1]
        resp = httpx.get(
            f"{registry_url}/packages/{pkg_short}",
            headers={"Authorization": f"Bearer {axiom_api_key}"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            pkg_data = resp.json()
            spec.version = pkg_data.get("version", "0.1.0")
            spec.language = pkg_data.get("language", "python")
            spec.proto_content = pkg_data.get("proto_content", "")
            spec.axiom_yaml = pkg_data.get("axiom_yaml", "")
            for node in pkg_data.get("nodes", []):
                spec.nodes.append(NodeSpec(
                    name=node.get("name", ""),
                    description=node.get("description", ""),
                    input_message=node.get("input_message", ""),
                    output_message=node.get("output_message", ""),
                    node_type=node.get("node_type", "unary"),
                ))
    except Exception as e:
        log.warning(f"Failed to fetch package from registry: {e}")

    return spec
