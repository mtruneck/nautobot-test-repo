from nautobot.apps.jobs import Job, StringVar, BooleanVar
import requests
import json


class SemaphoreTaskRunner(Job):
    """
    A job that logs into Semaphore and runs a specified task template.
    """
    class Meta:
        name = "Semaphore Task Runner"
        description = "Logs into Semaphore and runs a specified task template"
        commit_default = False

    # Define class variables for job inputs
    class InputVariables:
        semaphore_url = StringVar(
            description="Semaphore URL",
            default="http://semaphore:3000",
            required=True
        )
        username = StringVar(
            description="Semaphore username",
            default="admin",
            required=True
        )
        password = StringVar(
            description="Semaphore password",
            default="admin",
            required=True
        )
        project_id = StringVar(
            description="Semaphore project ID",
            default="1",
            required=True
        )
        template_id = StringVar(
            description="Semaphore task template ID",
            default="1",
            required=True
        )
        debug_mode = BooleanVar(
            description="Enable debug mode for the task",
            default=False,
            required=False
        )

    def run(self, data=None, commit=None):
        """
        The main execution method of the job.
        """
        if data is None:
            self.logger.error("No input data provided")
            return "Failed: No input data provided"
        
        # Extract parameters from input data
        semaphore_url = data.get("semaphore_url", "http://semaphore:3000")
        username = data.get("username", "admin")
        password = data.get("password", "admin")
        project_id = data.get("project_id", "1")
        template_id = data.get("template_id", "1")
        debug_mode = data.get("debug_mode", False)
        
        # Log the start of the job
        self.logger.info(f"Starting Semaphore task runner for template {template_id} in project {project_id}")
        
        try:
            # Step 1: Login to Semaphore
            self.logger.info("Logging into Semaphore...")
            login_url = f"{semaphore_url}/api/auth/login"
            login_payload = {
                "auth": username,
                "password": password
            }
            login_headers = {
                "accept": "application/json",
                "Content-Type": "application/json"
            }
            
            login_response = requests.post(
                login_url,
                headers=login_headers,
                json=login_payload,
                verify=False  # Note: In production, you should verify SSL certificates
            )
            
            if login_response.status_code != 204:
                self.logger.error(f"Failed to login to Semaphore: {login_response.status_code} {login_response.text}")
                return f"Failed to login to Semaphore: {login_response.status_code}"
            
            # Extract the session cookie
            semaphore_cookie = login_response.cookies.get("semaphore")
            if not semaphore_cookie:
                self.logger.error("No session cookie received from Semaphore")
                return "Failed: No session cookie received from Semaphore"
            
            self.logger.info("Successfully logged into Semaphore")
            
            # Step 2: Run the task template
            self.logger.info(f"Running task template {template_id}...")
            run_task_url = f"{semaphore_url}/api/project/{project_id}/tasks"
            run_task_payload = {
                "template_id": int(template_id)
            }
            
            # Add debug mode if requested
            if debug_mode:
                run_task_payload["debug"] = True
            
            run_task_headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "Cookie": f"semaphore={semaphore_cookie}"
            }
            
            run_task_response = requests.post(
                run_task_url,
                headers=run_task_headers,
                json=run_task_payload,
                verify=False  # Note: In production, you should verify SSL certificates
            )
            
            if run_task_response.status_code != 201:
                self.logger.error(f"Failed to run task template: {run_task_response.status_code} {run_task_response.text}")
                return f"Failed to run task template: {run_task_response.status_code}"
            
            # Parse the response
            task_result = run_task_response.json()
            task_id = task_result.get("id")
            task_status = task_result.get("status")
            
            self.logger.success(f"Successfully started task with ID {task_id}, status: {task_status}")
            
            # Return a success message with the task ID
            return f"Successfully started Semaphore task with ID {task_id}, status: {task_status}"
            
        except Exception as e:
            self.logger.error(f"Error running Semaphore task: {str(e)}")
            return f"Error running Semaphore task: {str(e)}"


class HelloWorldJob(Job):
    """
    A simple Hello World job that demonstrates the basic structure of a Nautobot job.
    """
    class Meta:
        name = "Hello World"
        description = "A simple job that says hello to the world"
        commit_default = False

    # Define class variables for job inputs
    class InputVariables:
        name = StringVar(
            description="Your name",
            default="World",
            required=False
        )

    def run(self, data=None, commit=None):
        """
        The main execution method of the job.
        """
        # Extract the name from the input data
        if data is None:
            name = "World"
        else:
            name = data.get("name", "World")
        
        # Log a message that will be displayed in the job result
        self.logger.info(f"Hello, {name}!")
        
        # Return a success message
        return f"Successfully said hello to {name}!"
