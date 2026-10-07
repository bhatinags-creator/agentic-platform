from dataclasses import dataclass
from uuid import uuid4


@dataclass
class HumanTask:
    human_task_id: str
    run_id: str
    status: str
    prompt: str

class HumanTaskService:
    def create_approval_task(self, run_id: str, prompt: str) -> HumanTask:
        return HumanTask(str(uuid4()), run_id, "pending", prompt)
