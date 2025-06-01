# Import and register all job classes
from nautobot.apps.jobs import register_jobs
from .hello_world import HelloWorldJob

# Register all jobs
register_jobs(HelloWorldJob)
