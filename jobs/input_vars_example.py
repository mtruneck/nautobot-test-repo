from nautobot.apps.jobs import Job, StringVar, ObjectVar
from nautobot.apps import jobs
from nautobot.dcim.models import Device

class InputVarsExampleJob(Job):
    class Meta:
        name = "Input Vars Example Job - Simple Who"
        description = "Demonstrates a simple 'who' input variable."
        commit_default = False

    who = StringVar(
        description="Whom should we greet?",
        default="world"
    )

    def run(self, *, who):
        greeting = f"Hello, {who}!"
        self.logger.info(greeting)
        return greeting

jobs.register_jobs(InputVarsExampleJob)
