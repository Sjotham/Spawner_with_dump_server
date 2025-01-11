from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import json
import sys
import asyncio
from jupyterhub.spawner import Spawner

# Import KubeSpawner
sys.path.append("/home/kubespawner/")  # Add the correct path to KubeSpawner
from kubespawner import KubeSpawner

class MockHub:
    """Mock class to represent the Hub for the spawner."""
    def __init__(self):
        self.public_host = "http://127.0.0.1:8081"
        self.url = "http://127.0.0.1:8081"
        self.base_url = "/hub/"
        self.api_url = "http://127.0.0.1:8081/hub/api"

class JSONRPCHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Parse the content length and read the request body
        content_length = int(self.headers['Content-Length'])
        request_body = self.rfile.read(content_length).decode('utf-8')

        # Parse JSON request
        try:
            request = json.loads(request_body)
            method = request.get('method')
            params = request.get('params', [])
            request_id = request.get('id')
        except json.JSONDecodeError:
            self.respond_with_error("Invalid JSON format", None)
            return

        # Dispatch the method
        response = asyncio.run(self.dispatch_method_async(method, params, request_id))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    async def dispatch_method_async(self, method, params, request_id):
        """Handle the method dispatch asynchronously."""
        methods = {
            "create_k8s_pod": self.create_k8s_pod,
        }

        if method not in methods:
            return self.create_error_response(f"Method {method} not found", request_id)

        try:
            # Call the method and return the result
            result = await methods[method](*params)
            return self.create_response(result, request_id)
        except Exception as e:
            return self.create_error_response(str(e), request_id)

    def create_response(self, result, request_id):
        """Create a JSON-RPC success response."""
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }

    async def create_k8s_pod(self, username, namespace="default"):
        """Create a Kubernetes pod using KubeSpawner for a given user."""
        try:
            user = MockUser(username)

            # Initialize the spawner with required attributes
            spawner = KubeSpawner(
                user=user,
                hub_url="http://127.0.0.1:8081",
                namespace=namespace
            )

            # Assign a MockHub object to spawner.hub
            spawner.hub = MockHub()

            # Assign other necessary attributes
            spawner.api_token = "dummy-token"
            spawner.user_options = {}

            # Assign the spawner to the user
            user.spawner = spawner

            # Start the spawner asynchronously
            await spawner.start()

            return {"message": f"Pod for user {username} started successfully in namespace {namespace}."}
        except Exception as e:
            return {"error": f"Error creating pod: {str(e)}"}



class MockUser:
    """Mock class to represent a user in JupyterHub."""
    def __init__(self, name):
        self.name = name
        self.id = name  # Set id as the username for simplicity
        self.spawner = None  # Placeholder for the spawner
        self.url = f"/user/{name}"  # Add a default URL based on the username

    def __str__(self):
        return self.name



def run_server():
    host, port = "127.0.0.1", 8000
    server = HTTPServer((host, port), JSONRPCHandler)
    print(f"JSON-RPC Server is running on {host}:{port}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down the server.")
        server.server_close()


if __name__ == "__main__":
    run_server()
