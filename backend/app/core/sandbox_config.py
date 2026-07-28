from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any

class SandboxSettings(BaseModel):
    sandboxMode: str = "all"
    sandboxBackend: str = "docker"
    sandboxDockerNetwork: str = "none"
    sandboxDockerReadOnlyRoot: bool = True
    sandboxDockerCapDrop: List[str] = ["ALL"]
    sandboxDockerImage: str = "alpine:latest"
    memoryLimit: int = 268435456  # 256MB
    cpuLimit: int = 500000000     # 0.5 CPU

SERVER_SANDBOX_SETTINGS = SandboxSettings()

class AgentCustomConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    displayName: str | None = None
    notes: str | None = None
