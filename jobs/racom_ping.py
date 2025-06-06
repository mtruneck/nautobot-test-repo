import requests
from nautobot.extras.jobs import Job
from nautobot.dcim.models import Device

class RacomDevicePing(Job):
    class Meta:
        name = "Racom Device API Ping"
        description = "Ping all RACOM devices in Nautobot using device_ping API call."
        has_sensitive_variables = False

    def run(self, data, commit):
        # Get all devices with a Domain custom field
        devices = Device.objects.all()
        if not devices.exists():
            self.log_info("No devices found in Nautobot.")
            return
        for device in devices:
            domain = device.custom_field_data.get("Domain")
            if not domain:
                self.log_warning(f"Device {device.name} has no Domain custom field; skipping.")
                continue
            url = f"https://{domain}:443/cgi-bin/rpc.cgi"
            payload = {"method": "device_ping"}
            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, verify=False, timeout=10)
                if resp.status_code == 200:
                    self.log_success(f"{device.name} ({domain}): API reachable.")
                    self.log_debug(f"Response: {resp.json()}")
                else:
                    self.log_failure(f"{device.name} ({domain}): API NOT reachable. Status: {resp.status_code}")
                    self.log_debug(f"Response: {resp.text}")
            except Exception as e:
                self.log_failure(f"{device.name} ({domain}): Exception: {e}")

job = RacomDevicePing
