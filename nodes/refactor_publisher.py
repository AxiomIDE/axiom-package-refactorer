import os
import re
import subprocess
import tempfile
import shutil

import httpx

from gen.axiom_official_axiom_agent_messages_messages_pb2 import PackageBuildContext, AgentProgress
from gen.axiom_logger import AxiomLogger, AxiomSecrets


def _bump_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) == 3:
        try:
            parts[2] = str(int(parts[2]) + 1)
        except ValueError:
            pass
    return ".".join(parts)


def _to_snake(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def refactor_publisher(log: AxiomLogger, secrets: AxiomSecrets, input: PackageBuildContext) -> AgentProgress:
    """Bump version, commit refactored code to GitHub, and republish."""

    github_token, _ = secrets.get("GITHUB_TOKEN")
    axiom_api_key, _ = secrets.get("AXIOM_API_KEY")
    new_version = _bump_version(input.version or "0.1.0")
    pkg_short = input.name.split("/")[-1] if "/" in input.name else input.name
    org = "AxiomIDE"
    repo_url = f"https://github.com/{org}/{pkg_short}"

    tmpdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmpdir, "nodes"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "messages"), exist_ok=True)

        if input.axiom_yaml:
            updated_yaml = input.axiom_yaml.replace(
                f"version: {input.version}",
                f"version: {new_version}"
            )
            with open(os.path.join(tmpdir, "axiom.yaml"), "w") as f:
                f.write(updated_yaml)

        if input.proto_content:
            with open(os.path.join(tmpdir, "messages", "messages.proto"), "w") as f:
                f.write(input.proto_content)

        reqs = input.requirements_txt or "grpcio>=1.60.0\ngrpcio-tools>=1.60.0\nprotobuf>=4.25.0\n"
        with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
            f.write(reqs)

        for node in input.nodes:
            if node.source_code:
                with open(os.path.join(tmpdir, "nodes", f"{_to_snake(node.name)}.py"), "w") as f:
                    f.write(node.source_code)

        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "agent@axiom.local"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Axiom Agent"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"refactor: bump to {new_version}"], cwd=tmpdir, capture_output=True)

        remote = f"https://x-access-token:{github_token}@github.com/{org}/{pkg_short}.git"
        push_result = subprocess.run(
            ["git", "push", remote, "HEAD:main", "--force"],
            cwd=tmpdir, capture_output=True, text=True
        )

        if push_result.returncode != 0:
            return AgentProgress(
                stage="error",
                message=f"git push failed: {push_result.stderr[:300]}",
                complete=True,
                success=False,
            )

        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmpdir, capture_output=True, text=True).stdout.strip()

        registry_url = os.environ.get("REGISTRY_URL", "http://axiom-registry.default.svc.cluster.local:8082")
        resp = httpx.post(
            f"{registry_url}/packages/publish",
            headers={"Authorization": f"Bearer {axiom_api_key}"},
            json={"repo_url": repo_url, "commit_hash": sha},
            timeout=300.0,
        )

        if resp.status_code == 200:
            return AgentProgress(
                stage="complete",
                message=f"Package {input.name} refactored and republished as v{new_version}.",
                complete=True,
                success=True,
                package_name=input.name,
            )
        else:
            return AgentProgress(
                stage="error",
                message=f"Registry returned {resp.status_code}: {resp.text[:300]}",
                complete=True,
                success=False,
            )
    except Exception as e:
        log.error(f"RefactorPublisher failed: {e}")
        return AgentProgress(stage="error", message=str(e), complete=True, success=False)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
