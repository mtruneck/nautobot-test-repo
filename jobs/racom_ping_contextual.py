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

    # InputVariables are for the 'Run Job' form (manual execution)
    # These are NOT used by receive_job_button directly but by the run() method.
    device_input = ObjectVar(
        model=Device,
        required=False,
        label="Device (for Manual Run)",
        description="Specific device to ping (used when running job manually)."
    )
    device_type_input = ObjectVar(
        model=DeviceType,
        required=False,
        label="Device Type (for Manual Run)",
        description="Ping all devices of this Device Type (used when running job manually)."
    )

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

    # This method is called by JobButtonReceiver's base run() method when triggered by a button.
    def receive_job_button(self, obj):
        """
        Handles job execution when triggered from a button on a Device or DeviceType page.
        'obj' is the instance of the Device or DeviceType model.
        """
        self.logger.info(f"Job triggered by button for object: {obj} (type: {type(obj).__name__})")
        devices_to_ping = Device.objects.none()

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

    # This method is called for manual runs (e.g., from the Jobs UI or API).
    # 'data' is a dictionary of the validated InputVariables.
    def run(self, data, commit=None): # Standard Job.run() signature
        """
        Handles job execution for manual runs.
        'data' contains validated input variables: device_input and device_type_input.
        """
        self.logger.info("Job triggered manually or via API.")
        devices_to_ping = Device.objects.none()

        device_from_input = data.get("device_input")
        device_type_from_input = data.get("device_type_input")

        if device_from_input:
            self.logger.info(f"Manual run: Pinging device from form input: {device_from_input}")
            devices_to_ping = Device.objects.filter(pk=device_from_input.pk)
        elif device_type_from_input:
            self.logger.info(f"Manual run: Pinging devices of type from form input: {device_type_from_input}")
            devices_to_ping = Device.objects.filter(device_type=device_type_from_input)
        else:
            self.logger.warning("Manual run: No specific device or device type provided. Please select an input.")
            return "Manual run: Please specify a Device or Device Type to ping. No devices will be pinged."

        return self._perform_ping(devices_to_ping)

jobs.register_jobs(RacomDeviceContextualPing)
