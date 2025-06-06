# Import and register all job classes
from nautobot.apps.jobs import register_jobs
from .hello_world import HelloWorldJob, SemaphoreTaskRunner
from .racom_ping import RacomDevicePing

# Register all jobs
register_jobs(HelloWorldJob, SemaphoreTaskRunner, RacomDevicePing)
