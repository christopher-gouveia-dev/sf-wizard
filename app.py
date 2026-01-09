#!/usr/bin/env python3
"""
SF Wizard - Salesforce utility application
Uses http.server with custom routing (no Flask dependency)
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Tuple, Any

from excel_generator import generate_where_in
from workspace_manager import WorkspaceManager

class RequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler with routing"""
    
    workspace_manager = None
    
    def do_GET(self) -> None:
        """Handle GET requests"""
        path = urllib.parse.urlparse(self.path).path
        query = urllib.parse.urlparse(self.path).query
        
        if path == "/" or path == "/index.html":
            self.serve_file("templates/index.html", "text/html")
        elif path.startswith("/api/"):
            self.handle_api_get(path, query)
        else:
            self.send_404()
    
    def do_POST(self) -> None:
        """Handle POST requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path.startswith("/api/"):
            self.handle_api_post(path)
        else:
            self.send_404()
    
    def handle_api_get(self, path: str, query: str) -> None:
        """Route GET API requests"""
        if path == "/api/workspaces":
            self.get_workspaces()
        elif path == "/api/workspace-info":
            params = urllib.parse.parse_qs(query)
            workspace = params.get("workspace", [None])[0]
            self.get_workspace_info(workspace)
        elif path == "/api/columns":
            params = urllib.parse.parse_qs(query)
            workspace = params.get("workspace", [None])[0]
            self.get_excel_columns(workspace)
        else:
            self.send_404()
    
    def handle_api_post(self, path: str) -> None:
        """Route POST API requests"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        if path == "/api/upload-excel":
            self.upload_excel(body)
        elif path == "/api/generate-where-in":
            self.generate_where_in_handler(body)
        else:
            self.send_404()
    
    def get_workspaces(self) -> None:
        """Get list of existing workspaces"""
        try:
            workspaces = self.workspace_manager.list_workspaces()
            self.send_json({"success": True, "workspaces": workspaces})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)
    
    def get_workspace_info(self, workspace: str) -> None:
        """Get workspace information"""
        try:
            if not workspace:
                self.send_json({"success": False, "error": "Workspace name required"}, 400)
                return
            
            info = self.workspace_manager.get_workspace_info(workspace)
            self.send_json({"success": True, "info": info})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)
    
    def get_excel_columns(self, workspace: str) -> None:
        """Get available columns from Excel file"""
        try:
            if not workspace:
                self.send_json({"success": False, "error": "Workspace name required"}, 400)
                return
            
            columns = self.workspace_manager.get_excel_columns(workspace)
            self.send_json({"success": True, "columns": columns})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)
    
    def upload_excel(self, body: bytes) -> None:
        """Handle Excel file upload"""
        try:
            # Parse multipart form data
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self.send_json({"success": False, "error": "Invalid content type"}, 400)
                return
            
            # Extract boundary
            boundary = content_type.split("boundary=")[1].encode()
            
            # Parse form data
            form_data = self.parse_multipart(body, boundary)
            
            if "excel" not in form_data or "workspace_name" not in form_data:
                self.send_json({"success": False, "error": "Missing required fields"}, 400)
                return
            
            workspace_name = form_data["workspace_name"].decode()
            file_content = form_data["excel"]
            
            # Create workspace and upload file
            result = self.workspace_manager.create_or_update_workspace(
                workspace_name, file_content
            )
            
            self.send_json({"success": True, "workspace": workspace_name})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)
    
    def generate_where_in_handler(self, body: bytes) -> None:
        """Handle WHERE IN generation"""
        try:
            data = json.loads(body.decode())
            
            required_fields = ["workspace", "generator_name", "source", "where_col"]
            if not all(field in data for field in required_fields):
                self.send_json({"success": False, "error": "Missing required fields"}, 400)
                return
            
            result = self.workspace_manager.generate_where_in(
                workspace=data["workspace"],
                generator_name=data["generator_name"],
                source=data["source"],
                where_col=data["where_col"],
                has_header=data.get("has_header", False),
                soql_base=data.get("soql_base", "")
            )
            
            self.send_json({"success": True, "version": result})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)
    
    def parse_multipart(self, body: bytes, boundary: bytes) -> Dict[str, bytes]:
        """Parse multipart form data"""
        form_data = {}
        parts = body.split(b"--" + boundary)
        
        for part in parts[1:-1]:
            if b"\r\n\r\n" not in part:
                continue
            
            header, content = part.split(b"\r\n\r\n", 1)
            content = content.rstrip(b"\r\n")
            
            # Extract field name
            for line in header.split(b"\r\n"):
                if b"name=" in line:
                    name_start = line.find(b'name="') + 6
                    name_end = line.find(b'"', name_start)
                    field_name = line[name_start:name_end].decode()
                    form_data[field_name] = content
                    break
        
        return form_data
    
    def serve_file(self, filepath: str, content_type: str) -> None:
        """Serve a static file"""
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_404()
    
    def send_json(self, data: Dict[str, Any], status_code: int = 200) -> None:
        """Send JSON response"""
        content = json.dumps(data).encode()
        
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)
    
    def send_404(self) -> None:
        """Send 404 response"""
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"404 Not Found")
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(host: str = "localhost", port: int = 8000) -> None:
    """Start the HTTP server"""
    RequestHandler.workspace_manager = WorkspaceManager()
    
    server = HTTPServer((host, port), RequestHandler)
    
    print("="*50)
    print("SF Wizard Server")
    print("="*50)
    print(f"Server running at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    print("="*50 + "\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
