import requests
from nautobot.apps.jobs import JobButtonReceiver, ObjectVar # JobButtonReceiver already inherits Job
from nautobot.apps import jobs
from nautobot.dcim.models import Device, DeviceType

class RacomDeviceContextualPing(JobButtonReceiver):
    class Meta:
        name = "Racom Device Contextual Ping"
        description = "Ping RACOM device(s) from Device or Device Type page, or manually."
        commit_default = False
        # model attribute tells JobButtonReceiver which object types this button should appear on
        model = ["dcim.device", "dcim.devicetype"]


    def _perform_ping(self, devices_to_ping):
        """
        Helper method containing the core pinging logic.
        """
        if not devices_to_ping.exists():
            self.logger.warning("No devices selected or found to ping.")
            return "No devices selected or found to ping."

        success_count = 0
        fail_count = 0

        for dev_instance in devices_to_ping:
            domain = dev_instance.custom_field_data.get("Domain")
            if not domain:
                self.logger.warning(f"Device {dev_instance.name} has no Domain custom field; skipping.")
                continue
            
            url = f"https://{domain}:443/cgi-bin/rpc.cgi"
            payload = {"method": "device_ping"}
            
            try:
                # Disable SSL verification for self-signed certs
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, verify=False, timeout=10)
                
                if resp.status_code == 200:
                    try:
                        json_data = resp.json()
                        self.logger.debug(f"Device {dev_instance.name} ({domain}) - Response: {json_data}")
                        if str(json_data.get("status", "")) == "200" and "msg" in json_data and "OK" in json_data["msg"]:
                            self.logger.info(f"{dev_instance.name} ({domain}): API reachable and OK.")
                            success_count += 1
                        else:
                            self.logger.warning(f"{dev_instance.name} ({domain}): API reachable but unexpected JSON content: {json_data.get('msg', 'N/A')}")
                            fail_count += 1
                    except requests.exceptions.JSONDecodeError as json_exc:
                        self.logger.error(f"{dev_instance.name} ({domain}): Response is not valid JSON: {json_exc}. Raw response: {resp.text[:200]}...")
                        fail_count += 1
                else:
                    self.logger.error(f"{dev_instance.name} ({domain}): API NOT reachable. Status: {resp.status_code}. Response: {resp.text[:200]}...")
                    fail_count += 1
            except requests.exceptions.RequestException as e:
                self.logger.error(f"{dev_instance.name} ({domain}): Request Exception: {e}")
                fail_count += 1
            except Exception as e: # Generic exception
                self.logger.error(f"{dev_instance.name} ({domain}): Generic Exception during ping: {e}")
                fail_count += 1

        summary = f"Ping Results: Processed {devices_to_ping.count()} device(s). Successful: {success_count}, Failed: {fail_count}."
        self.logger.info(summary)
        return summary

    def receive_job_button(self, obj):
        if isinstance(obj, Device):
            self.logger.info(f"Context: Device - {obj.name}")
            devices_to_ping = Device.objects.filter(pk=obj.pk)
            return self._perform_ping(devices_to_ping)
        elif isinstance(obj, DeviceType):
            self.logger.info(f"Context: DeviceType - {obj.name}")
            devices_to_ping = Device.objects.filter(device_type=obj)
            return self._perform_ping(devices_to_ping)
        else:
            self.logger.error(f"Unsupported object type for button trigger: {type(obj).__name__}")
            return f"Error: Job button called on unsupported object type {type(obj).__name__}."

jobs.register_jobs(RacomDeviceContextualPing)
