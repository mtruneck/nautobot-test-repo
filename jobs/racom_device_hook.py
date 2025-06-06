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
        # On device create/update, fetch config and compare names
        if action in ("create", "update") and changed_object is not None:
            nautobot_name = changed_object.name
            domain = changed_object.custom_field_data.get("Domain")
            if not domain:
                self.logger.warning(f"Device {changed_object} has no Domain custom field; skipping config check.")
                return
            # --- RACOM login ---
            login_url = f"https://{domain}:443/cgi-bin/login.cgi"
            login_payload = {"username": "admin", "password": "admin", "language_code": "en"}
            try:
                login_resp = requests.post(login_url, json=login_payload, headers={"Content-Type": "application/json"}, verify=False, timeout=10)
                if not login_resp or login_resp.status_code != 200:
                    self.logger.error(f"Could not login to device at {domain}")
                    raise Exception(f"Could not login to device at {domain}")
                token = login_resp.json().get("token")
                if not token:
                    self.logger.error(f"No token returned from device at {domain}")
                    raise Exception(f"No token returned from device at {domain}")
            except Exception as e:
                self.logger.error(f"Exception during login to {domain}: {e}")
                raise
            # --- Get config ---
            config_url = f"https://{domain}:443/cgi-bin/rpc.cgi"
            config_payload = {"method": "settings_get"}
            config_headers = {"Content-Type": "application/json", "apikey": token}
            try:
                config_resp = requests.post(config_url, json=config_payload, headers=config_headers, verify=False, timeout=10)
                if not config_resp or config_resp.status_code != 200:
                    self.logger.error(f"Could not retrieve config from device at {domain}")
                    raise Exception(f"Could not retrieve config from device at {domain}")
                config_json = config_resp.json()
                config_name = config_json["result"]["config_data"]["main"]["RR_StationName"]
            except Exception as e:
                self.logger.error(f"Could not extract station name from config: {e}")
                raise Exception(f"Could not extract station name from config: {e}")
            # --- Compare names ---
            if nautobot_name != config_name:
                msg = f"Device name mismatch: Nautobot='{nautobot_name}' vs DeviceConfig='{config_name}'"
                self.logger.error(msg)
                raise Exception(msg)
            self.logger.info(f"Device name matches: '{nautobot_name}'")
        elif action == "delete":
            self.logger.info(f"Device {changed_object} was deleted. No ping attempted.")

jobs.register_jobs(RacomDeviceChangeHook)
