from nautobot.apps.jobs import Job, StringVar, ObjectVar
from nautobot.dcim.models import Device

class InputVarsExampleJob(Job):
    class Meta:
        name = "Input Vars Example Job"
        description = "Demonstrates input variables in Nautobot v2.4+ jobs."
        commit_default = False

    class InputVariables:
        name = StringVar(
            description="Your name",
            default="World",
            required=False
        )
        device = ObjectVar(
            model=Device,
            required=False,
            description="Device to operate on (optional)"
        )

    def run(self, data=None, commit=None):
        greeting = f"Hello, {data.get('name', 'World')}!"
        self.logger.info(greeting)
        if data.get("device"):
            self.logger.info(f"Device selected: {data['device']}")
            return f"{greeting} Device selected: {data['device']}"
        return greeting

job = InputVarsExampleJob
