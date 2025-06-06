import requests
import requests
from nautobot.apps.jobs import Job
from nautobot.dcim.models import Device

class RacomDevicePing(Job):
    """
    Ping all RACOM devices in Nautobot using device_ping API call.
    """
    class Meta:
        name = "Racom Device API Ping"
        description = "Ping all RACOM devices in Nautobot using device_ping API call."
        commit_default = False

    class InputVariables:
        pass  # No input variables needed for this job

    def run(self, data=None, commit=None):
        devices = Device.objects.all()
        if not devices.exists():
            self.logger.info("No devices found in Nautobot.")
            return "No devices found in Nautobot."
        success_count = 0
        fail_count = 0
        for device in devices:
            domain = device.custom_field_data.get("Domain")
            if not domain:
                self.logger.warning(f"Device {device.name} has no Domain custom field; skipping.")
                continue
            url = f"https://{domain}:443/cgi-bin/rpc.cgi"
            payload = {"method": "device_ping"}
            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, verify=False, timeout=10)
                if resp.status_code == 200:
                    self.logger.info(f"{device.name} ({domain}): API reachable.")
                    try:
                        json_data = resp.json()
                        self.logger.debug(f"Response: {json_data}")
                        success_count += 1
                    except Exception as json_exc:
                        self.logger.error(f"{device.name} ({domain}): Response is not valid JSON: {json_exc}")
                        self.logger.debug(f"Raw response: {resp.text}")
                        fail_count += 1
                else:
                    self.logger.error(f"{device.name} ({domain}): API NOT reachable. Status: {resp.status_code}")
                    self.logger.debug(f"Response: {resp.text}")
                    fail_count += 1
            except Exception as e:
                self.logger.error(f"{device.name} ({domain}): Exception: {e}")
                fail_count += 1
        summary = f"Pinged {success_count + fail_count} devices: {success_count} successful, {fail_count} failed."
        self.logger.info(summary)
        return summary

job = RacomDevicePing
