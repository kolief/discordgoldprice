# OSRS Discord Gold Price

This Python script scrapes OSRS gold prices from `merchants.to` & `eldorado.gg` API endpoints and posts them to a Discord webhook. It is designed to be run in a Docker container.

Here is an example:

![alt text](https://github.com/kolief/discordgoldprice/blob/main/example.png)

## Prerequisites

*   Docker installed on your system.
*   A Discord Webhook URL.

## Files

*   `discordgold.py`: The main Python script.
*   `Dockerfile`: Defines the Docker image for the application.
*   `requirements.txt`: Lists the Python dependencies (`cloudscraper`).

## Configuration

The script requires a Discord Webhook URL to send notifications. This URL must be provided as an environment variable named `DISCORD_WEBHOOK_URL` when running the Docker container.

You can set this URL directly in the `discordgold.py` script if you are not using Docker or if you prefer to hardcode it, but using an environment variable is recommended for Docker deployments.

## Building the Docker Image

1.  Clone this repository or ensure all files (`discordgold.py`, `Dockerfile`, `requirements.txt`) are in the same directory.
2.  Open a terminal in that directory.
3.  Build the Docker image using the following command:

    ```bash
    docker build -t discordgold .
    ```

    This will create a Docker image tagged `discordgold`.

## Running the Docker Container

Once the image is built, you can run it as a container. You **must** provide your Discord webhook URL as an environment variable.

```bash
docker run -d --name osrs-gold-price-notifier \
    -e DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL_HERE" \
    discordgold
```

Replace `"YOUR_DISCORD_WEBHOOK_URL_HERE"` with your actual Discord webhook URL.

**Explanation of flags:**
*   `-d`: Runs the container in detached mode (in the background).
*   `--name osrs-gold-price-notifier`: Assigns a name to the container for easier management.
*   `-e DISCORD_WEBHOOK_URL="..."`: Sets the environment variable inside the container.

The script inside the container will then run and post updates to your Discord channel every 30 minutes.

## Viewing Logs

To view the logs from the running container (e.g., to check for errors or see script output):

```bash
docker logs osrs-gold-price-notifier
```

If you used a different name for your container, replace `osrs-gold-price-notifier` with the name you used. To follow the logs in real-time, add the `-f` flag:

```bash
docker logs -f osrs-gold-price-notifier
```

## Stopping the Container

To stop the container:

```bash
docker stop osrs-gold-price-notifier
```

## Updating

If you make changes to the script or `requirements.txt`:
1.  Stop the running container (if any).
2.  Remove the old container (optional, but good practice if you don't need it):
    ```bash
    docker rm osrs-gold-price-notifier
    ```
3.  Rebuild the Docker image:
    ```bash
    docker build -t discordgold .
    ```
4.  Run the new image as a container with the same command as before. 

## Hosting on a VPS (Without Docker)

If you prefer to run the script directly on a Virtual Private Server (VPS) without Docker, follow these steps:

### 1. Prerequisites

*   A VPS with SSH access.
*   Python 3 installed on the VPS (most modern Linux distributions come with Python 3).
*   `pip` (Python package installer) installed.
*   `git` installed (for cloning the repository).

### 2. Setup

1.  **Connect to your VPS via SSH.**

2.  **Clone the repository:**
    ```bash
    git clone https://github.com/YourRepo/discordgold # Replace with your repository URL if different
    cd discordgold
    ```

3.  **Create a Python virtual environment (recommended):**
    This isolates the script's dependencies from the system's Python packages.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    You'll need to activate the virtual environment (`source .venv/bin/activate`) every time you open a new shell session to work on this project.

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 3. Configuration

You need to provide the Discord Webhook URL to the script. You have two main options:

*   **Option A (Recommended for VPS): Modify the script (if not already done for Docker env var)**
    If your `discordgold.py` is set up to read the webhook URL from an environment variable, you can set it in your shell before running the script:
    ```bash
    export DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL_HERE"
    ```
    To make this permanent across reboots or new sessions, you can add this line to your shell's configuration file (e.g., `~/.bashrc`, `~/.zshrc`), then source it (e.g., `source ~/.bashrc`).

*   **Option B: Hardcode in the script (Less flexible)**
    You can directly edit the `discordgold.py` file and set the `DISCORD_WEBHOOK_URL` variable:
    ```python
    # In discordgold.py
    DISCORD_WEBHOOK_URL = "YOUR_ACTUAL_DISCORD_WEBHOOK_URL"
    ```
    Remember to save the file if you make this change.

### 4. Running the Script

Once configured, you can run the script:

*   **Directly (for testing):**
    ```bash
    python discordgold.py
    ```
    The script will run in the foreground, and you'll see its output directly in the terminal. Closing the terminal will stop the script.

*   **In the background (for continuous operation):**
    For long-term operation, you should run the script in the background and ensure it restarts if it crashes or the server reboots. Here are a few common methods:

    *   **Using `nohup` (simple):**
        ```bash
        nohup python discordgold.py > scraper.log 2>&1 &
        ```
        This runs the script in the background, redirects its output to `scraper.log`, and keeps it running even if you close your SSH session. To stop it, you'll need to find its process ID (`ps aux | grep discordgold.py`) and use `kill <PID>`.

    *   **Using a process manager (more robust, recommended for production):**
        Tools like `systemd` (common on modern Linux distributions) or `supervisor` can manage your script as a service. This typically involves creating a service configuration file that defines how to start, stop, and restart your script, and manage its logs. Setting up `systemd` or `supervisor` is beyond the scope of this README but is highly recommended for reliability.

        For example, a simple `systemd` service file might look like this (e.g., `/etc/systemd/system/discordgold.service`):

        ```ini
        [Unit]
        Description=OSRS Discord Gold Price
        After=network.target

        [Service]
        User=your_username # Replace with the user you want to run the script as
        WorkingDirectory=/path/to/discordgold # Replace with the actual path
        ExecStart=/path/to/discordgold/.venv/bin/python discordgold.py
        Restart=always
        Environment="DISCORD_WEBHOOK_URL=YOUR_DISCORD_WEBHOOK_URL_HERE"

        [Install]
        WantedBy=multi-user.target
        ```
        You would then enable and start it with `sudo systemctl enable discordgold` and `sudo systemctl start discordgold`.

Choose the method that best suits your needs for running the script continuously. 
