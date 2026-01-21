#!/usr/bin/env python3
"""
Argo Workflow Helper Script
Provides advanced workflow operations for Claude Code skill
"""

import subprocess
import json
import sys
from typing import Dict, List, Optional, Any


def run_command(cmd: List[str], timeout: int = 60) -> Dict[str, Any]:
    """Execute a command and return structured output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out",
            "returncode": -1
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "returncode": -1
        }


def get_workflows_json(namespace: str = "default", status: Optional[str] = None) -> Dict[str, Any]:
    """Get workflows as structured JSON"""
    cmd = ["argo", "list", "-n", namespace, "-o", "json"]
    if status:
        cmd.extend(["--status", status])
    
    result = run_command(cmd)
    if not result["success"]:
        return {"error": result.get("stderr", result.get("error"))}
    
    try:
        data = json.loads(result["stdout"])
        workflows = []
        items = data if isinstance(data, list) else data.get("items", [])
        
        for wf in items:
            workflows.append({
                "name": wf.get("metadata", {}).get("name"),
                "namespace": wf.get("metadata", {}).get("namespace"),
                "status": wf.get("status", {}).get("phase"),
                "created": wf.get("metadata", {}).get("creationTimestamp"),
                "finished": wf.get("status", {}).get("finishedAt"),
                "progress": wf.get("status", {}).get("progress")
            })
        
        return {"workflows": workflows, "count": len(workflows)}
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON output"}


def get_workflow_details(name: str, namespace: str = "default") -> Dict[str, Any]:
    """Get detailed workflow information"""
    cmd = ["argo", "get", name, "-n", namespace, "-o", "json"]
    result = run_command(cmd)
    
    if not result["success"]:
        return {"error": result.get("stderr", result.get("error"))}
    
    try:
        data = json.loads(result["stdout"])
        return {
            "name": name,
            "status": data.get("status", {}).get("phase"),
            "message": data.get("status", {}).get("message"),
            "progress": data.get("status", {}).get("progress"),
            "nodes": data.get("status", {}).get("nodes", {}),
            "full_data": data
        }
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON output"}


def submit_workflow(
    workflow_file: str,
    namespace: str = "default",
    parameters: Optional[Dict[str, str]] = None,
    wait: bool = False
) -> Dict[str, Any]:
    """Submit a workflow with parameters"""
    cmd = ["argo", "submit", workflow_file, "-n", namespace, "-o", "json"]
    
    if parameters:
        for key, value in parameters.items():
            cmd.extend(["-p", f"{key}={value}"])
    
    if wait:
        cmd.append("--wait")
    
    result = run_command(cmd, timeout=600 if wait else 60)
    
    if not result["success"]:
        return {"error": result.get("stderr", result.get("error"))}
    
    try:
        data = json.loads(result["stdout"])
        return {
            "workflow_name": data.get("metadata", {}).get("name"),
            "namespace": data.get("metadata", {}).get("namespace"),
            "uid": data.get("metadata", {}).get("uid"),
            "status": data.get("status", {}).get("phase")
        }
    except json.JSONDecodeError:
        return {"output": result["stdout"]}


def batch_retry_failed(namespace: str = "default", limit: int = 10) -> Dict[str, Any]:
    """Retry all failed workflows in a namespace"""
    workflows_result = get_workflows_json(namespace, status="Failed")
    
    if "error" in workflows_result:
        return workflows_result
    
    workflows = workflows_result.get("workflows", [])[:limit]
    results = []
    
    for wf in workflows:
        name = wf.get("name")
        cmd = ["argo", "retry", name, "-n", namespace]
        result = run_command(cmd)
        results.append({
            "workflow": name,
            "success": result["success"],
            "message": result.get("stdout") if result["success"] else result.get("stderr")
        })
    
    return {
        "total_attempted": len(results),
        "results": results
    }


def batch_delete_succeeded(namespace: str = "default", limit: int = 50) -> Dict[str, Any]:
    """Delete succeeded workflows to clean up"""
    workflows_result = get_workflows_json(namespace, status="Succeeded")
    
    if "error" in workflows_result:
        return workflows_result
    
    workflows = workflows_result.get("workflows", [])[:limit]
    results = []
    
    for wf in workflows:
        name = wf.get("name")
        cmd = ["argo", "delete", name, "-n", namespace]
        result = run_command(cmd)
        results.append({
            "workflow": name,
            "success": result["success"]
        })
    
    return {
        "total_deleted": sum(1 for r in results if r["success"]),
        "total_attempted": len(results),
        "results": results
    }


def get_workflow_summary(namespace: str = "default") -> Dict[str, Any]:
    """Get summary statistics for workflows"""
    workflows_result = get_workflows_json(namespace)
    
    if "error" in workflows_result:
        return workflows_result
    
    workflows = workflows_result.get("workflows", [])
    
    summary = {
        "total": len(workflows),
        "by_status": {},
        "namespace": namespace
    }
    
    for wf in workflows:
        status = wf.get("status", "Unknown")
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
    
    return summary


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: argo_helper.py <command> [args...]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        namespace = sys.argv[2] if len(sys.argv) > 2 else "default"
        status = sys.argv[3] if len(sys.argv) > 3 else None
        result = get_workflows_json(namespace, status)
        print(json.dumps(result, indent=2))
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: argo_helper.py get <workflow-name> [namespace]")
            sys.exit(1)
        name = sys.argv[2]
        namespace = sys.argv[3] if len(sys.argv) > 3 else "default"
        result = get_workflow_details(name, namespace)
        print(json.dumps(result, indent=2))
    
    elif command == "submit":
        if len(sys.argv) < 3:
            print("Usage: argo_helper.py submit <workflow-file> [namespace] [param1=value1,param2=value2]")
            sys.exit(1)
        workflow_file = sys.argv[2]
        namespace = sys.argv[3] if len(sys.argv) > 3 else "default"
        params = {}
        if len(sys.argv) > 4:
            for param in sys.argv[4].split(','):
                key, value = param.split('=')
                params[key] = value
        result = submit_workflow(workflow_file, namespace, params)
        print(json.dumps(result, indent=2))
    
    elif command == "summary":
        namespace = sys.argv[2] if len(sys.argv) > 2 else "default"
        result = get_workflow_summary(namespace)
        print(json.dumps(result, indent=2))
    
    elif command == "retry-failed":
        namespace = sys.argv[2] if len(sys.argv) > 2 else "default"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        result = batch_retry_failed(namespace, limit)
        print(json.dumps(result, indent=2))
    
    elif command == "cleanup-succeeded":
        namespace = sys.argv[2] if len(sys.argv) > 2 else "default"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        result = batch_delete_succeeded(namespace, limit)
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)