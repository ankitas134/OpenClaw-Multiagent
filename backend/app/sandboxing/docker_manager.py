import os
import docker
from typing import Dict, Any
from app.core.config import settings

from app.core.sandbox_config import SERVER_SANDBOX_SETTINGS

def get_docker_client():
    return docker.from_env()

def prepare_agent_workspace(agent_id: str, team_name: str, team_context: str, agent_name: str, task_context: str) -> str:
    workspace_dir = os.path.join(settings.WORKSPACES_ROOT, str(agent_id))
    os.makedirs(workspace_dir, exist_ok=True)
    os.makedirs(os.path.join(workspace_dir, "docs"), exist_ok=True)

    memory_content = f"""# Agent Workspace Memory & Guidelines

## Agent Profile
- **Name**: {agent_name}
- **Agent ID**: {agent_id}
- **Team**: {team_name}

## Standing Team Context & Guidelines
{team_context if team_context else "No standing team instructions provided."}

## Specific Run Task Objective
{task_context if task_context else "No active task objective set."}

## Workspace Execution Rules
1. All generated output must remain within `/workspace`.
2. Document references are synchronized under `/workspace/docs/`.
3. Operate strictly according to team security standards.
"""
    memory_file = os.path.join(workspace_dir, "MEMORY.md")
    with open(memory_file, "w", encoding="utf-8") as f:
        f.write(memory_content)

    return workspace_dir

def spinup_agent_container(
    agent_id: str,
    team_name: str,
    team_context: str,
    agent_name: str,
    task_context: str,
    config: Dict[str, Any] = None
) -> str:
    try:
        client = get_docker_client()
        client.ping()
    except Exception as ex:
        if settings.ALLOW_UNSANDBOXED_DEV_MODE:
            print(f"[Docker] Docker daemon unavailable ({ex}). ALLOW_UNSANDBOXED_DEV_MODE is enabled — using Local Sandboxed Workspace.")
            workspace_dir = prepare_agent_workspace(agent_id, team_name, team_context, agent_name, task_context)
            return f"local-dev-agent-{agent_id}"
        print(f"[Docker] Docker daemon unavailable ({ex}). Sandboxing failed.")
        raise RuntimeError(f"Docker daemon unavailable and unsandboxed mode is disabled: {ex}")

    container_name = f"openclaw-agent-{agent_id}"

    # Clean up existing container if any
    try:
        existing = client.containers.get(container_name)
        existing.stop()
        existing.remove()
    except Exception:
        pass

    workspace_dir = prepare_agent_workspace(agent_id, team_name, team_context, agent_name, task_context)

    # Sandbox Configuration Parameters from server-controlled defaults
    sandbox = SERVER_SANDBOX_SETTINGS
    docker_image = sandbox.sandboxDockerImage
    read_only_root = sandbox.sandboxDockerReadOnlyRoot
    cap_drop = sandbox.sandboxDockerCapDrop
    network_mode = sandbox.sandboxDockerNetwork
    mem_limit = sandbox.memoryLimit
    nano_cpus = sandbox.cpuLimit

    # Ensure docker image is available
    try:
        client.images.get(docker_image)
    except Exception:
        try:
            print(f"[Docker] Pulling sandbox image {docker_image}...")
            client.images.pull(docker_image)
        except Exception as pull_ex:
            print(f"[Docker] Warning: Failed to pull sandbox image {docker_image}: {pull_ex}")

    try:
        # Launch isolated sandbox container
        container = client.containers.run(
            image=docker_image,
            name=container_name,
            command="tail -f /dev/null",
            detach=True,
            read_only=read_only_root,
            cap_drop=cap_drop,
            network_mode=network_mode,
            mem_limit=mem_limit,
            nano_cpus=nano_cpus,
            volumes={
                workspace_dir: {"bind": "/workspace", "mode": "rw"},
                "/tmp": {"bind": "/tmp", "mode": "rw"}
            },
            working_dir="/workspace"
        )
        print(f"[Docker] Agent container {container_name} created successfully (ID: {container.short_id}).")
        return container.id
    except Exception as ex:
        if settings.ALLOW_UNSANDBOXED_DEV_MODE:
            print(f"[Docker] Container launch failed ({ex}). ALLOW_UNSANDBOXED_DEV_MODE is enabled — using Local Sandboxed Workspace.")
            return f"local-dev-agent-{agent_id}"
        print(f"[Docker] Container launch failed ({ex}). Sandboxing failed.")
        raise RuntimeError(f"Container launch failed: {ex}")

def stop_agent_container(container_id: str):
    if not container_id or container_id.startswith("local-agent-") or container_id.startswith("local-dev-agent-"):
        return
    try:
        client = get_docker_client()
        container = client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove()
        print(f"[Docker] Container {container_id[:12]} stopped and removed.")
    except Exception as e:
        print(f"[Docker] Warning stopping container {container_id}: {e}")

def exec_container_command(container_id: str, cmd: str) -> str:
    if not container_id or container_id.startswith("local-agent-") or container_id.startswith("local-dev-agent-"):
        return "Executed in Local Workspace."
    try:
        client = get_docker_client()
        container = client.containers.get(container_id)
        res = container.exec_run(cmd, workdir="/workspace")
        return res.output.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[Docker] Failed to execute container command: {e}")
        return f"Local Execution Fallback: {e}"
