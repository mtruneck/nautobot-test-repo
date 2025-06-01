from nautobot.apps.jobs import Job, StringVar


class HelloWorldJob(Job):
    """
    A simple Hello World job that demonstrates the basic structure of a Nautobot job.
    """
    class Meta:
        name = "Hello World"
        description = "A simple job that says hello to the world"
        commit_default = False

    # Input variables for the job
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
        name = data.get("name", "World")
        
        # Log a message that will be displayed in the job result
        self.log_info(f"Hello, {name}!")
        
        # Return a success message
        return f"Successfully said hello to {name}!"
