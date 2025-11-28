"""
Autonomous VM Recovery Agent
Handles complete VM recovery workflow: Start VM → Wait for boot → Restart services
"""
import os
import sys
import subprocess
import time
import tempfile
import shutil
from typing import Any, Dict, List, Optional
from pathlib import Path
import httpx
import structlog

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent

logger = structlog.get_logger()


class AutonomousVMRecovery(BaseAgent):
    """Agent for autonomous VM recovery using Terraform and Ansible"""

    def __init__(self):
        super().__init__(agent_name="AutonomousVMRecovery", agent_type="infrastructure_recovery")

        # Configuration
        self.project_id = os.getenv("GCP_PROJECT_ID", "agent-ai-test-461120")
        self.credentials_path = os.getenv("GCP_CREDENTIALS_PATH", "./gcp-service-account-key.json")
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_repo = "sam2881/test_01"

        # Paths
        self.workspace_dir = Path("/tmp/agent_workspace")
        self.scripts_dir = self.workspace_dir / "automation_scripts"

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate recovery task input"""
        required = ["vm_name", "zone"]
        return all(k in task for k in required)

    def clone_automation_scripts(self) -> bool:
        """Clone automation scripts from GitHub repo"""
        try:
            logger.info("cloning_automation_scripts", repo=self.github_repo)

            # Clean workspace
            if self.workspace_dir.exists():
                shutil.rmtree(self.workspace_dir)
            self.workspace_dir.mkdir(parents=True)

            # Clone repo
            clone_cmd = [
                "git", "clone",
                f"https://github.com/{self.github_repo}.git",
                str(self.workspace_dir)
            ]

            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info("scripts_cloned_successfully", path=str(self.workspace_dir))

                # Check if automation_scripts directory exists
                if not self.scripts_dir.exists():
                    logger.warning("automation_scripts_not_found_in_repo")
                    # Copy from local installation
                    local_scripts = Path(__file__).parent.parent.parent.parent / "automation_scripts"
                    if local_scripts.exists():
                        shutil.copytree(local_scripts, self.scripts_dir)
                        logger.info("copied_scripts_from_local", path=str(local_scripts))
                    else:
                        logger.error("automation_scripts_not_available")
                        return False

                return True
            else:
                logger.error("git_clone_failed", error=result.stderr)
                return False

        except Exception as e:
            logger.error("clone_error", error=str(e))
            return False

    def start_vm_with_terraform(self, vm_name: str, zone: str) -> Dict[str, Any]:
        """Start GCP VM using Terraform"""
        try:
            logger.info("starting_vm_with_terraform", vm_name=vm_name, zone=zone)

            terraform_dir = self.scripts_dir / "terraform"
            if not terraform_dir.exists():
                return {
                    "success": False,
                    "error": "Terraform scripts not found"
                }

            # Copy credentials file
            creds_src = Path(self.credentials_path)
            if creds_src.exists():
                shutil.copy(creds_src, terraform_dir / "gcp-service-account-key.json")

            # Initialize Terraform
            init_cmd = ["terraform", "init"]
            result = subprocess.run(
                init_cmd,
                cwd=terraform_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error("terraform_init_failed", error=result.stderr)
                return {"success": False, "error": "Terraform init failed", "details": result.stderr}

            # Apply Terraform (use simple version with gcloud)
            apply_cmd = [
                "terraform", "apply",
                "-auto-approve",
                f"-var=project_id={self.project_id}",
                f"-var=zone={zone}",
                f"-var=vm_name={vm_name}",
                "-var=credentials_file=./gcp-service-account-key.json"
            ]

            # Use the simple terraform file
            result = subprocess.run(
                apply_cmd,
                cwd=terraform_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "TF_VAR_project_id": self.project_id}
            )

            if result.returncode == 0:
                logger.info("vm_started_successfully", vm_name=vm_name)

                # Parse outputs
                output_cmd = ["terraform", "output", "-json"]
                output_result = subprocess.run(
                    output_cmd,
                    cwd=terraform_dir,
                    capture_output=True,
                    text=True
                )

                import json
                outputs = {}
                if output_result.returncode == 0:
                    try:
                        outputs = json.loads(output_result.stdout)
                    except:
                        pass

                return {
                    "success": True,
                    "vm_name": vm_name,
                    "zone": zone,
                    "outputs": outputs,
                    "terraform_output": result.stdout
                }
            else:
                logger.error("terraform_apply_failed", error=result.stderr)
                return {
                    "success": False,
                    "error": "Terraform apply failed",
                    "details": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Terraform operation timed out"}
        except Exception as e:
            logger.error("terraform_error", error=str(e))
            return {"success": False, "error": str(e)}

    def get_vm_ip(self, vm_name: str, zone: str) -> Optional[str]:
        """Get VM external IP using gcloud"""
        try:
            cmd = [
                "gcloud", "compute", "instances", "describe",
                vm_name,
                f"--zone={zone}",
                f"--project={self.project_id}",
                "--format=get(networkInterfaces[0].accessConfigs[0].natIP)"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "GOOGLE_APPLICATION_CREDENTIALS": self.credentials_path}
            )

            if result.returncode == 0:
                ip = result.stdout.strip()
                logger.info("vm_ip_retrieved", vm_name=vm_name, ip=ip)
                return ip
            else:
                logger.error("get_ip_failed", error=result.stderr)
                return None

        except Exception as e:
            logger.error("get_ip_error", error=str(e))
            return None

    def wait_for_vm_ready(self, vm_ip: str, timeout: int = 300) -> bool:
        """Wait for VM to be SSH accessible"""
        logger.info("waiting_for_vm", ip=vm_ip, timeout=timeout)

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try SSH connection
                cmd = [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=5",
                    f"samrattidke600@{vm_ip}",
                    "echo 'VM Ready'"
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    logger.info("vm_ready", ip=vm_ip)
                    return True

            except:
                pass

            time.sleep(10)
            logger.debug("vm_not_ready_yet", ip=vm_ip, elapsed=int(time.time() - start_time))

        logger.error("vm_wait_timeout", ip=vm_ip)
        return False

    def restart_nginx_with_ansible(self, vm_name: str, vm_ip: str) -> Dict[str, Any]:
        """Restart Nginx on VM using Ansible"""
        try:
            logger.info("restarting_nginx_with_ansible", vm=vm_name, ip=vm_ip)

            ansible_dir = self.scripts_dir / "ansible"
            if not ansible_dir.exists():
                return {"success": False, "error": "Ansible scripts not found"}

            # Create dynamic inventory
            inventory_content = f"""[target_vm]
{vm_name} ansible_host={vm_ip} ansible_user=samrattidke600

[target_vm:vars]
ansible_ssh_private_key_file=~/.ssh/google_compute_engine
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
"""
            inventory_path = ansible_dir / "inventory.ini"
            inventory_path.write_text(inventory_content)

            # Run install playbook first (to ensure Nginx is installed)
            install_cmd = [
                "ansible-playbook",
                "-i", str(inventory_path),
                str(ansible_dir / "install_nginx.yml"),
                "-v"
            ]

            install_result = subprocess.run(
                install_cmd,
                cwd=ansible_dir,
                capture_output=True,
                text=True,
                timeout=300
            )

            logger.info("nginx_install_completed", rc=install_result.returncode)

            # Run restart playbook
            restart_cmd = [
                "ansible-playbook",
                "-i", str(inventory_path),
                str(ansible_dir / "restart_nginx.yml"),
                "-v"
            ]

            restart_result = subprocess.run(
                restart_cmd,
                cwd=ansible_dir,
                capture_output=True,
                text=True,
                timeout=180
            )

            if restart_result.returncode == 0:
                logger.info("nginx_restarted_successfully", vm=vm_name)
                return {
                    "success": True,
                    "vm_name": vm_name,
                    "vm_ip": vm_ip,
                    "ansible_output": restart_result.stdout
                }
            else:
                logger.error("ansible_restart_failed", error=restart_result.stderr)
                return {
                    "success": False,
                    "error": "Ansible restart failed",
                    "details": restart_result.stderr,
                    "stdout": restart_result.stdout
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Ansible operation timed out"}
        except Exception as e:
            logger.error("ansible_error", error=str(e))
            return {"success": False, "error": str(e)}

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process autonomous VM recovery task"""
        vm_name = task["vm_name"]
        zone = task.get("zone", "us-central1-a")
        restart_services = task.get("restart_services", True)

        logger.info("starting_autonomous_recovery", vm=vm_name, zone=zone)

        workflow_steps = []

        # Step 1: Clone automation scripts
        workflow_steps.append({"step": "clone_scripts", "status": "starting"})
        if not self.clone_automation_scripts():
            return {
                "success": False,
                "error": "Failed to clone automation scripts",
                "workflow_steps": workflow_steps
            }
        workflow_steps[-1]["status"] = "completed"

        # Step 2: Start VM with Terraform
        workflow_steps.append({"step": "start_vm_terraform", "status": "starting"})
        terraform_result = self.start_vm_with_terraform(vm_name, zone)
        workflow_steps[-1]["result"] = terraform_result

        if not terraform_result.get("success"):
            workflow_steps[-1]["status"] = "failed"
            return {
                "success": False,
                "error": "Failed to start VM with Terraform",
                "workflow_steps": workflow_steps
            }
        workflow_steps[-1]["status"] = "completed"

        # Step 3: Get VM IP
        workflow_steps.append({"step": "get_vm_ip", "status": "starting"})
        vm_ip = self.get_vm_ip(vm_name, zone)
        workflow_steps[-1]["vm_ip"] = vm_ip

        if not vm_ip:
            workflow_steps[-1]["status"] = "failed"
            return {
                "success": False,
                "error": "Failed to retrieve VM IP",
                "workflow_steps": workflow_steps
            }
        workflow_steps[-1]["status"] = "completed"

        # Step 4: Wait for VM to be ready
        workflow_steps.append({"step": "wait_for_vm_ready", "status": "starting"})
        if not self.wait_for_vm_ready(vm_ip):
            workflow_steps[-1]["status"] = "failed"
            return {
                "success": False,
                "error": "VM did not become ready within timeout",
                "workflow_steps": workflow_steps,
                "vm_ip": vm_ip
            }
        workflow_steps[-1]["status"] = "completed"

        # Step 5: Restart services with Ansible (if requested)
        if restart_services:
            workflow_steps.append({"step": "restart_nginx_ansible", "status": "starting"})
            ansible_result = self.restart_nginx_with_ansible(vm_name, vm_ip)
            workflow_steps[-1]["result"] = ansible_result

            if not ansible_result.get("success"):
                workflow_steps[-1]["status"] = "failed"
                return {
                    "success": False,
                    "error": "Failed to restart Nginx",
                    "workflow_steps": workflow_steps,
                    "vm_ip": vm_ip,
                    "vm_started": True
                }
            workflow_steps[-1]["status"] = "completed"

        # Success!
        return {
            "success": True,
            "vm_name": vm_name,
            "vm_ip": vm_ip,
            "zone": zone,
            "workflow_steps": workflow_steps,
            "message": f"VM {vm_name} successfully recovered and services restarted"
        }
