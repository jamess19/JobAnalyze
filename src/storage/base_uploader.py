class BaseUploader:
    """Base class for data uploaders."""
    def __init__(self):
        """Initializes the uploader."""
        pass
    
    def upload(self, filepath: str) -> str:
        """Uploads a file and returns the URL or identifier of the uploaded file.

        Args:
            filepath (str): The path to the file to be uploaded.
        Returns:
            str: The URL or identifier of the uploaded file.
        """
        pass
    

    