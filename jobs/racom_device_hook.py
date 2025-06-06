import requests
from nautobot.apps.jobs import JobHookReceiver
from nautobot.apps import jobs
from nautobot.dcim.models import Device

class RacomDeviceChangeHook(JobHookReceiver):
    class Meta:
        name = "Racom Device Change Hook"
        description = "Triggered on Device create/update/delete events."

    def receive_job_hook(self, change, action, changed_object):
        """
        This method is called when a Device is created, updated, or deleted.
        Args:
            change (ObjectChange): the Nautobot ObjectChange instance
            action (str): "create", "update", or "delete"
            changed_object (Device or None): the Device instance (or None if deleted)
        """
        self.logger.info(
            f"Device change event: action={action}, object={changed_object}, change={change}"
        )
        # Example: if device is created or updated, ping it
        if action in ("create", "update") and changed_object is not None:
            domain = changed_object.custom_field_data.get("Domain")
            if not domain:
                self.logger.warning(f"Device {changed_object} has no Domain custom field; skipping ping.")
                return
            url = f"https://{domain}:443/cgi-bin/rpc.cgi"
            payload = {"method": "device_ping"}
            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, verify=False, timeout=10)
                if resp.status_code == 200:
                    self.logger.info(f"{changed_object} ({domain}): API reachable (HTTP 200) after {action}.")
                else:
                    self.logger.error(f"{changed_object} ({domain}): API NOT reachable after {action}. Status: {resp.status_code}. Response: {resp.text[:200]}...")
            except Exception as e:
                self.logger.error(f"{changed_object} ({domain}): Exception during ping after {action}: {e}")
        elif action == "delete":
            self.logger.info(f"Device {changed_object} was deleted. No ping attempted.")

jobs.register_jobs(RacomDeviceChangeHook)
