## Agent Coding Conventions

1.  **API Keys**:
    *   Prefer environment variables for API keys (e.g., `os.getenv('SERPAPI_API_KEY')`).
    *   If direct input is necessary, ensure it's handled securely and not hardcoded in committed files.
    *   Provide clear instructions to the user on how to set up API keys.

2.  **Modularity**:
    *   Break down the pipeline into well-defined functions or classes.
    *   Each major step in the plan (retrieval, filtering, generation) should correspond to distinct code modules/functions.

3.  **Error Handling**:
    *   Implement robust error handling, especially for API calls and file operations.
    *   Provide informative error messages to the user.

4.  **Data Storage**:
    *   Use structured formats like JSON or CSV for intermediate data storage.
    *   Ensure output files are saved in a designated `outputs/` directory.

5.  **User Feedback**:
    *   Keep the user informed about the progress of the pipeline (e.g., "Fetching articles...", "Filtering articles...").

6.  **Dependencies**:
    *   List all external libraries required for the project in a `requirements.txt` file (to be created later).

7.  **Reproducibility**:
    *   Save user input parameters and key intermediate results to allow for easier reproduction of results.
