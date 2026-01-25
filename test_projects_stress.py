#!/usr/bin/env python3
"""
Stress test helper: Create 20 projects quickly to validate no corruption.
Run: python test_projects_stress.py
"""

import sys
import tempfile
from pathlib import Path

import projects as projects_module

def test_stress_create_projects():
    """Create 20 projects rapidly and verify they're all saved correctly."""
    test_owner_id = "acct:sub:test123456"
    tmp_dir = tempfile.mkdtemp(prefix="chronoplan-projects-stress-")
    tmp_path = Path(tmp_dir)

    # Isolate project storage away from repo artifacts/.
    projects_module.PROJECTS_PATH = tmp_path / "projects.json"
    projects_module.PROJECTS_DIR = tmp_path / "projects"
    projects_module.PROJECTS_LOCK_PATH = tmp_path / "projects.json.lock"
    
    print(f"[*] Creating 20 projects with owner_id={test_owner_id}...")
    
    for i in range(20):
        project = projects_module.create_project(f"Stress Test Project {i+1}", owner_id=test_owner_id)
        if not project:
            print(f"[!] Failed to create project {i+1}")
            return False
        print(f"[+] Created project {i+1}: {project['id']}")
    
    print(f"\n[*] Listing all projects for owner...")
    projects = projects_module.list_projects(owner_id=test_owner_id)
    
    if len(projects) != 20:
        print(f"[!] Expected 20 projects, got {len(projects)}")
        print(f"[!] Projects: {projects}")
        return False
    
    print(f"[+] All 20 projects found: OK")
    
    # Verify all project IDs are unique
    project_ids = {p.get("id") for p in projects}
    if len(project_ids) != 20:
        print(f"[!] Duplicate project IDs found!")
        return False
    
    print(f"[+] All project IDs unique: OK")
    
    # Verify no corrupted entries
    for i, p in enumerate(projects, 1):
        if not p.get("id") or not p.get("owner_id") or not p.get("name"):
            print(f"[!] Project {i} is corrupted: {p}")
            return False
    
    print(f"[+] No corrupted entries: OK")
    print(f"\n[+] STRESS TEST PASSED!")
    return True

if __name__ == "__main__":
    success = test_stress_create_projects()
    sys.exit(0 if success else 1)
