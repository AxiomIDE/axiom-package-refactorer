import logging
import os

import anthropic

from gen.axiom_official_axiom_agent_messages_messages_pb2 import PackageSpec

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Python developer applying targeted refactoring changes to Axiom node implementations.
Apply only the requested changes while preserving the existing structure and handle() function signature."""


def handle(spec: PackageSpec, context) -> PackageSpec:
    """Apply refactoring changes to each node's source code."""

    api_key = context.secrets.get("ANTHROPIC_API_KEY") if hasattr(context, 'secrets') else os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)

    refactor_goal = spec.fix_instructions or "improve code quality"

    for node in spec.nodes:
        if not node.source_code:
            continue

        logger.info(f"Refactoring node {node.name}")
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"""Apply this refactoring to the node:

Refactoring goal: {refactor_goal}

Current source code:
```python
{node.source_code}
```

Return ONLY the updated Python source code, no explanation."""
            }]
        )

        content = message.content[0].text
        if "```python" in content:
            start = content.index("```python") + 9
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()

        node.source_code = content

    spec.fix_instructions = ""
    return spec
