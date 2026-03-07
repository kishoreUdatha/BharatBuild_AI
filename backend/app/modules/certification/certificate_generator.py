"""
Skill Certification Generator Module
Generates certificates for students based on project completion, skill attainment, and OBE metrics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import uuid
import hashlib
import json
import io
import base64


class CertificateType(str, Enum):
    PROJECT_COMPLETION = "project_completion"
    SKILL_PROFICIENCY = "skill_proficiency"
    COURSE_COMPLETION = "course_completion"
    INTERNSHIP = "internship"
    HACKATHON = "hackathon"
    WORKSHOP = "workshop"
    ASSESSMENT = "assessment"


class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class VerificationStatus(str, Enum):
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


@dataclass
class Skill:
    """Represents a skill with proficiency level"""
    name: str
    category: str
    level: SkillLevel
    hours_practiced: int = 0
    projects_applied: int = 0
    assessment_score: Optional[float] = None


@dataclass
class CourseOutcomeAttainment:
    """CO attainment record"""
    co_id: str
    co_description: str
    target_level: float
    achieved_level: float
    attainment_percentage: float
    bloom_level: str


@dataclass
class ProgramOutcomeMapping:
    """PO mapping from project"""
    po_id: str
    po_description: str
    contribution_percentage: float
    evidence: List[str] = field(default_factory=list)


@dataclass
class CertificateData:
    """Data structure for certificate content"""
    certificate_id: str
    certificate_type: CertificateType
    student_name: str
    student_id: str
    institution_name: str
    department: str

    # Project details
    project_title: Optional[str] = None
    project_description: Optional[str] = None
    project_duration_weeks: int = 0
    project_repository: Optional[str] = None

    # Skills and technologies
    skills: List[Skill] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)

    # OBE metrics
    course_outcomes: List[CourseOutcomeAttainment] = field(default_factory=list)
    program_outcomes: List[ProgramOutcomeMapping] = field(default_factory=list)
    overall_attainment: float = 0.0

    # Assessment
    grade: Optional[str] = None
    score: Optional[float] = None
    percentile: Optional[float] = None

    # Timestamps and verification
    issue_date: datetime = field(default_factory=datetime.now)
    expiry_date: Optional[datetime] = None
    verification_code: str = ""
    verification_url: str = ""

    # Additional metadata
    issuer_name: str = "BharatBuild AI"
    issuer_signature: Optional[str] = None
    faculty_name: Optional[str] = None
    faculty_designation: Optional[str] = None

    # QR code for verification
    qr_code_data: Optional[str] = None


@dataclass
class CertificateTemplate:
    """Template for certificate generation"""
    template_id: str
    template_name: str
    certificate_type: CertificateType
    html_template: str
    css_styles: str
    header_image: Optional[str] = None
    footer_image: Optional[str] = None
    signature_positions: List[Dict] = field(default_factory=list)
    watermark: Optional[str] = None


class SkillCertificationGenerator:
    """
    Generates skill certificates with OBE integration
    Features:
    - Auto-generate certificates from project data
    - CO-PO attainment visualization
    - Skill proficiency mapping
    - Verification QR codes
    - Multiple certificate types
    - Industry-aligned skill badges
    """

    def __init__(self):
        self.templates = self._load_default_templates()
        self.skill_categories = self._init_skill_categories()
        self.issued_certificates: Dict[str, CertificateData] = {}

    def _init_skill_categories(self) -> Dict[str, List[str]]:
        """Initialize skill categories and their constituent skills"""
        return {
            "Programming Languages": [
                "Python", "JavaScript", "TypeScript", "Java", "C++", "C#",
                "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin"
            ],
            "Frontend Development": [
                "React", "Vue.js", "Angular", "Next.js", "Svelte",
                "HTML5", "CSS3", "Tailwind CSS", "Bootstrap", "SASS"
            ],
            "Backend Development": [
                "Node.js", "Express.js", "FastAPI", "Django", "Flask",
                "Spring Boot", "ASP.NET", "Ruby on Rails", "Laravel"
            ],
            "Database": [
                "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite",
                "Oracle", "SQL Server", "Cassandra", "DynamoDB"
            ],
            "Cloud & DevOps": [
                "AWS", "Azure", "GCP", "Docker", "Kubernetes",
                "CI/CD", "Jenkins", "GitHub Actions", "Terraform", "Ansible"
            ],
            "AI/ML": [
                "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
                "TensorFlow", "PyTorch", "Scikit-learn", "Keras", "OpenCV"
            ],
            "Data Science": [
                "Data Analysis", "Data Visualization", "Statistics",
                "Pandas", "NumPy", "Matplotlib", "Tableau", "Power BI"
            ],
            "Mobile Development": [
                "React Native", "Flutter", "iOS Development", "Android Development",
                "Xamarin", "Ionic", "SwiftUI", "Jetpack Compose"
            ],
            "Cybersecurity": [
                "Network Security", "Ethical Hacking", "Cryptography",
                "OWASP", "Penetration Testing", "Security Auditing"
            ],
            "Soft Skills": [
                "Problem Solving", "Team Collaboration", "Communication",
                "Project Management", "Agile/Scrum", "Technical Writing"
            ]
        }

    def _load_default_templates(self) -> Dict[str, CertificateTemplate]:
        """Load default certificate templates"""
        return {
            CertificateType.PROJECT_COMPLETION: CertificateTemplate(
                template_id="proj_comp_001",
                template_name="Project Completion Certificate",
                certificate_type=CertificateType.PROJECT_COMPLETION,
                html_template=self._get_project_completion_template(),
                css_styles=self._get_default_css(),
                signature_positions=[
                    {"role": "Faculty Advisor", "x": 150, "y": 700},
                    {"role": "Head of Department", "x": 450, "y": 700}
                ]
            ),
            CertificateType.SKILL_PROFICIENCY: CertificateTemplate(
                template_id="skill_prof_001",
                template_name="Skill Proficiency Certificate",
                certificate_type=CertificateType.SKILL_PROFICIENCY,
                html_template=self._get_skill_proficiency_template(),
                css_styles=self._get_default_css(),
                signature_positions=[
                    {"role": "Skill Assessor", "x": 300, "y": 700}
                ]
            ),
            CertificateType.COURSE_COMPLETION: CertificateTemplate(
                template_id="course_comp_001",
                template_name="Course Completion Certificate",
                certificate_type=CertificateType.COURSE_COMPLETION,
                html_template=self._get_course_completion_template(),
                css_styles=self._get_default_css(),
                signature_positions=[
                    {"role": "Course Instructor", "x": 150, "y": 700},
                    {"role": "Dean", "x": 450, "y": 700}
                ]
            )
        }

    def generate_certificate(
        self,
        student_name: str,
        student_id: str,
        institution_name: str,
        department: str,
        certificate_type: CertificateType,
        project_data: Optional[Dict] = None,
        evaluation_result: Optional[Dict] = None,
        skills: Optional[List[Dict]] = None,
        faculty_name: Optional[str] = None
    ) -> CertificateData:
        """
        Generate a certificate based on project data and evaluation

        Args:
            student_name: Name of the student
            student_id: Student enrollment/registration ID
            institution_name: Name of the institution
            department: Department name
            certificate_type: Type of certificate to generate
            project_data: Project details including title, description, technologies
            evaluation_result: Evaluation scores and CO-PO attainment
            skills: List of skills demonstrated
            faculty_name: Name of faculty advisor

        Returns:
            CertificateData object with all certificate information
        """
        # Generate unique certificate ID
        cert_id = self._generate_certificate_id(student_id, certificate_type)

        # Generate verification code
        verification_code = self._generate_verification_code(cert_id, student_id)

        # Process skills
        processed_skills = []
        if skills:
            for skill_data in skills:
                processed_skills.append(Skill(
                    name=skill_data.get("name", ""),
                    category=self._categorize_skill(skill_data.get("name", "")),
                    level=SkillLevel(skill_data.get("level", "intermediate")),
                    hours_practiced=skill_data.get("hours", 0),
                    projects_applied=skill_data.get("projects", 1),
                    assessment_score=skill_data.get("score")
                ))

        # Process CO attainment from evaluation
        co_attainments = []
        po_mappings = []
        overall_attainment = 0.0

        if evaluation_result:
            co_data = evaluation_result.get("co_attainment", {})
            for co_id, data in co_data.items():
                co_attainments.append(CourseOutcomeAttainment(
                    co_id=co_id,
                    co_description=data.get("description", ""),
                    target_level=data.get("target", 3.0),
                    achieved_level=data.get("achieved", 0.0),
                    attainment_percentage=data.get("percentage", 0.0),
                    bloom_level=data.get("bloom_level", "L3")
                ))

            po_data = evaluation_result.get("po_mapping", {})
            for po_id, data in po_data.items():
                po_mappings.append(ProgramOutcomeMapping(
                    po_id=po_id,
                    po_description=data.get("description", ""),
                    contribution_percentage=data.get("contribution", 0.0),
                    evidence=data.get("evidence", [])
                ))

            overall_attainment = evaluation_result.get("overall_attainment", 0.0)

        # Extract technologies from project
        technologies = []
        if project_data:
            technologies = project_data.get("technologies", [])
            if not technologies and project_data.get("tech_stack"):
                technologies = project_data["tech_stack"]

        # Create certificate data
        certificate = CertificateData(
            certificate_id=cert_id,
            certificate_type=certificate_type,
            student_name=student_name,
            student_id=student_id,
            institution_name=institution_name,
            department=department,
            project_title=project_data.get("title") if project_data else None,
            project_description=project_data.get("description") if project_data else None,
            project_duration_weeks=project_data.get("duration_weeks", 0) if project_data else 0,
            project_repository=project_data.get("repository") if project_data else None,
            skills=processed_skills,
            technologies=technologies,
            course_outcomes=co_attainments,
            program_outcomes=po_mappings,
            overall_attainment=overall_attainment,
            grade=evaluation_result.get("grade") if evaluation_result else None,
            score=evaluation_result.get("score") if evaluation_result else None,
            verification_code=verification_code,
            verification_url=f"https://bharatbuild.ai/verify/{verification_code}",
            faculty_name=faculty_name,
            issue_date=datetime.now()
        )

        # Generate QR code data
        certificate.qr_code_data = self._generate_qr_data(certificate)

        # Store certificate for verification
        self.issued_certificates[cert_id] = certificate

        return certificate

    def generate_project_certificate(
        self,
        student_name: str,
        student_id: str,
        institution_name: str,
        department: str,
        project_id: str,
        project_title: str,
        project_description: str,
        technologies: List[str],
        duration_weeks: int,
        evaluation_score: float,
        grade: str,
        co_attainment: Dict[str, float],
        po_mapping: Dict[str, float],
        faculty_name: str
    ) -> CertificateData:
        """
        Convenience method to generate project completion certificate
        """
        project_data = {
            "id": project_id,
            "title": project_title,
            "description": project_description,
            "technologies": technologies,
            "duration_weeks": duration_weeks
        }

        evaluation_result = {
            "score": evaluation_score,
            "grade": grade,
            "co_attainment": {
                f"CO{i+1}": {"achieved": v, "percentage": v * 100 / 3.0}
                for i, (k, v) in enumerate(co_attainment.items())
            },
            "po_mapping": {
                f"PO{i+1}": {"contribution": v}
                for i, (k, v) in enumerate(po_mapping.items())
            },
            "overall_attainment": sum(co_attainment.values()) / len(co_attainment) if co_attainment else 0
        }

        # Extract skills from technologies
        skills = [
            {"name": tech, "level": "intermediate", "projects": 1}
            for tech in technologies
        ]

        return self.generate_certificate(
            student_name=student_name,
            student_id=student_id,
            institution_name=institution_name,
            department=department,
            certificate_type=CertificateType.PROJECT_COMPLETION,
            project_data=project_data,
            evaluation_result=evaluation_result,
            skills=skills,
            faculty_name=faculty_name
        )

    def generate_skill_badge(
        self,
        student_name: str,
        student_id: str,
        skill_name: str,
        skill_level: SkillLevel,
        assessment_score: float,
        hours_practiced: int,
        projects_completed: int
    ) -> Dict[str, Any]:
        """
        Generate a skill badge for specific skill proficiency
        """
        badge_id = f"BADGE-{skill_name.upper().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"

        return {
            "badge_id": badge_id,
            "student_name": student_name,
            "student_id": student_id,
            "skill_name": skill_name,
            "skill_category": self._categorize_skill(skill_name),
            "level": skill_level.value,
            "assessment_score": assessment_score,
            "hours_practiced": hours_practiced,
            "projects_completed": projects_completed,
            "issue_date": datetime.now().isoformat(),
            "verification_code": hashlib.md5(f"{badge_id}{student_id}".encode()).hexdigest()[:12].upper(),
            "badge_image_url": f"/badges/{skill_name.lower().replace(' ', '-')}-{skill_level.value}.png"
        }

    def verify_certificate(self, verification_code: str) -> Dict[str, Any]:
        """
        Verify a certificate by its verification code
        """
        for cert_id, cert in self.issued_certificates.items():
            if cert.verification_code == verification_code:
                # Check expiry
                status = VerificationStatus.VALID
                if cert.expiry_date and datetime.now() > cert.expiry_date:
                    status = VerificationStatus.EXPIRED

                return {
                    "status": status.value,
                    "certificate_id": cert.certificate_id,
                    "student_name": cert.student_name,
                    "certificate_type": cert.certificate_type.value,
                    "project_title": cert.project_title,
                    "institution_name": cert.institution_name,
                    "issue_date": cert.issue_date.isoformat(),
                    "grade": cert.grade,
                    "verified": True
                }

        return {
            "status": "not_found",
            "verified": False,
            "message": "Certificate not found or invalid verification code"
        }

    def get_certificate_html(self, certificate: CertificateData) -> str:
        """
        Generate HTML representation of the certificate
        """
        template = self.templates.get(certificate.certificate_type)
        if not template:
            template = self.templates[CertificateType.PROJECT_COMPLETION]

        # Replace placeholders in template
        html = template.html_template

        replacements = {
            "{{CERTIFICATE_ID}}": certificate.certificate_id,
            "{{STUDENT_NAME}}": certificate.student_name,
            "{{STUDENT_ID}}": certificate.student_id,
            "{{INSTITUTION_NAME}}": certificate.institution_name,
            "{{DEPARTMENT}}": certificate.department,
            "{{PROJECT_TITLE}}": certificate.project_title or "",
            "{{PROJECT_DESCRIPTION}}": certificate.project_description or "",
            "{{TECHNOLOGIES}}": ", ".join(certificate.technologies),
            "{{GRADE}}": certificate.grade or "",
            "{{SCORE}}": str(certificate.score or ""),
            "{{ISSUE_DATE}}": certificate.issue_date.strftime("%B %d, %Y"),
            "{{VERIFICATION_CODE}}": certificate.verification_code,
            "{{VERIFICATION_URL}}": certificate.verification_url,
            "{{FACULTY_NAME}}": certificate.faculty_name or "",
            "{{OVERALL_ATTAINMENT}}": f"{certificate.overall_attainment:.1f}%"
        }

        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)

        # Add skills section
        skills_html = self._generate_skills_html(certificate.skills)
        html = html.replace("{{SKILLS_SECTION}}", skills_html)

        # Add CO-PO attainment section
        attainment_html = self._generate_attainment_html(
            certificate.course_outcomes,
            certificate.program_outcomes
        )
        html = html.replace("{{ATTAINMENT_SECTION}}", attainment_html)

        return f"<style>{template.css_styles}</style>{html}"

    def export_certificate_pdf(self, certificate: CertificateData) -> bytes:
        """
        Export certificate as PDF bytes
        Note: Requires weasyprint or similar library for full PDF generation
        For now, returns HTML that can be converted to PDF
        """
        html = self.get_certificate_html(certificate)

        # In a real implementation, use weasyprint or reportlab
        # For now, return HTML bytes that can be converted client-side
        return html.encode('utf-8')

    def get_certificate_json(self, certificate: CertificateData) -> Dict[str, Any]:
        """
        Export certificate data as JSON for API responses
        """
        return {
            "certificate_id": certificate.certificate_id,
            "certificate_type": certificate.certificate_type.value,
            "student": {
                "name": certificate.student_name,
                "id": certificate.student_id
            },
            "institution": {
                "name": certificate.institution_name,
                "department": certificate.department
            },
            "project": {
                "title": certificate.project_title,
                "description": certificate.project_description,
                "duration_weeks": certificate.project_duration_weeks,
                "repository": certificate.project_repository,
                "technologies": certificate.technologies
            } if certificate.project_title else None,
            "skills": [
                {
                    "name": s.name,
                    "category": s.category,
                    "level": s.level.value,
                    "hours_practiced": s.hours_practiced,
                    "projects_applied": s.projects_applied,
                    "assessment_score": s.assessment_score
                }
                for s in certificate.skills
            ],
            "obe_metrics": {
                "course_outcomes": [
                    {
                        "co_id": co.co_id,
                        "description": co.co_description,
                        "target_level": co.target_level,
                        "achieved_level": co.achieved_level,
                        "attainment_percentage": co.attainment_percentage,
                        "bloom_level": co.bloom_level
                    }
                    for co in certificate.course_outcomes
                ],
                "program_outcomes": [
                    {
                        "po_id": po.po_id,
                        "description": po.po_description,
                        "contribution": po.contribution_percentage,
                        "evidence": po.evidence
                    }
                    for po in certificate.program_outcomes
                ],
                "overall_attainment": certificate.overall_attainment
            },
            "assessment": {
                "grade": certificate.grade,
                "score": certificate.score,
                "percentile": certificate.percentile
            },
            "verification": {
                "code": certificate.verification_code,
                "url": certificate.verification_url,
                "qr_data": certificate.qr_code_data
            },
            "metadata": {
                "issue_date": certificate.issue_date.isoformat(),
                "expiry_date": certificate.expiry_date.isoformat() if certificate.expiry_date else None,
                "issuer": certificate.issuer_name,
                "faculty_name": certificate.faculty_name,
                "faculty_designation": certificate.faculty_designation
            }
        }

    def _generate_certificate_id(self, student_id: str, cert_type: CertificateType) -> str:
        """Generate unique certificate ID"""
        timestamp = datetime.now().strftime("%Y%m%d")
        unique = uuid.uuid4().hex[:6].upper()
        type_code = cert_type.value[:4].upper()
        return f"CERT-{type_code}-{timestamp}-{unique}"

    def _generate_verification_code(self, cert_id: str, student_id: str) -> str:
        """Generate verification code for certificate"""
        data = f"{cert_id}{student_id}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16].upper()

    def _generate_qr_data(self, certificate: CertificateData) -> str:
        """Generate QR code data for verification"""
        qr_data = {
            "cert_id": certificate.certificate_id,
            "verify_url": certificate.verification_url,
            "code": certificate.verification_code
        }
        return base64.b64encode(json.dumps(qr_data).encode()).decode()

    def _categorize_skill(self, skill_name: str) -> str:
        """Categorize a skill based on name"""
        skill_lower = skill_name.lower()
        for category, skills in self.skill_categories.items():
            if any(s.lower() in skill_lower or skill_lower in s.lower() for s in skills):
                return category
        return "General"

    def _generate_skills_html(self, skills: List[Skill]) -> str:
        """Generate HTML for skills section"""
        if not skills:
            return "<p>No skills recorded</p>"

        html = "<div class='skills-grid'>"
        for skill in skills:
            level_color = {
                SkillLevel.BEGINNER: "#4CAF50",
                SkillLevel.INTERMEDIATE: "#2196F3",
                SkillLevel.ADVANCED: "#FF9800",
                SkillLevel.EXPERT: "#9C27B0"
            }.get(skill.level, "#757575")

            html += f"""
            <div class='skill-badge' style='border-color: {level_color}'>
                <span class='skill-name'>{skill.name}</span>
                <span class='skill-level' style='background: {level_color}'>{skill.level.value.title()}</span>
            </div>
            """
        html += "</div>"
        return html

    def _generate_attainment_html(
        self,
        course_outcomes: List[CourseOutcomeAttainment],
        program_outcomes: List[ProgramOutcomeMapping]
    ) -> str:
        """Generate HTML for CO-PO attainment section"""
        html = "<div class='attainment-section'>"

        if course_outcomes:
            html += "<h4>Course Outcome Attainment</h4><table class='attainment-table'>"
            html += "<tr><th>CO</th><th>Description</th><th>Target</th><th>Achieved</th><th>Attainment</th></tr>"
            for co in course_outcomes:
                html += f"""
                <tr>
                    <td>{co.co_id}</td>
                    <td>{co.co_description[:50]}...</td>
                    <td>{co.target_level}</td>
                    <td>{co.achieved_level:.2f}</td>
                    <td>{co.attainment_percentage:.1f}%</td>
                </tr>
                """
            html += "</table>"

        if program_outcomes:
            html += "<h4>Program Outcome Contribution</h4><div class='po-bars'>"
            for po in program_outcomes:
                width = min(po.contribution_percentage, 100)
                html += f"""
                <div class='po-item'>
                    <span class='po-label'>{po.po_id}</span>
                    <div class='po-bar'>
                        <div class='po-fill' style='width: {width}%'></div>
                    </div>
                    <span class='po-value'>{po.contribution_percentage:.0f}%</span>
                </div>
                """
            html += "</div>"

        html += "</div>"
        return html

    def _get_project_completion_template(self) -> str:
        """Get HTML template for project completion certificate"""
        return """
        <div class="certificate project-completion">
            <div class="certificate-header">
                <div class="logo">BharatBuild AI</div>
                <h1>Certificate of Project Completion</h1>
                <p class="certificate-id">Certificate ID: {{CERTIFICATE_ID}}</p>
            </div>

            <div class="certificate-body">
                <p class="intro">This is to certify that</p>
                <h2 class="student-name">{{STUDENT_NAME}}</h2>
                <p class="student-id">Student ID: {{STUDENT_ID}}</p>
                <p class="institution">{{INSTITUTION_NAME}}</p>
                <p class="department">Department of {{DEPARTMENT}}</p>

                <p class="achievement">has successfully completed the project</p>
                <h3 class="project-title">"{{PROJECT_TITLE}}"</h3>
                <p class="project-desc">{{PROJECT_DESCRIPTION}}</p>

                <div class="details">
                    <p><strong>Technologies Used:</strong> {{TECHNOLOGIES}}</p>
                    <p><strong>Grade Achieved:</strong> {{GRADE}}</p>
                    <p><strong>Overall Attainment:</strong> {{OVERALL_ATTAINMENT}}</p>
                </div>

                {{SKILLS_SECTION}}
                {{ATTAINMENT_SECTION}}
            </div>

            <div class="certificate-footer">
                <div class="signatures">
                    <div class="signature">
                        <div class="signature-line"></div>
                        <p>{{FACULTY_NAME}}</p>
                        <p class="designation">Faculty Advisor</p>
                    </div>
                    <div class="signature">
                        <div class="signature-line"></div>
                        <p>Head of Department</p>
                    </div>
                </div>

                <div class="verification">
                    <p>Issue Date: {{ISSUE_DATE}}</p>
                    <p>Verification Code: {{VERIFICATION_CODE}}</p>
                    <p>Verify at: {{VERIFICATION_URL}}</p>
                </div>
            </div>
        </div>
        """

    def _get_skill_proficiency_template(self) -> str:
        """Get HTML template for skill proficiency certificate"""
        return """
        <div class="certificate skill-proficiency">
            <div class="certificate-header">
                <div class="logo">BharatBuild AI</div>
                <h1>Skill Proficiency Certificate</h1>
                <p class="certificate-id">Certificate ID: {{CERTIFICATE_ID}}</p>
            </div>

            <div class="certificate-body">
                <p class="intro">This is to certify that</p>
                <h2 class="student-name">{{STUDENT_NAME}}</h2>
                <p class="student-id">Student ID: {{STUDENT_ID}}</p>
                <p class="institution">{{INSTITUTION_NAME}}</p>

                <p class="achievement">has demonstrated proficiency in the following skills</p>

                {{SKILLS_SECTION}}

                <div class="score-section">
                    <p><strong>Assessment Score:</strong> {{SCORE}}/100</p>
                    <p><strong>Grade:</strong> {{GRADE}}</p>
                </div>
            </div>

            <div class="certificate-footer">
                <div class="verification">
                    <p>Issue Date: {{ISSUE_DATE}}</p>
                    <p>Verification Code: {{VERIFICATION_CODE}}</p>
                </div>
            </div>
        </div>
        """

    def _get_course_completion_template(self) -> str:
        """Get HTML template for course completion certificate"""
        return """
        <div class="certificate course-completion">
            <div class="certificate-header">
                <div class="logo">BharatBuild AI</div>
                <h1>Course Completion Certificate</h1>
                <p class="certificate-id">Certificate ID: {{CERTIFICATE_ID}}</p>
            </div>

            <div class="certificate-body">
                <p class="intro">This is to certify that</p>
                <h2 class="student-name">{{STUDENT_NAME}}</h2>
                <p class="student-id">Student ID: {{STUDENT_ID}}</p>
                <p class="institution">{{INSTITUTION_NAME}}</p>
                <p class="department">{{DEPARTMENT}}</p>

                <p class="achievement">has successfully completed the course with the following outcomes</p>

                {{ATTAINMENT_SECTION}}

                <div class="grade-section">
                    <p><strong>Final Grade:</strong> {{GRADE}}</p>
                    <p><strong>Overall Attainment:</strong> {{OVERALL_ATTAINMENT}}</p>
                </div>
            </div>

            <div class="certificate-footer">
                <div class="signatures">
                    <div class="signature">
                        <div class="signature-line"></div>
                        <p>{{FACULTY_NAME}}</p>
                        <p class="designation">Course Instructor</p>
                    </div>
                </div>

                <div class="verification">
                    <p>Issue Date: {{ISSUE_DATE}}</p>
                    <p>Verify: {{VERIFICATION_URL}}</p>
                </div>
            </div>
        </div>
        """

    def _get_default_css(self) -> str:
        """Get default CSS styles for certificates"""
        return """
        .certificate {
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border: 3px solid #1a365d;
            font-family: 'Georgia', serif;
        }

        .certificate-header {
            text-align: center;
            border-bottom: 2px solid #1a365d;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .logo {
            font-size: 24px;
            font-weight: bold;
            color: #2563eb;
            margin-bottom: 10px;
        }

        .certificate-header h1 {
            color: #1a365d;
            font-size: 28px;
            margin: 10px 0;
        }

        .certificate-id {
            color: #666;
            font-size: 12px;
        }

        .certificate-body {
            text-align: center;
            padding: 20px 0;
        }

        .intro {
            font-size: 16px;
            color: #333;
        }

        .student-name {
            font-size: 32px;
            color: #1a365d;
            margin: 15px 0;
            font-style: italic;
        }

        .student-id, .institution, .department {
            font-size: 14px;
            color: #555;
            margin: 5px 0;
        }

        .achievement {
            font-size: 16px;
            margin: 20px 0;
        }

        .project-title {
            font-size: 24px;
            color: #2563eb;
            margin: 10px 0;
        }

        .project-desc {
            font-size: 14px;
            color: #666;
            max-width: 600px;
            margin: 10px auto;
        }

        .details {
            margin: 20px 0;
            padding: 15px;
            background: rgba(255,255,255,0.5);
            border-radius: 8px;
        }

        .skills-grid {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
        }

        .skill-badge {
            padding: 8px 16px;
            border: 2px solid;
            border-radius: 20px;
            background: white;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .skill-level {
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 10px;
            color: white;
        }

        .attainment-section {
            margin: 20px 0;
            text-align: left;
        }

        .attainment-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 12px;
        }

        .attainment-table th, .attainment-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
        }

        .attainment-table th {
            background: #1a365d;
            color: white;
        }

        .po-bars {
            margin: 10px 0;
        }

        .po-item {
            display: flex;
            align-items: center;
            margin: 5px 0;
        }

        .po-label {
            width: 40px;
            font-weight: bold;
        }

        .po-bar {
            flex: 1;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 0 10px;
        }

        .po-fill {
            height: 100%;
            background: linear-gradient(90deg, #2563eb, #3b82f6);
            border-radius: 10px;
        }

        .po-value {
            width: 40px;
            text-align: right;
        }

        .certificate-footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #1a365d;
        }

        .signatures {
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
        }

        .signature {
            text-align: center;
        }

        .signature-line {
            width: 150px;
            border-bottom: 1px solid #333;
            margin-bottom: 10px;
        }

        .designation {
            font-size: 12px;
            color: #666;
        }

        .verification {
            text-align: center;
            font-size: 12px;
            color: #666;
        }
        """


# Singleton instance
certificate_generator = SkillCertificationGenerator()
