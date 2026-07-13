from dataclasses import dataclass
from pydantic import BaseModel


class TaskRequest(BaseModel):
    task_id: str
    command: str


@dataclass
class TaskInput:
    task_id: str
    command: str


@dataclass
class AgentResult:
    output: str
    artifacts: list[str]


@dataclass
class WorkflowResult:
    message: str
    artifacts: list[str]
