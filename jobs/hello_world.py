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
        # Initialize default values
        semaphore_url = "http://semaphore:3000"
        username = "admin"
        password = "admin"
        project_id = "1"
        template_id = "1"
        debug_mode = False
        
        # Extract parameters from input data if provided
        if data is not None:
            semaphore_url = data.get("semaphore_url", semaphore_url)
            username = data.get("username", username)
            password = data.get("password", password)
            project_id = data.get("project_id", project_id)
            template_id = data.get("template_id", template_id)
            debug_mode = data.get("debug_mode", debug_mode)
        
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
            
            # Monitor task until completion
            self.logger.info(f"Monitoring task {task_id} until completion...")
            
            import time
            max_attempts = 60  # Maximum number of attempts (10 minutes with 10-second intervals)
            attempt = 0
            completed_statuses = ["success", "error", "failed"]
            
            while attempt < max_attempts:
                # Get task status
                task_status_url = f"{semaphore_url}/api/project/{project_id}/tasks/{task_id}"
                task_status_headers = {
                    "accept": "application/json",
                    "Cookie": f"semaphore={semaphore_cookie}"
                }
                
                try:
                    task_status_response = requests.get(
                        task_status_url,
                        headers=task_status_headers,
                        verify=False
                    )
                    
                    if task_status_response.status_code != 200:
                        self.logger.warning(f"Failed to get task status: {task_status_response.status_code}")
                        attempt += 1
                        time.sleep(10)
                        continue
                    
                    # Parse task status
                    current_task = task_status_response.json()
                    current_status = current_task.get("status")
                    
                    # Log current status
                    self.logger.info(f"Task {task_id} status: {current_status} (attempt {attempt+1}/{max_attempts})")
                    
                    # Check if task is completed
                    if current_status in completed_statuses:
                        # Get task output
                        self.logger.info(f"Task {task_id} completed with status: {current_status}")
                        
                        # Get task output/logs
                        task_output_url = f"{semaphore_url}/api/project/{project_id}/tasks/{task_id}/output"
                        task_output_headers = {
                            "accept": "application/json",
                            "Cookie": f"semaphore={semaphore_cookie}"
                        }
                        
                        task_output_response = requests.get(
                            task_output_url,
                            headers=task_output_headers,
                            verify=False
                        )
                        
                        if task_output_response.status_code == 200:
                            # Parse and log task output
                            task_output = task_output_response.json()
                            
                            # Log summary of task output
                            self.logger.info("Task Output Summary:")
                            for output_line in task_output:
                                output_time = output_line.get("time")
                                output_type = output_line.get("type")
                                output_output = output_line.get("output")
                                
                                if output_type == "play" or output_type == "task" or "fatal" in output_output.lower():
                                    self.logger.info(f"[{output_time}] [{output_type}] {output_output}")
                        else:
                            self.logger.warning(f"Failed to get task output: {task_output_response.status_code}")
                        
                        # Return success or failure based on task status
                        if current_status == "success":
                            return f"Task {task_id} completed successfully"
                        else:
                            return f"Task {task_id} failed with status: {current_status}"
                
                except Exception as e:
                    self.logger.error(f"Error checking task status: {str(e)}")
                
                # Increment attempt counter and wait before next check
                attempt += 1
                time.sleep(10)
            
            # If we've reached the maximum number of attempts, return a timeout message
            self.logger.warning(f"Reached maximum monitoring attempts for task {task_id}. Last status: {current_status}")
            return f"Task monitoring timed out after {max_attempts * 10} seconds. Last status: {current_status}"
            
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
