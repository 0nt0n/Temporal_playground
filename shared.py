from dataclasses import dataclass


@dataclass
class TaskInput:
    task_id: str
    command: str
