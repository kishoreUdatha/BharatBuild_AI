"""
Test Complex Fullstack Application - Java Spring Boot + React

Run: python test_fullstack_complex.py
"""

import asyncio
import os
from pathlib import Path

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

print(f"[OK] API key loaded")

from anthropic import AsyncAnthropic

PROMPTS_DIR = Path(__file__).parent / "app" / "config" / "prompts"


def load_prompt(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


async def test_complex_planner():
    """Test planner with complex fullstack app."""
    print("\n" + "=" * 70)
    print("TEST: Complex Fullstack Planner - Hospital Management System")
    print("=" * 70)

    core = load_prompt("planner_core.txt")
    java = load_prompt("planner_java.txt")
    react = load_prompt("planner_react.txt")

    system_prompt = core + "\n\n" + java + "\n\n" + react
    print(f"[OK] Combined prompt: ~{len(system_prompt)//4} tokens")

    client = AsyncAnthropic()

    # Complex fullstack request
    user_prompt = """Create a Hospital Management System with:

BACKEND (Spring Boot + Java):
- Patient entity: name, email, phone, dateOfBirth, gender (enum: MALE/FEMALE/OTHER), bloodGroup, address
- Doctor entity: name, email, specialization, qualification, experienceYears, consultationFee (BigDecimal)
- Appointment entity: patient (relationship), doctor (relationship), appointmentDate, status (enum: SCHEDULED/COMPLETED/CANCELLED), notes
- Department entity: name, description, headDoctor (relationship)

FRONTEND (React + TypeScript + Tailwind):
- Dashboard with statistics
- Patient list with search/filter
- Doctor list with specialization filter
- Appointment booking form
- Appointment calendar view

Use Spring Boot 3.x with PostgreSQL and React with Vite."""

    print(f"\n[Calling Claude for complex fullstack plan...]")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    output = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    print(f"[OK] Response: {len(output)} chars, {tokens} tokens")

    # Check for all entities in entity_specs
    checks = {
        "<plan>": "<plan>" in output,
        "<entity_specs>": "<entity_specs>" in output,
        "Patient entity": "ENTITY: Patient" in output,
        "Doctor entity": "ENTITY: Doctor" in output,
        "Appointment entity": "ENTITY: Appointment" in output,
        "Department entity": "ENTITY: Department" in output,
        "Gender enum": "ENUM: Gender" in output or "gender:" in output.lower(),
        "AppointmentStatus enum": "ENUM:" in output and "Status" in output,
        "Relationships defined": "relationship" in output.lower() or "patient:" in output.lower(),
        "Frontend files": "frontend/" in output,
        "Backend files": "backend/" in output,
        "<files>": "<files>" in output,
    }

    print("\n[Checking plan completeness...]")
    passed = 0
    for check, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")
        if result:
            passed += 1

    # Extract and show entity_specs
    if "<entity_specs>" in output:
        start = output.find("<entity_specs>")
        end = output.find("</entity_specs>") + len("</entity_specs>")
        if start >= 0 and end > start:
            print("\n[Generated Entity Specs:]")
            print("-" * 50)
            print(output[start:end][:3000])
            print("-" * 50)

    # Count files
    file_count = output.count("<file path=")
    print(f"\n[Files planned: {file_count}]")

    return passed >= 8, output  # Pass if 8+ checks pass


async def test_complex_service():
    """Test writer with complex service that has relationships."""
    print("\n" + "=" * 70)
    print("TEST: Complex Service - AppointmentService with relationships")
    print("=" * 70)

    core = load_prompt("writer_core.txt")
    java = load_prompt("writer_java.txt")

    system_prompt = core + "\n\n" + java
    print(f"[OK] Combined prompt: ~{len(system_prompt)//4} tokens")

    client = AsyncAnthropic()

    user_prompt = """Generate this file:

FILE TO GENERATE: backend/src/main/java/com/hospital/service/AppointmentService.java

ENTITY_SPECS:
ENTITY: Appointment
TABLE: appointments
FIELDS:
  - id: Long (primary key)
  - patient: Patient (ManyToOne relationship)
  - doctor: Doctor (ManyToOne relationship)
  - appointmentDate: LocalDateTime
  - status: AppointmentStatus (enum)
  - notes: String
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/appointments

ENTITY: Patient
FIELDS:
  - id: Long
  - name: String
  - email: String

ENTITY: Doctor
FIELDS:
  - id: Long
  - name: String
  - specialization: String

ENUM: AppointmentStatus
VALUES: SCHEDULED, COMPLETED, CANCELLED

FILES ALREADY CREATED:
- backend/src/main/java/com/hospital/model/Appointment.java
- backend/src/main/java/com/hospital/model/Patient.java
- backend/src/main/java/com/hospital/model/Doctor.java
- backend/src/main/java/com/hospital/model/enums/AppointmentStatus.java
- backend/src/main/java/com/hospital/dto/AppointmentDto.java
- backend/src/main/java/com/hospital/repository/AppointmentRepository.java
- backend/src/main/java/com/hospital/repository/PatientRepository.java
- backend/src/main/java/com/hospital/repository/DoctorRepository.java

Generate the complete service with:
- CRUD operations
- Find appointments by patient
- Find appointments by doctor
- Find appointments by date range
- Update appointment status
- NO LOMBOK - explicit getters/setters in convertToDto/convertToEntity"""

    print(f"\n[Calling Claude for complex service...]")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    output = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    print(f"[OK] Response: {len(output)} chars, {tokens} tokens")

    checks = {
        "<file path=": "<file path=" in output,
        "jakarta imports": "jakarta" in output,
        "NO Lombok": "@Data" not in output and "import lombok" not in output,
        "@Service annotation": "@Service" in output,
        "@Transactional": "@Transactional" in output,
        "Constructor injection": "public AppointmentService(" in output,
        "findAll method": "findAll" in output,
        "findById method": "findById" in output,
        "create method": "create(" in output,
        "update method": "update(" in output,
        "delete method": "delete(" in output,
        "findByPatient": "findByPatient" in output or "ByPatient" in output,
        "findByDoctor": "findByDoctor" in output or "ByDoctor" in output,
        "convertToDto": "convertToDto" in output,
        "convertToEntity": "convertToEntity" in output,
        "Uses getPatient()": "getPatient()" in output,
        "Uses getDoctor()": "getDoctor()" in output,
        "Uses getStatus()": "getStatus()" in output,
    }

    print("\n[Checking service code...]")
    passed = 0
    for check, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")
        if result:
            passed += 1

    # Show code snippet
    if "<file" in output:
        print("\n[Generated Service (first 100 lines):]")
        print("-" * 50)
        start = output.find("<file")
        end = output.find("</file>") + len("</file>")
        code = output[start:end]
        lines = code.split("\n")[:100]
        for i, line in enumerate(lines, 1):
            print(f"{i:3}: {line}")
        print("-" * 50)

    return passed >= 14  # Pass if 14+ checks pass


async def test_complex_react_page():
    """Test writer with complex React page with API calls and state."""
    print("\n" + "=" * 70)
    print("TEST: Complex React Page - Appointment Booking Form")
    print("=" * 70)

    core = load_prompt("writer_core.txt")
    react = load_prompt("writer_react.txt")

    system_prompt = core + "\n\n" + react
    print(f"[OK] Combined prompt: ~{len(system_prompt)//4} tokens")

    client = AsyncAnthropic()

    user_prompt = """Generate this file:

FILE TO GENERATE: frontend/src/pages/BookAppointment.tsx

TYPES (from types/index.ts):
interface Patient {
  id: number;
  name: string;
  email: string;
  phone: string;
}

interface Doctor {
  id: number;
  name: string;
  specialization: string;
  consultationFee: number;
}

interface AppointmentCreate {
  patientId: number;
  doctorId: number;
  appointmentDate: string;
  notes?: string;
}

interface PageResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  number: number;
  size: number;
}

FILES ALREADY CREATED:
- frontend/src/types/index.ts (exports: Patient, Doctor, AppointmentCreate, PageResponse)
- frontend/src/lib/api.ts (exports: api with get, post methods)
- frontend/src/components/ui/Button.tsx
- frontend/src/components/ui/Input.tsx
- frontend/src/components/ui/Select.tsx
- frontend/src/components/layout/Header.tsx

Create a booking form page with:
- Dropdown to select patient (fetch from /api/patients)
- Dropdown to select doctor (fetch from /api/doctors)
- Date/time picker for appointment
- Notes textarea
- Submit button that POSTs to /api/appointments
- Loading states and error handling
- Success message after booking
- Use Tailwind with glass effects and gradients
- Theme: healthcare (cyan + teal)"""

    print(f"\n[Calling Claude for complex React page...]")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    output = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    print(f"[OK] Response: {len(output)} chars, {tokens} tokens")

    checks = {
        "<file path=": "<file path=" in output,
        "NO import React from": "import React from" not in output,
        "useState hook": "useState" in output,
        "useEffect hook": "useEffect" in output,
        "export default": "export default" in output,
        "Fetches patients": "/api/patients" in output or "patients" in output.lower(),
        "Fetches doctors": "/api/doctors" in output or "doctors" in output.lower(),
        "Form submission": "submit" in output.lower() or "handleSubmit" in output,
        "Loading state": "loading" in output.lower() or "Loading" in output,
        "Error handling": "error" in output.lower() or "Error" in output,
        "Tailwind classes": "className=" in output,
        "Uses Patient type": "Patient" in output,
        "Uses Doctor type": "Doctor" in output,
        "Healthcare colors (cyan/teal)": "cyan" in output or "teal" in output,
    }

    print("\n[Checking React page...]")
    passed = 0
    for check, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")
        if result:
            passed += 1

    return passed >= 11  # Pass if 11+ checks pass


async def main():
    print("=" * 70)
    print("COMPLEX FULLSTACK APPLICATION TEST")
    print("Testing: Hospital Management System (Spring Boot + React)")
    print("=" * 70)

    results = {}

    # Test 1: Complex Planner
    planner_passed, plan_output = await test_complex_planner()
    results["Planner (Complex Fullstack)"] = planner_passed

    # Test 2: Complex Service
    results["Writer (Complex Service)"] = await test_complex_service()

    # Test 3: Complex React Page
    results["Writer (Complex React Page)"] = await test_complex_react_page()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY - Complex Fullstack Application")
    print("=" * 70)

    all_passed = True
    for test, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] All complex tests passed!")
        print("Simplified prompts handle complex fullstack applications correctly.")
    else:
        print("[WARNING] Some tests failed. Review output above.")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
