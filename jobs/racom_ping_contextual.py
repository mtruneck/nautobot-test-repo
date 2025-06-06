import requests
from nautobot.apps.jobs import Job, JobButtonReceiver, ObjectVar
from nautobot.apps import jobs
from nautobot.dcim.models import Device, DeviceType

class RacomDeviceContextualPing(JobButtonReceiver):
    class Meta:
        name = "Racom Device Contextual Ping"
        description = "Ping RACOM device(s) from Device or Device Type page, or manually."
        commit_default = False
        model = ["dcim.device", "dcim.devicetype"]

    class InputVariables:
        # These are for manual runs or if user wants to override context
        device_input = ObjectVar(
            model=Device,
            required=False,
            label="Device (Manual/Override)",
            description="Specific device to ping (for manual run or to override context)."
        )
        device_type_input = ObjectVar(
            model=DeviceType,
            required=False,
            label="Device Type (Manual/Override)",
            description="Ping all devices of this Device Type (for manual run or to override context)."
        )

    def run(self, obj=None, data=None, commit=None):
        devices_to_ping = Device.objects.none() # Start with an empty queryset

        if obj:
            if isinstance(obj, Device):
                devices_to_ping = Device.objects.filter(pk=obj.pk)
                self.logger.info(f"Pinging device from context: {obj.name}")
            elif isinstance(obj, DeviceType):
                devices_to_ping = Device.objects.filter(device_type=obj)
                self.logger.info(f"Pinging devices of type from context: {obj.name}")
        elif data:
            if data.get("device_input"):
                devices_to_ping = Device.objects.filter(pk=data["device_input"].pk)
                self.logger.info(f"Pinging device from form input: {data['device_input']}")
            elif data.get("device_type_input"):
                devices_to_ping = Device.objects.filter(device_type=data["device_type_input"])
                self.logger.info(f"Pinging devices of type from form input: {data['device_type_input']}")
            else:
                devices_to_ping = Device.objects.all()
                self.logger.info("Pinging all devices (manual run, no specific input).")
        else:
            devices_to_ping = Device.objects.all()
            self.logger.info("Pinging all devices (no context, no specific input).")

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
                # Disable SSL verification for self-signed certs, common in lab/internal devices
                # In a production environment, proper certificate management is crucial.
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
            except Exception as e:
                self.logger.error(f"{dev_instance.name} ({domain}): Generic Exception: {e}")
                fail_count += 1

        summary = f"Contextual Ping: Processed {devices_to_ping.count()} device(s). Successful: {success_count}, Failed: {fail_count}."
        self.logger.info(summary)
        return summary

jobs.register_jobs(RacomDeviceContextualPing)
