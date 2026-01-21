---
name: argo-workflow
description: Manage Argo Workflows using the argo CLI. Submit workflows, monitor execution, view logs, and control workflow lifecycle (pause, resume, retry, terminate, delete). Use this skill when working with Kubernetes workflows, CI/CD pipelines, batch jobs, or any Argo Workflow operations.
---

# Argo Workflow Management Skill

This skill provides comprehensive Argo Workflow management capabilities through the argo CLI command-line tool.

## When to Use This Skill

Use this skill when you need to:
- Submit and run Argo Workflows
- Monitor workflow execution status
- View real-time or historical workflow logs
- Control workflow lifecycle (pause, resume, terminate, retry)
- List and filter workflows by status or namespace
- Validate workflow YAML syntax
- Delete or clean up workflows

## Prerequisites

- `argo` CLI must be installed and available in PATH
- `kubectl` must be configured with access to your Kubernetes cluster
- Appropriate RBAC permissions for the target namespace

## Core Operations

### 1. Discover Available Commands

To see all available argo commands:
```bash
argo --help
```

To get help for a specific command:
```bash
argo <command> --help
# Examples:
# argo submit --help
# argo list --help
# argo logs --help
```

### 2. Submit Workflows

Basic submission:
```bash
argo submit <workflow-file.yaml> -n <namespace>
```

With parameters:
```bash
argo submit <workflow-file.yaml> -n <namespace> \
  -p param1=value1 \
  -p param2=value2
```

Submit and wait for completion:
```bash
argo submit <workflow-file.yaml> -n <namespace> --wait
```

Submit and watch execution:
```bash
argo submit <workflow-file.yaml> -n <namespace> --watch
```

Get JSON output:
```bash
argo submit <workflow-file.yaml> -n <namespace> -o json
```

### 3. List Workflows

List all workflows in namespace:
```bash
argo list -n <namespace>
```

Filter by status:
```bash
argo list -n <namespace> --status Running
argo list -n <namespace> --status Succeeded
argo list -n <namespace> --status Failed
```

List across all namespaces:
```bash
argo list --all-namespaces
```

Get JSON output:
```bash
argo list -n <namespace> -o json
```

### 4. Get Workflow Details

Get detailed information:
```bash
argo get <workflow-name> -n <namespace>
```

Get as JSON:
```bash
argo get <workflow-name> -n <namespace> -o json
```

### 5. View Workflow Logs

Get all logs:
```bash
argo logs <workflow-name> -n <namespace>
```

Follow logs in real-time:
```bash
argo logs <workflow-name> -n <namespace> --follow
```

Get logs for specific container:
```bash
argo logs <workflow-name> -n <namespace> -c <container-name>
```

Get recent logs:
```bash
argo logs <workflow-name> -n <namespace> --since 5m
argo logs <workflow-name> -n <namespace> --tail 100
```

### 6. Watch Workflow Execution

Monitor workflow in real-time:
```bash
argo watch <workflow-name> -n <namespace>
```

### 7. Control Workflow Lifecycle

**Terminate** (stop running workflow):
```bash
argo terminate <workflow-name> -n <namespace>
```

**Suspend** (pause execution):
```bash
argo suspend <workflow-name> -n <namespace>
```

**Resume** (continue paused workflow):
```bash
argo resume <workflow-name> -n <namespace>
```

**Retry** (retry failed workflow):
```bash
argo retry <workflow-name> -n <namespace>
```

**Resubmit** (create new instance from completed workflow):
```bash
argo resubmit <workflow-name> -n <namespace>
```

### 8. Delete Workflows

Delete a workflow:
```bash
argo delete <workflow-name> -n <namespace>
```

Force delete:
```bash
argo delete <workflow-name> -n <namespace> --force
```

### 9. Validate Workflow YAML

Check syntax before submitting:
```bash
argo lint <workflow-file.yaml>
```

## Common Workflow Statuses

- **Pending**: Workflow is waiting to start
- **Running**: Workflow is currently executing
- **Succeeded**: Workflow completed successfully
- **Failed**: Workflow failed during execution
- **Error**: Workflow encountered an error
- **Skipped**: Workflow step was skipped
- **Omitted**: Workflow step was omitted

## Usage Examples

### Example 1: Complete Workflow Submission Flow
```bash
# 1. Validate the workflow first
argo lint workflows/my-workflow.yaml

# 2. Submit the workflow
argo submit workflows/my-workflow.yaml -n argo -o json

# 3. Get the workflow name from output, then monitor it
argo watch my-workflow-xxxxx -n argo

# 4. View logs
argo logs my-workflow-xxxxx -n argo
```

### Example 2: Monitor Running Workflows
```bash
# List all running workflows
argo list -n argo --status Running

# Watch a specific workflow
argo watch my-workflow-xxxxx -n argo

# Follow logs in real-time
argo logs my-workflow-xxxxx -n argo --follow
```

### Example 3: Handle Failed Workflows
```bash
# List failed workflows
argo list -n argo --status Failed

# Get details about failure
argo get failed-workflow-xxxxx -n argo

# View error logs
argo logs failed-workflow-xxxxx -n argo

# Retry the workflow
argo retry failed-workflow-xxxxx -n argo
```

### Example 4: Cleanup Old Workflows
```bash
# List completed workflows
argo list -n argo --status Succeeded

# Delete old workflow
argo delete old-workflow-xxxxx -n argo
```

## Best Practices

1. **Always validate before submitting**: Use `argo lint` to catch syntax errors early
2. **Use meaningful parameter names**: Makes workflows more maintainable
3. **Monitor long-running workflows**: Use `watch` or `logs --follow` for real-time updates
4. **Use namespace isolation**: Separate dev/test/prod workflows by namespace
5. **Clean up completed workflows**: Regularly delete old workflows to free resources
6. **Check logs for debugging**: Always review logs when workflows fail
7. **Use JSON output for automation**: Parse JSON output in scripts with `jq`

## Troubleshooting

**Skill not triggering?**
- Make sure to mention "argo" or "workflow" in your request
- Try being more specific: "submit argo workflow" or "check workflow status"

**Command fails?**
- Verify `argo` CLI is installed: `which argo`
- Check kubectl context: `kubectl config current-context`
- Verify namespace exists: `kubectl get namespaces`
- Check RBAC permissions

**Workflow stuck in Pending?**
- Check cluster resources: `kubectl top nodes`
- Verify workflow controller is running
- Check for resource quota issues

## Script Support

This skill executes argo CLI commands directly. When you ask Claude