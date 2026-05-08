"""
polar_auth.py
─────────────
Standalone OAuth2 authorization flow for the Polar AccessLink API.
Run once from CLI: python -m auth.polar_auth

Produces: config.yml with access_token and user_id written.
Has zero dependencies on Streamlit or any other app layer.

Layer 1 — Auth (zero imports from other layers)
"""

import webbrowser
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import yaml
from requests_oauthlib import OAuth2Session
import requests

# ── Polar OAuth2 endpoints ───────────────────────────────────────────────────
AUTH_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"
REGISTER_URL = "https://www.polaraccesslink.com/v3/users"
REDIRECT_URI = "http://localhost:5000/callback"
SCOPE = "accesslink.read_all"

CONFIG_PATH = Path("config.yml")


def load_config() -> dict:
    """Load configuration from config.yml."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"{CONFIG_PATH} not found. "
            "Copy config.example.yml to config.yml and add your credentials."
        )
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_token(token: dict, user_id: str) -> None:
    """Save access token and user ID to config.yml."""
    config = load_config()
    config["access_token"] = token["access_token"]
    config["user_id"] = user_id
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def get_token() -> str:
    """
    Public interface: returns the stored access token. No OAuth logic here.
    
    Returns:
        str: Access token for Polar AccessLink API
        
    Raises:
        RuntimeError: If no access token found in config
    """
    config = load_config()
    token = config.get("access_token")
    if not token:
        raise RuntimeError(
            "No access token found. Run: python -m auth.polar_auth"
        )
    return token


def get_user_id() -> str:
    """
    Public interface: returns the stored Polar user ID.
    
    Returns:
        str: Polar user ID
        
    Raises:
        RuntimeError: If no user ID found in config
    """
    config = load_config()
    user_id = config.get("user_id")
    if not user_id:
        raise RuntimeError(
            "No user ID found. Run: python -m auth.polar_auth"
        )
    return str(user_id)


def authorize() -> None:
    """Run the full one-time authorization flow."""
    config = load_config()
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    
    print(f"\n[CONFIG] Client ID: {client_id}")
    print(f"[CONFIG] Redirect URI: {REDIRECT_URI}")
    print(f"[CONFIG] Scope: {SCOPE}\n")
    print("IMPORTANT: Verify the redirect URI above matches EXACTLY what's")
    print("configured in your Polar AccessLink admin panel.\n")

    oauth = OAuth2Session(client_id, redirect_uri=REDIRECT_URI, scope=SCOPE)
    auth_url, _ = oauth.authorization_url(AUTH_URL)

    # Start the callback server in the background before opening browser
    code_holder = {"code": None, "server_ready": False}
    
    def run_server():
        """Run callback server in background thread."""
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                print(f"[DEBUG] Received request: {self.path}")
                
                # Only process requests to /callback with parameters
                if "/callback" in self.path:
                    parsed = urlparse(self.path)
                    params = parse_qs(parsed.query)
                    
                    print(f"[DEBUG] Callback params: {list(params.keys())}")
                    
                    # Check for error response from Polar
                    if "error" in params:
                        error = params.get("error", ["unknown"])[0]
                        error_desc = params.get("error_description", [""])[0]
                        print(f"[ERROR] OAuth error: {error}")
                        if error_desc:
                            print(f"[ERROR] Description: {error_desc}")
                        self.send_response(400)
                        self.end_headers()
                        msg = f"Authorization failed: {error}"
                        if error_desc:
                            msg += f"\nDescription: {error_desc}"
                        self.wfile.write(msg.encode('utf-8'))
                        code_holder["code"] = "ERROR"  # Signal error
                        return
                    
                    # Check for authorization code
                    code = params.get("code", [None])[0]
                    if code:
                        print(f"[SUCCESS] Received authorization code")
                        code_holder["code"] = code
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"Authorization complete! You may close this tab.")
                        return
                    
                    # Callback received but no code
                    print(f"[WARNING] Callback received but no code parameter")
                
                # Ignore other requests (favicon, etc.)
                print(f"[DEBUG] Ignoring non-callback request: {self.path}")
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass  # suppress default server logs

        server = HTTPServer(("localhost", 5000), CallbackHandler)
        code_holder["server_ready"] = True
        
        # Keep handling requests until we get the authorization code
        while code_holder["code"] is None:
            server.handle_request()
        
        server.server_close()
    
    # Start server thread
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to be ready
    while not code_holder["server_ready"]:
        time.sleep(0.1)
    
    print(f"\n✓ Callback server ready on localhost:5000")
    print(f"\nOpening browser for Polar authorization...\n{auth_url}\n")
    webbrowser.open(auth_url)
    
    # Wait for callback (with timeout)
    print("Waiting for authorization callback...")
    timeout = 300  # 5 minutes
    elapsed = 0
    while code_holder["code"] is None and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5
    
    code = code_holder["code"]
    if not code:
        raise RuntimeError("Authorization failed: no code received (timeout or user cancelled).")
    
    if code == "ERROR":
        raise RuntimeError("Authorization failed: Polar returned an error (see output above).")

    print(f"[DEBUG] Exchanging authorization code for access token...")
    
    # Exchange code for token (Basic Auth as required by Polar)
    token = oauth.fetch_token(
        TOKEN_URL,
        code=code,
        client_secret=client_secret,
        include_client_id=True,
    )

    # Register user (required once)
    user_id = token.get("x_user_id")
    resp = requests.post(
        REGISTER_URL,
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "Content-Type": "application/json",
        },
    )
    
    # 409 Conflict means user already registered (acceptable)
    if resp.status_code not in (200, 201, 409):
        print(f"Warning: User registration returned {resp.status_code}")

    save_token(token, str(user_id))
    print(f"✓ Authorization complete. Token saved for user {user_id}.")


if __name__ == "__main__":
    authorize()
