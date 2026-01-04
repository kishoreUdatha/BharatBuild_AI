#!/usr/bin/env python3
"""Update ECS task definition with EFS environment variables."""

import json
import subprocess
import sys

def run_aws(cmd):
    """Run AWS CLI command and return output."""
    full_cmd = f'"{r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"}" {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

# Get current task definition
print("Getting current task definition...")
task_def_json = run_aws('ecs describe-task-definition --task-definition bharatbuild-backend --query "taskDefinition"')
task_def = json.loads(task_def_json)

# Add EFS environment variables
env_vars = task_def['containerDefinitions'][0]['environment']
efs_vars = [
    {"name": "SANDBOX_PATH", "value": "/efs/sandbox/workspace"},
    {"name": "EFS_ENABLED", "value": "true"}
]

# Check if already exists
existing_names = {v['name'] for v in env_vars}
for var in efs_vars:
    if var['name'] not in existing_names:
        env_vars.append(var)
        print(f"Added: {var['name']}={var['value']}")
    else:
        # Update existing
        for v in env_vars:
            if v['name'] == var['name']:
                v['value'] = var['value']
                print(f"Updated: {var['name']}={var['value']}")

# Remove fields that can't be in register-task-definition
for field in ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes',
              'compatibilities', 'registeredAt', 'registeredBy']:
    task_def.pop(field, None)

# Save to file
with open('/tmp/new-task-def.json', 'w') as f:
    json.dump(task_def, f, indent=2)

print("\nRegistering new task definition...")
output = run_aws('ecs register-task-definition --cli-input-json file:///tmp/new-task-def.json --query "taskDefinition.taskDefinitionArn" --output text')
print(f"New task definition: {output.strip()}")

print("\nUpdating ECS service...")
output = run_aws('ecs update-service --cluster bharatbuild-cluster --service bharatbuild-backend --task-definition bharatbuild-backend --force-new-deployment --query "service.taskDefinition" --output text')
print(f"Service updated with: {output.strip()}")

print("\nDone! EFS environment variables added.")
