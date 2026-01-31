"""
Hospital Management System - Full Build Test
Tests the complete flow: Planner -> Writer -> Maven Build
"""
import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

# Load API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
for env_file in [".env.test", ".env"]:
    if api_key:
        break
    env_path = Path(__file__).parent / env_file
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                os.environ["ANTHROPIC_API_KEY"] = api_key
                break

if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not found")
    exit(1)

from anthropic import AsyncAnthropic

PROMPTS_DIR = Path(__file__).parent / "app" / "config" / "prompts"
OUTPUT_DIR = Path(__file__).parent / "test_hospital_project"


def load_prompt(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def extract_file_content(response: str) -> str:
    match = re.search(r'<file[^>]*>(.*?)</file>', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response


# Hospital Management Entity Specs
ENTITY_SPECS = """
<entity_specs>
ENTITY: Patient
TABLE: patients
FIELDS:
  - id: Long (primary key)
  - name: String
  - email: String
  - phone: String
  - dateOfBirth: LocalDate
  - gender: Gender
  - bloodGroup: String
  - address: String
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/patients
RELATIONS:
  - appointments: OneToMany (Appointment)

ENTITY: Doctor
TABLE: doctors
FIELDS:
  - id: Long (primary key)
  - name: String
  - email: String
  - specialization: String
  - qualification: String
  - experienceYears: Integer
  - consultationFee: BigDecimal
  - departmentId: Long (foreign key to Department)
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/doctors
RELATIONS:
  - appointments: OneToMany (Appointment)
  - department: ManyToOne (Department)

ENTITY: Appointment
TABLE: appointments
FIELDS:
  - id: Long (primary key)
  - patientId: Long (foreign key to Patient)
  - doctorId: Long (foreign key to Doctor)
  - appointmentDate: LocalDateTime
  - status: AppointmentStatus
  - notes: String (optional)
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/appointments
RELATIONS:
  - patient: ManyToOne (Patient)
  - doctor: ManyToOne (Doctor)

ENTITY: Department
TABLE: departments
FIELDS:
  - id: Long (primary key)
  - name: String
  - description: String
  - headDoctorId: Long (foreign key to Doctor) (optional)
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/departments
RELATIONS:
  - doctors: OneToMany (Doctor)

ENUM: Gender
VALUES: MALE, FEMALE, OTHER

ENUM: AppointmentStatus
VALUES: SCHEDULED, COMPLETED, CANCELLED
</entity_specs>
"""

# Files to generate (dependency order)
FILES = [
    ("pom.xml", "Maven POM with Spring Boot 3.x, PostgreSQL, NO security dependencies"),
    ("src/main/resources/application.yml", "Spring Boot config for PostgreSQL"),
    ("src/main/java/com/hospital/model/enums/Gender.java", "Gender enum: MALE, FEMALE, OTHER"),
    ("src/main/java/com/hospital/model/enums/AppointmentStatus.java", "AppointmentStatus enum: SCHEDULED, COMPLETED, CANCELLED"),
    ("src/main/java/com/hospital/model/Patient.java", "Patient entity with all fields from entity_specs"),
    ("src/main/java/com/hospital/model/Doctor.java", "Doctor entity with department relationship"),
    ("src/main/java/com/hospital/model/Appointment.java", "Appointment entity with patient/doctor relationships"),
    ("src/main/java/com/hospital/model/Department.java", "Department entity with doctors relationship"),
    ("src/main/java/com/hospital/dto/PatientDto.java", "Patient DTO matching entity fields"),
    ("src/main/java/com/hospital/dto/DoctorDto.java", "Doctor DTO matching entity fields"),
    ("src/main/java/com/hospital/dto/AppointmentDto.java", "Appointment DTO matching entity fields"),
    ("src/main/java/com/hospital/dto/DepartmentDto.java", "Department DTO matching entity fields"),
    ("src/main/java/com/hospital/repository/PatientRepository.java", "Patient JpaRepository"),
    ("src/main/java/com/hospital/repository/DoctorRepository.java", "Doctor JpaRepository"),
    ("src/main/java/com/hospital/repository/AppointmentRepository.java", "Appointment JpaRepository with findByPatientId, findByDoctorId"),
    ("src/main/java/com/hospital/repository/DepartmentRepository.java", "Department JpaRepository"),
    ("src/main/java/com/hospital/service/PatientService.java", "Patient service with CRUD operations"),
    ("src/main/java/com/hospital/service/DoctorService.java", "Doctor service with CRUD operations"),
    ("src/main/java/com/hospital/service/AppointmentService.java", "Appointment service with CRUD and relationship queries"),
    ("src/main/java/com/hospital/service/DepartmentService.java", "Department service with CRUD operations"),
    ("src/main/java/com/hospital/controller/PatientController.java", "Patient REST controller"),
    ("src/main/java/com/hospital/controller/DoctorController.java", "Doctor REST controller"),
    ("src/main/java/com/hospital/controller/AppointmentController.java", "Appointment REST controller"),
    ("src/main/java/com/hospital/controller/DepartmentController.java", "Department REST controller"),
    ("src/main/java/com/hospital/HospitalManagementApplication.java", "Main Spring Boot application class"),
    ("Dockerfile", "Multi-stage Dockerfile with Maven build"),
]


async def generate_file(client, system_prompt: str, file_path: str, description: str,
                        generated_files: Dict[str, str], entity_specs: str) -> str:
    """Generate a single file with cross-file context."""

    # Build context from generated files - FULL content for critical dependencies
    context_parts = []
    full_context_parts = []  # For Services when generating Controllers

    for path, content in generated_files.items():
        if path.endswith('.java'):
            # For Controllers: include FULL Service code (critical for method names)
            if 'Controller' in file_path and 'Service' in path and 'Impl' not in path:
                # Extract entity name from controller (e.g., PatientController -> Patient)
                controller_entity = file_path.split('/')[-1].replace('Controller.java', '')
                service_entity = path.split('/')[-1].replace('Service.java', '')
                if controller_entity == service_entity:
                    full_context_parts.append(f"// FULL SERVICE - USE ONLY THESE METHODS:\n// {path}\n{content}")
                else:
                    context_parts.append(f"// {path}\n{content[:1500]}")
            # For Services: include full Repository
            elif 'Service' in file_path and 'Repository' in path:
                service_entity = file_path.split('/')[-1].replace('Service.java', '')
                repo_entity = path.split('/')[-1].replace('Repository.java', '')
                if service_entity == repo_entity:
                    full_context_parts.append(f"// FULL REPOSITORY - USE ONLY THESE METHODS:\n// {path}\n{content}")
                else:
                    context_parts.append(f"// {path}\n{content[:1000]}")
            # For DTOs: include full Entity
            elif 'dto' in file_path.lower() and 'model' in path and 'enum' not in path.lower():
                dto_entity = file_path.split('/')[-1].replace('Dto.java', '')
                model_entity = path.split('/')[-1].replace('.java', '')
                if dto_entity == model_entity:
                    full_context_parts.append(f"// FULL ENTITY - MATCH THESE FIELDS:\n// {path}\n{content}")
            # Include enums and models as partial context
            elif 'model' in path or 'dto' in path:
                context_parts.append(f"// {path}\n{content[:1000]}")

    # Combine: full context first, then partial
    all_context = full_context_parts + context_parts[-3:]
    context = "\n\n".join(all_context) if all_context else ""

    # Build specific rules based on file type
    specific_rules = ""
    if 'Controller' in file_path:
        specific_rules = """
⚠️ CONTROLLER RULES (CRITICAL):
- ONLY call methods that exist in the Service class provided below
- DO NOT invent methods like getXxxByName(), searchXxx(), countXxx() unless they exist in Service
- Standard methods: findAll(), findById(), create(), update(), delete()
- Check the Service code below for exact method signatures"""
    elif 'Service' in file_path and 'Impl' not in file_path:
        specific_rules = """
⚠️ SERVICE RULES (CRITICAL):
- ONLY call methods that exist in the Repository interface provided below
- Standard JpaRepository methods: findAll(), findById(), save(), deleteById(), existsById()
- Custom methods must be defined in Repository first"""

    user_prompt = f"""Generate: {file_path}
Description: {description}

{entity_specs}

CRITICAL RULES:
- Use EXACT field names from entity_specs above
- NO Lombok annotations
- NO spring-boot-starter-security
- Spring Boot 3.x uses jakarta.* (not javax.*)
- Enums are in com.hospital.model.enums package
{specific_rules}

{f"EXISTING FILES (USE ONLY METHODS DEFINED HERE):" + chr(10) + context if context else ""}

Output ONLY the file content inside <file path="{file_path}">...</file> tags."""

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return extract_file_content(response.content[0].text)


async def main():
    print("=" * 70)
    print("HOSPITAL MANAGEMENT SYSTEM - FULL BUILD TEST")
    print("=" * 70)

    client = AsyncAnthropic()
    generated_files: Dict[str, str] = {}

    # Load prompts
    core = load_prompt("writer_core.txt")
    java = load_prompt("writer_java.txt")
    system_prompt = core + "\n\n" + java

    print(f"\n[PHASE 1] Generating {len(FILES)} files...")

    for i, (file_path, description) in enumerate(FILES):
        print(f"  [{i+1}/{len(FILES)}] {file_path.split('/')[-1]}")
        content = await generate_file(client, system_prompt, file_path, description,
                                      generated_files, ENTITY_SPECS)
        generated_files[file_path] = content

    # Clean and create output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    print(f"\n[PHASE 2] Saving to {OUTPUT_DIR}...")

    for file_path, content in generated_files.items():
        full_path = OUTPUT_DIR / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        print(f"  Saved: {file_path.split('/')[-1]}")

    # Check for security references (should be none)
    print(f"\n[PHASE 3] Checking for unwanted security code...")
    security_found = False
    for file_path, content in generated_files.items():
        if 'security' in content.lower() and 'spring-boot-starter-security' in content.lower():
            print(f"  [WARN] Security dependency in {file_path}")
            security_found = True
        if 'SecurityConfig' in content or 'JwtService' in content:
            print(f"  [WARN] Security class reference in {file_path}")
            security_found = True

    if not security_found:
        print("  [OK] No unwanted security code found")

    # Run Maven build
    print(f"\n[PHASE 4] Running Maven build in Docker...")

    # Convert Windows path to Docker-compatible path
    project_path = str(OUTPUT_DIR.absolute()).replace('\\', '/')
    if len(project_path) > 1 and project_path[1] == ':':
        project_path = '/' + project_path[0].lower() + project_path[2:]

    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{project_path}:/app",
        "-w", "/app",
        "maven:3.9-eclipse-temurin-17-alpine",
        "mvn", "compile", "-q"
    ]

    print(f"  Running: docker run maven:3.9-eclipse-temurin-17-alpine mvn compile")

    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("\n" + "=" * 70)
            print("[SUCCESS] Maven build completed - 0 errors!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("[FAILED] Maven build failed")
            print("=" * 70)

            # Count and show errors
            output = result.stdout + result.stderr
            error_lines = [l for l in output.split('\n') if '[ERROR]' in l]
            print(f"\nCompilation errors: {len(error_lines)}")

            # Show last 80 lines of output
            lines = output.strip().split('\n')
            print("\n[Build Output (last 80 lines)]")
            print("-" * 50)
            for line in lines[-80:]:
                print(line)

    except subprocess.TimeoutExpired:
        print("\n[TIMEOUT] Maven build timed out after 5 minutes")
    except Exception as e:
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    asyncio.run(main())
