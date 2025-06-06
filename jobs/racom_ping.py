import requests
import requests
from nautobot.apps.jobs import Job, ObjectVar
from nautobot.apps import jobs
from nautobot.dcim.models import Device, DeviceType

class RacomDevicePing(Job):
    """
    Ping all RACOM devices in Nautobot using device_ping API call.
    """
    class Meta:
        name = "Racom Device API Ping"
        description = "Ping all RACOM devices in Nautobot using device_ping API call."
        commit_default = False

    device = ObjectVar(
        model=Device,
        required=False,
        description="Specific device to ping (optional)."
    )
    device_type = ObjectVar(
        model=DeviceType,
        required=False,
        description="Ping all devices of this Device Type (optional)."
    )

    def run(self, *, device=None, device_type=None, commit=None):
        # Determine which filter to use
        if device:
            devices = Device.objects.filter(pk=device.pk)
            self.logger.info(f"Pinging single device: {device}")
        elif device_type:
            devices = Device.objects.filter(device_type=device_type)
            self.logger.info(f"Pinging all devices of type: {device_type}")
        else:
            devices = Device.objects.all()
            self.logger.info("Pinging all devices.")

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
                    try:
                        json_data = resp.json()
                        self.logger.debug(f"Response: {json_data}")
                        # Accept as success if status==200 and msg contains OK
                        if (
                            str(json_data.get("status", "")) == "200"
                            and "msg" in json_data
                            and "OK" in json_data["msg"]
                        ):
                            self.logger.info(f"{device.name} ({domain}): API reachable and OK.")
                            success_count += 1
                        else:
                            self.logger.warning(f"{device.name} ({domain}): API reachable but unexpected JSON content.")
                            fail_count += 1
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

jobs.register_jobs(RacomDevicePing)

