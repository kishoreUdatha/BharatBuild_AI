'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  GraduationCap,
  FileText,
  Building2,
  Users,
  Shield,
  Leaf,
  Save,
  Upload,
  CheckCircle2,
  Clock,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Loader2,
  FolderOpen,
  User,
  ClipboardList,
  FileCheck,
  Info,
  Target,
  Award,
  Trash2,
  X,
  File,
  Check
} from 'lucide-react'

// Complete NAAC Criterion Data with proper structure
const CRITERIA_DATA: Record<number, CriterionData> = {
  1: {
    number: 1,
    name: 'Curricular Aspects',
    marks: 150,
    icon: 'BookOpen',
    color: 'orange',
    purpose: 'To show how well your curriculum is designed, planned, implemented, and improved in line with University/Regulatory norms, Industry needs, Student outcomes, and Employability & skill development.',
    keyIndicators: [
      {
        code: '1.1',
        name: 'Curriculum Design and Development',
        description: 'How curriculum is designed/revised with involvement of Faculty, Industry experts, Alumni, Employers. Alignment with POs, PSOs, COs, Industry trends, National policies (NEP, SDGs).',
        maxMarks: 20,
        dataOwners: ['BoS / Academic Council', 'HODs', 'IQAC'],
        requiredDocs: ['Board of Studies (BoS) minutes', 'Syllabus copies', 'Expert feedback', 'CO-PO mapping documents'],
        metrics: [
          { id: '1.1.1', name: 'Curriculum design with stakeholder input', type: 'percentage', unit: '%', description: 'Percentage of programs where curriculum is designed with stakeholder participation' },
          { id: '1.1.2', name: 'Programs with syllabus revision in last 3 years', type: 'number', unit: 'programs', description: 'Number of programs where syllabus was revised' },
          { id: '1.1.3', name: 'Courses with industry expert involvement', type: 'number', unit: 'courses', description: 'Number of courses developed with industry expert input' },
        ]
      },
      {
        code: '1.2',
        name: 'Academic Flexibility',
        description: 'Choice Based Credit System (CBCS), Electives/Open electives, Value-added courses, Interdisciplinary options offered to students.',
        maxMarks: 30,
        dataOwners: ['Academic Section', 'HODs', 'Course Coordinators'],
        requiredDocs: ['List of electives', 'Student enrollment numbers', 'Value-added course details', 'CBCS implementation documents'],
        metrics: [
          { id: '1.2.1', name: 'Programs with CBCS/Elective system', type: 'percentage', unit: '%', description: 'Percentage of programs offering CBCS' },
          { id: '1.2.2', name: 'Add-on/Certificate programs offered', type: 'number', unit: 'programs', description: 'Total number of add-on programs' },
          { id: '1.2.3', name: 'Students enrolled in Certificate/Add-on programs', type: 'number', unit: 'students', description: 'Total enrollment in add-on programs' },
          { id: '1.2.4', name: 'Open elective courses available', type: 'number', unit: 'courses', description: 'Number of open elective courses offered' },
        ]
      },
      {
        code: '1.3',
        name: 'Curriculum Enrichment',
        description: 'Add-on/Certificate courses, Skill development programs, Industry/emerging areas (AI/ML, Blockchain, Cybersecurity), Cross-cutting issues (Gender, Environment, Ethics, Human values).',
        maxMarks: 30,
        dataOwners: ['Training & Placement Cell', 'Industry Collaboration Cell', 'Department Coordinators'],
        requiredDocs: ['Course brochures', 'MoUs with industry', 'Attendance sheets', 'Completion certificates', 'Skill course content'],
        metrics: [
          { id: '1.3.1', name: 'Courses on employability/entrepreneurship/skill development', type: 'percentage', unit: '%', description: 'Percentage of courses focusing on skills' },
          { id: '1.3.2', name: 'Students in project work/field work/internships', type: 'percentage', unit: '%', description: 'Percentage of students undertaking experiential learning' },
          { id: '1.3.3', name: 'Value-added courses offered', type: 'number', unit: 'courses', description: 'Number of value-added courses' },
          { id: '1.3.4', name: 'Courses on cross-cutting issues', type: 'number', unit: 'courses', description: 'Courses addressing gender, environment, ethics' },
          { id: '1.3.5', name: 'Students enrolled in value-added courses', type: 'number', unit: 'students', description: 'Total students in value-added courses' },
        ]
      },
      {
        code: '1.4',
        name: 'Feedback System',
        description: 'Structured feedback from Students, Alumni, Teachers, Employers. Analysis of feedback and action taken reports.',
        maxMarks: 20,
        dataOwners: ['IQAC', 'Feedback Committee', 'Department Representatives'],
        requiredDocs: ['Feedback questionnaires', 'Analysis reports', 'Action Taken Reports (ATR)', 'Feedback forms from all stakeholders'],
        metrics: [
          { id: '1.4.1', name: 'Structured feedback from students', type: 'select', options: ['Yes, with analysis', 'Yes, without analysis', 'No'], description: 'Student feedback mechanism' },
          { id: '1.4.2', name: 'Feedback from teachers on curriculum', type: 'select', options: ['Yes, with analysis', 'Yes, without analysis', 'No'], description: 'Teacher feedback mechanism' },
          { id: '1.4.3', name: 'Feedback from employers/industry', type: 'select', options: ['Yes, with analysis', 'Yes, without analysis', 'No'], description: 'Employer feedback mechanism' },
          { id: '1.4.4', name: 'Feedback from alumni', type: 'select', options: ['Yes, with analysis', 'Yes, without analysis', 'No'], description: 'Alumni feedback mechanism' },
          { id: '1.4.5', name: 'Action taken on feedback', type: 'textarea', description: 'Describe actions taken based on feedback analysis' },
        ]
      },
    ],
    folderStructure: [
      'Criterion 1/',
      '├── 1.1 Curriculum Design/',
      '│   ├── BoS Minutes/',
      '│   ├── Syllabus/',
      '│   └── CO-PO Mapping/',
      '├── 1.2 Academic Flexibility/',
      '│   ├── CBCS Documents/',
      '│   ├── Elective Lists/',
      '│   └── Add-on Courses/',
      '├── 1.3 Curriculum Enrichment/',
      '│   ├── Value Added Courses/',
      '│   ├── Skill Programs/',
      '│   └── Industry MoUs/',
      '└── 1.4 Feedback System/',
      '    ├── Feedback Forms/',
      '    ├── Analysis Reports/',
      '    └── Action Taken Reports/'
    ],
    proTips: [
      'Use industry-aligned programs (AI, Data, Cloud, Core Engg tools)',
      'Show clear CO-PO mapping for all courses',
      'Link add-on courses to employability outcomes',
      'Maintain documented feedback loop with ATRs',
      'Include NEP 2020 alignment evidence'
    ]
  },
  2: {
    number: 2,
    name: 'Teaching-Learning and Evaluation',
    marks: 200,
    icon: 'GraduationCap',
    color: 'blue',
    purpose: 'To assess student enrollment diversity, teaching-learning processes, teacher quality, evaluation mechanisms, and learning outcomes achievement.',
    keyIndicators: [
      {
        code: '2.1',
        name: 'Student Enrollment and Profile',
        description: 'Enrollment against sanctioned intake, diversity of students, reservation category fulfillment.',
        maxMarks: 20,
        dataOwners: ['Admissions Office', 'Academic Section', 'Registrar'],
        requiredDocs: ['Admission records', 'Category-wise enrollment', 'State/Country-wise data'],
        metrics: [
          { id: '2.1.1', name: 'Enrollment percentage', type: 'percentage', unit: '%', description: 'Students enrolled vs sanctioned intake' },
          { id: '2.1.2', name: 'Seats filled against reserved categories', type: 'percentage', unit: '%', description: 'Reservation category fulfillment' },
          { id: '2.1.3', name: 'Students from other states/countries', type: 'number', unit: 'students', description: 'Diversity in student enrollment' },
        ]
      },
      {
        code: '2.2',
        name: 'Catering to Student Diversity',
        description: 'Programs for advanced learners, slow learners, differently-abled students. Student-teacher ratio.',
        maxMarks: 20,
        dataOwners: ['Academic Section', 'Counseling Cell', 'HODs'],
        requiredDocs: ['Remedial class records', 'Advanced learner programs', 'Mentoring records'],
        metrics: [
          { id: '2.2.1', name: 'Student-full time teacher ratio', type: 'ratio', unit: ':1', description: 'Overall student to teacher ratio' },
          { id: '2.2.2', name: 'Students in advanced learner programs', type: 'number', unit: 'students', description: 'Honor students/toppers programs' },
          { id: '2.2.3', name: 'Students in slow learner programs', type: 'number', unit: 'students', description: 'Remedial/bridge course students' },
        ]
      },
      {
        code: '2.3',
        name: 'Teaching-Learning Process',
        description: 'ICT-enabled teaching, student-centric methods, experiential learning, participative learning.',
        maxMarks: 40,
        dataOwners: ['HODs', 'Faculty', 'IT Department'],
        requiredDocs: ['ICT facility records', 'Innovative teaching methods', 'Lab manuals', 'Project reports'],
        metrics: [
          { id: '2.3.1', name: 'ICT enabled classrooms/seminar halls', type: 'percentage', unit: '%', description: 'Smart classrooms percentage' },
          { id: '2.3.2', name: 'Teachers using ICT for teaching', type: 'percentage', unit: '%', description: 'Faculty ICT adoption rate' },
          { id: '2.3.3', name: 'Student-centric methods used', type: 'textarea', description: 'List experiential, participative methods' },
          { id: '2.3.4', name: 'Mentor-mentee ratio', type: 'ratio', unit: ':1', description: 'Students assigned per mentor' },
        ]
      },
      {
        code: '2.4',
        name: 'Teacher Profile and Quality',
        description: 'Qualifications (PhD, NET/SET), experience, awards, faculty development.',
        maxMarks: 40,
        dataOwners: ['HR/Establishment', 'IQAC', 'HODs'],
        requiredDocs: ['Faculty qualification records', 'PhD certificates', 'Experience certificates', 'Award documents'],
        metrics: [
          { id: '2.4.1', name: 'Full-time teachers with PhD', type: 'percentage', unit: '%', description: 'PhD holders percentage' },
          { id: '2.4.2', name: 'Full-time teachers with NET/SET/SLET', type: 'percentage', unit: '%', description: 'NET qualified percentage' },
          { id: '2.4.3', name: 'Average teaching experience', type: 'number', unit: 'years', description: 'Average years of experience' },
          { id: '2.4.4', name: 'Teachers with industry experience', type: 'number', unit: 'teachers', description: 'Faculty with industry background' },
          { id: '2.4.5', name: 'Awards/recognitions received by teachers', type: 'number', unit: 'awards', description: 'Faculty achievements' },
        ]
      },
      {
        code: '2.5',
        name: 'Evaluation Process and Reforms',
        description: 'Continuous Internal Evaluation, examination reforms, IT integration, grievance redressal.',
        maxMarks: 30,
        dataOwners: ['Examination Cell', 'COE', 'IQAC'],
        requiredDocs: ['CIE records', 'Exam automation details', 'Grievance records', 'Result analysis'],
        metrics: [
          { id: '2.5.1', name: 'Continuous Internal Evaluation mechanism', type: 'select', options: ['Yes', 'No'], description: 'CIE implementation status' },
          { id: '2.5.2', name: 'Student grievances redressed', type: 'percentage', unit: '%', description: 'Grievance resolution rate' },
          { id: '2.5.3', name: 'IT integration in examination', type: 'select', options: ['Fully automated', 'Partially automated', 'Manual'], description: 'Exam automation level' },
        ]
      },
      {
        code: '2.6',
        name: 'Student Performance and Learning Outcomes',
        description: 'Program outcomes attainment, pass percentage, students qualifying competitive exams.',
        maxMarks: 30,
        dataOwners: ['Examination Cell', 'Departments', 'T&P Cell'],
        requiredDocs: ['PO attainment data', 'Result analysis', 'Competitive exam qualifiers'],
        metrics: [
          { id: '2.6.1', name: 'Program outcomes (POs) attainment', type: 'percentage', unit: '%', description: 'Average PO attainment level' },
          { id: '2.6.2', name: 'Pass percentage of final year', type: 'percentage', unit: '%', description: 'Final year pass rate' },
          { id: '2.6.3', name: 'Students qualifying GATE/NET/other exams', type: 'number', unit: 'students', description: 'Competitive exam qualifiers' },
        ]
      },
      {
        code: '2.7',
        name: 'Student Satisfaction Survey',
        description: 'Online student satisfaction survey conducted and analyzed.',
        maxMarks: 20,
        dataOwners: ['IQAC', 'IT Cell'],
        requiredDocs: ['Survey forms', 'Analysis report', 'Action taken'],
        metrics: [
          { id: '2.7.1', name: 'Student satisfaction score', type: 'percentage', unit: '%', description: 'Overall satisfaction percentage' },
          { id: '2.7.2', name: 'Students participated in survey', type: 'percentage', unit: '%', description: 'Survey participation rate' },
        ]
      },
    ],
    folderStructure: [
      'Criterion 2/',
      '├── 2.1 Student Enrollment/',
      '├── 2.2 Student Diversity/',
      '├── 2.3 Teaching-Learning/',
      '├── 2.4 Teacher Profile/',
      '├── 2.5 Evaluation/',
      '├── 2.6 Learning Outcomes/',
      '└── 2.7 Student Satisfaction/'
    ],
    proTips: [
      'Maintain detailed CO-PO attainment calculations',
      'Document all ICT-enabled teaching initiatives',
      'Keep faculty development records updated',
      'Conduct regular student satisfaction surveys'
    ]
  },
  3: {
    number: 3,
    name: 'Research, Innovations and Extension',
    marks: 150,
    icon: 'FileText',
    color: 'green',
    purpose: 'To assess research ecosystem, funding, publications, patents, innovations, startups, and extension activities.',
    keyIndicators: [
      {
        code: '3.1',
        name: 'Resource Mobilization for Research',
        description: 'Grants from government and non-government agencies, research projects, fellowships.',
        maxMarks: 20,
        dataOwners: ['Research Cell', 'Finance Section', 'Principal'],
        requiredDocs: ['Sanction letters', 'Utilization certificates', 'Project reports'],
        metrics: [
          { id: '3.1.1', name: 'Grants from government (₹ Lakhs)', type: 'number', unit: '₹ Lakhs', description: 'Total government funding received' },
          { id: '3.1.2', name: 'Grants from non-government (₹ Lakhs)', type: 'number', unit: '₹ Lakhs', description: 'Industry/private funding' },
          { id: '3.1.3', name: 'Research projects sanctioned', type: 'number', unit: 'projects', description: 'Number of funded projects' },
        ]
      },
      {
        code: '3.2',
        name: 'Innovation Ecosystem',
        description: 'Innovation/Incubation centers, IPR workshops, startups incubated, innovation awards.',
        maxMarks: 20,
        dataOwners: ['Innovation Cell', 'Incubation Center', 'IPR Cell'],
        requiredDocs: ['Incubation center records', 'Startup details', 'IPR workshop reports'],
        metrics: [
          { id: '3.2.1', name: 'Innovation/Incubation center exists', type: 'select', options: ['Yes', 'No'], description: 'Incubation facility status' },
          { id: '3.2.2', name: 'Startups incubated', type: 'number', unit: 'startups', description: 'Number of startups supported' },
          { id: '3.2.3', name: 'IPR workshops/seminars conducted', type: 'number', unit: 'events', description: 'Awareness programs on IPR' },
        ]
      },
      {
        code: '3.3',
        name: 'Research Publications and Awards',
        description: 'Publications in UGC-CARE, Scopus, Web of Science journals. Books, patents, h-index.',
        maxMarks: 40,
        dataOwners: ['Research Cell', 'Library', 'Faculty'],
        requiredDocs: ['Publication list with DOI', 'Patent certificates', 'Book copies'],
        metrics: [
          { id: '3.3.1', name: 'Papers in UGC-CARE journals', type: 'number', unit: 'papers', description: 'UGC recognized publications' },
          { id: '3.3.2', name: 'Papers in Scopus/Web of Science', type: 'number', unit: 'papers', description: 'Indexed journal publications' },
          { id: '3.3.3', name: 'Books and chapters published', type: 'number', unit: 'books', description: 'Academic books authored' },
          { id: '3.3.4', name: 'Patents published/granted', type: 'number', unit: 'patents', description: 'IPR achievements' },
        ]
      },
      {
        code: '3.4',
        name: 'Extension Activities',
        description: 'NSS, NCC, community outreach, social responsibility initiatives.',
        maxMarks: 40,
        dataOwners: ['NSS/NCC Coordinators', 'Extension Cell', 'IQAC'],
        requiredDocs: ['Activity reports', 'Photos', 'Beneficiary feedback', 'Certificates'],
        metrics: [
          { id: '3.4.1', name: 'Extension activities conducted', type: 'number', unit: 'activities', description: 'Outreach programs organized' },
          { id: '3.4.2', name: 'Students in extension activities', type: 'percentage', unit: '%', description: 'Student participation rate' },
          { id: '3.4.3', name: 'Awards for extension activities', type: 'number', unit: 'awards', description: 'Recognition received' },
        ]
      },
      {
        code: '3.5',
        name: 'Collaboration',
        description: 'MoUs with institutions and industries, collaborative activities, linkages.',
        maxMarks: 30,
        dataOwners: ['Industry Relations', 'International Cell', 'IQAC'],
        requiredDocs: ['MoU copies', 'Activity reports', 'Exchange program details'],
        metrics: [
          { id: '3.5.1', name: 'Functional MoUs with institutions', type: 'number', unit: 'MoUs', description: 'Active academic collaborations' },
          { id: '3.5.2', name: 'Functional MoUs with industries', type: 'number', unit: 'MoUs', description: 'Active industry partnerships' },
          { id: '3.5.3', name: 'Collaborative activities conducted', type: 'number', unit: 'activities', description: 'Joint programs/events' },
        ]
      },
    ],
    folderStructure: [
      'Criterion 3/',
      '├── 3.1 Research Funding/',
      '├── 3.2 Innovation/',
      '├── 3.3 Publications/',
      '├── 3.4 Extension/',
      '└── 3.5 Collaborations/'
    ],
    proTips: [
      'Maintain publication database with DOI links',
      'Document all MoU activities with evidence',
      'Track patent filing and grant status'
    ]
  },
  4: {
    number: 4,
    name: 'Infrastructure and Learning Resources',
    marks: 100,
    icon: 'Building2',
    color: 'purple',
    purpose: 'To assess physical facilities, library resources, IT infrastructure, and maintenance systems.',
    keyIndicators: [
      {
        code: '4.1',
        name: 'Physical Facilities',
        description: 'Classrooms, laboratories, computing equipment, sports facilities.',
        maxMarks: 30,
        dataOwners: ['Estate/Infrastructure', 'Lab Incharges', 'Sports Director'],
        requiredDocs: ['Building plans', 'Lab equipment list', 'Sports facility details'],
        metrics: [
          { id: '4.1.1', name: 'Classrooms with ICT facilities', type: 'percentage', unit: '%', description: 'Smart classroom percentage' },
          { id: '4.1.2', name: 'Laboratories available', type: 'number', unit: 'labs', description: 'Total functional laboratories' },
          { id: '4.1.3', name: 'Campus area (acres)', type: 'number', unit: 'acres', description: 'Total campus land area' },
          { id: '4.1.4', name: 'Built-up area (sq.m)', type: 'number', unit: 'sq.m', description: 'Total constructed area' },
        ]
      },
      {
        code: '4.2',
        name: 'Library as a Learning Resource',
        description: 'Library automation, e-resources, usage statistics.',
        maxMarks: 20,
        dataOwners: ['Librarian', 'IT Cell'],
        requiredDocs: ['Library software details', 'E-resource subscriptions', 'Usage statistics'],
        metrics: [
          { id: '4.2.1', name: 'Library automation status', type: 'select', options: ['Fully automated', 'Partially automated', 'Not automated'], description: 'Library management system' },
          { id: '4.2.2', name: 'Total books in library', type: 'number', unit: 'books', description: 'Print book collection' },
          { id: '4.2.3', name: 'E-journals/E-books subscribed', type: 'number', unit: 'resources', description: 'Digital library resources' },
          { id: '4.2.4', name: 'Annual library expenditure (₹ Lakhs)', type: 'number', unit: '₹ Lakhs', description: 'Library budget utilization' },
        ]
      },
      {
        code: '4.3',
        name: 'IT Infrastructure',
        description: 'Computing facilities, internet, campus network, ERP.',
        maxMarks: 20,
        dataOwners: ['IT Department', 'System Admin'],
        requiredDocs: ['Network diagram', 'Bandwidth details', 'ERP screenshots'],
        metrics: [
          { id: '4.3.1', name: 'Student-computer ratio', type: 'ratio', unit: ':1', description: 'Computers available per student' },
          { id: '4.3.2', name: 'Internet bandwidth (Mbps)', type: 'number', unit: 'Mbps', description: 'Total internet bandwidth' },
          { id: '4.3.3', name: 'Wi-Fi enabled campus', type: 'select', options: ['Yes, 100%', 'Yes, partial', 'No'], description: 'Wireless coverage' },
          { id: '4.3.4', name: 'ERP system implemented', type: 'select', options: ['Yes, fully', 'Yes, partially', 'No'], description: 'Enterprise system usage' },
        ]
      },
      {
        code: '4.4',
        name: 'Maintenance of Campus Infrastructure',
        description: 'Maintenance systems, audits, expenditure on upkeep.',
        maxMarks: 30,
        dataOwners: ['Estate Section', 'Finance', 'IQAC'],
        requiredDocs: ['Maintenance policy', 'Audit reports', 'AMC documents'],
        metrics: [
          { id: '4.4.1', name: 'Annual maintenance expenditure (₹ Lakhs)', type: 'number', unit: '₹ Lakhs', description: 'Infrastructure maintenance budget' },
          { id: '4.4.2', name: 'Green audit conducted', type: 'select', options: ['Yes', 'No'], description: 'Environmental audit status' },
          { id: '4.4.3', name: 'Energy audit conducted', type: 'select', options: ['Yes', 'No'], description: 'Energy efficiency audit' },
        ]
      },
    ],
    folderStructure: ['Criterion 4/', '├── 4.1 Physical Facilities/', '├── 4.2 Library/', '├── 4.3 IT Infrastructure/', '└── 4.4 Maintenance/'],
    proTips: ['Maintain updated equipment inventory', 'Document all green initiatives', 'Keep library usage statistics']
  },
  5: {
    number: 5,
    name: 'Student Support and Progression',
    marks: 50,
    icon: 'Users',
    color: 'cyan',
    purpose: 'To assess student support services, career guidance, placements, higher education progression, and alumni engagement.',
    keyIndicators: [
      {
        code: '5.1',
        name: 'Student Support',
        description: 'Scholarships, capability enhancement, career counseling, competitive exam coaching.',
        maxMarks: 15,
        dataOwners: ['Scholarship Cell', 'T&P Cell', 'Student Welfare'],
        requiredDocs: ['Scholarship records', 'Career guidance reports', 'Coaching program details'],
        metrics: [
          { id: '5.1.1', name: 'Students benefited by scholarships', type: 'percentage', unit: '%', description: 'Scholarship coverage' },
          { id: '5.1.2', name: 'Capability enhancement programs', type: 'number', unit: 'programs', description: 'Soft skills, aptitude training' },
          { id: '5.1.3', name: 'Students in competitive exam coaching', type: 'number', unit: 'students', description: 'GATE/CAT/GRE coaching' },
        ]
      },
      {
        code: '5.2',
        name: 'Student Progression',
        description: 'Placements, higher education, competitive exam qualifiers.',
        maxMarks: 15,
        dataOwners: ['T&P Cell', 'Academic Section'],
        requiredDocs: ['Placement records', 'Higher education data', 'Offer letters'],
        metrics: [
          { id: '5.2.1', name: 'Placement percentage', type: 'percentage', unit: '%', description: 'Students placed through campus' },
          { id: '5.2.2', name: 'Students to higher education', type: 'percentage', unit: '%', description: 'PG/Research admission rate' },
          { id: '5.2.3', name: 'Average salary package (₹ LPA)', type: 'number', unit: '₹ LPA', description: 'Average CTC of placed students' },
          { id: '5.2.4', name: 'Students qualifying competitive exams', type: 'number', unit: 'students', description: 'GATE/NET/CAT qualifiers' },
        ]
      },
      {
        code: '5.3',
        name: 'Student Participation and Activities',
        description: 'Sports, cultural activities, student council, clubs.',
        maxMarks: 10,
        dataOwners: ['Sports Director', 'Cultural Committee', 'Student Council'],
        requiredDocs: ['Event reports', 'Award certificates', 'Activity photos'],
        metrics: [
          { id: '5.3.1', name: 'Awards in sports/cultural at state/national level', type: 'number', unit: 'awards', description: 'Student achievements' },
          { id: '5.3.2', name: 'Student council exists', type: 'select', options: ['Yes', 'No'], description: 'Student governance body' },
        ]
      },
      {
        code: '5.4',
        name: 'Alumni Engagement',
        description: 'Alumni association, contributions, networking, mentoring.',
        maxMarks: 10,
        dataOwners: ['Alumni Cell', 'T&P Cell'],
        requiredDocs: ['Alumni database', 'Contribution records', 'Event reports'],
        metrics: [
          { id: '5.4.1', name: 'Registered alumni association', type: 'select', options: ['Yes', 'No'], description: 'Formal alumni body' },
          { id: '5.4.2', name: 'Alumni contributing to development', type: 'number', unit: 'alumni', description: 'Active alumni contributors' },
          { id: '5.4.3', name: 'Alumni contribution (₹ Lakhs)', type: 'number', unit: '₹ Lakhs', description: 'Financial/in-kind support' },
        ]
      },
    ],
    folderStructure: ['Criterion 5/', '├── 5.1 Student Support/', '├── 5.2 Progression/', '├── 5.3 Activities/', '└── 5.4 Alumni/'],
    proTips: ['Maintain year-wise placement data', 'Document all scholarships disbursed', 'Track alumni contributions']
  },
  6: {
    number: 6,
    name: 'Governance, Leadership and Management',
    marks: 50,
    icon: 'Shield',
    color: 'indigo',
    purpose: 'To assess institutional governance, leadership, strategy, faculty empowerment, and quality assurance mechanisms.',
    keyIndicators: [
      {
        code: '6.1',
        name: 'Institutional Vision and Leadership',
        description: 'Vision, mission, governance structure, participative management.',
        maxMarks: 10,
        dataOwners: ['Principal', 'Management', 'IQAC'],
        requiredDocs: ['Vision/Mission documents', 'Governance structure', 'Committee minutes'],
        metrics: [
          { id: '6.1.1', name: 'Vision and Mission displayed', type: 'select', options: ['Yes', 'No'], description: 'Visibility of V&M' },
          { id: '6.1.2', name: 'Participative management', type: 'select', options: ['Yes', 'No'], description: 'Stakeholder involvement in decisions' },
        ]
      },
      {
        code: '6.2',
        name: 'Strategy Development and Deployment',
        description: 'Strategic plan, e-governance, organizational structure.',
        maxMarks: 10,
        dataOwners: ['Principal', 'Admin', 'IT Cell'],
        requiredDocs: ['Strategic plan', 'E-governance portal', 'Organogram'],
        metrics: [
          { id: '6.2.1', name: 'Perspective/Strategic plan exists', type: 'select', options: ['Yes', 'No'], description: 'Long-term planning' },
          { id: '6.2.2', name: 'E-governance areas implemented', type: 'number', unit: 'areas', description: 'Admin, Finance, Student, Exam' },
        ]
      },
      {
        code: '6.3',
        name: 'Faculty Empowerment Strategies',
        description: 'Faculty development, financial support, welfare measures.',
        maxMarks: 10,
        dataOwners: ['HR', 'IQAC', 'Finance'],
        requiredDocs: ['FDP records', 'Conference attendance', 'Welfare schemes'],
        metrics: [
          { id: '6.3.1', name: 'Teachers with FDP/Conference support', type: 'percentage', unit: '%', description: 'Faculty receiving financial support' },
          { id: '6.3.2', name: 'FDPs/Workshops conducted', type: 'number', unit: 'programs', description: 'Internal development programs' },
        ]
      },
      {
        code: '6.4',
        name: 'Financial Management and Resource Mobilization',
        description: 'Audits, fund mobilization, budget utilization.',
        maxMarks: 10,
        dataOwners: ['Finance Section', 'Accounts', 'Principal'],
        requiredDocs: ['Audit reports', 'Budget documents', 'Fund statements'],
        metrics: [
          { id: '6.4.1', name: 'Internal/External audit conducted', type: 'select', options: ['Yes', 'No'], description: 'Financial audit status' },
          { id: '6.4.2', name: 'Grants/Funds mobilized (₹ Lakhs)', type: 'number', unit: '₹ Lakhs', description: 'Resource mobilization' },
        ]
      },
      {
        code: '6.5',
        name: 'Internal Quality Assurance System',
        description: 'IQAC functioning, quality initiatives, AQAR submission.',
        maxMarks: 10,
        dataOwners: ['IQAC', 'Principal'],
        requiredDocs: ['IQAC minutes', 'AQAR copies', 'Quality initiatives'],
        metrics: [
          { id: '6.5.1', name: 'IQAC established and functional', type: 'select', options: ['Yes', 'No'], description: 'IQAC status' },
          { id: '6.5.2', name: 'Quality initiatives by IQAC', type: 'number', unit: 'initiatives', description: 'Improvement programs' },
          { id: '6.5.3', name: 'AQAR submitted regularly', type: 'select', options: ['Yes', 'No'], description: 'Annual report submission' },
        ]
      },
    ],
    folderStructure: ['Criterion 6/', '├── 6.1 Vision Leadership/', '├── 6.2 Strategy/', '├── 6.3 Faculty Empowerment/', '├── 6.4 Finance/', '└── 6.5 IQAC/'],
    proTips: ['Maintain IQAC meeting minutes', 'Document all governance decisions', 'Submit AQAR on time']
  },
  7: {
    number: 7,
    name: 'Institutional Values and Best Practices',
    marks: 50,
    icon: 'Leaf',
    color: 'emerald',
    purpose: 'To assess institutional values, social responsibilities, environmental consciousness, best practices, and institutional distinctiveness.',
    keyIndicators: [
      {
        code: '7.1',
        name: 'Institutional Values and Social Responsibilities',
        description: 'Gender equity, inclusivity, environment sustainability, green initiatives, divyangjan facilities.',
        maxMarks: 20,
        dataOwners: ['Women Cell', 'NSS/NCC', 'Estate', 'IQAC'],
        requiredDocs: ['Gender audit', 'Green audit', 'Solar/Energy data', 'Accessibility features'],
        metrics: [
          { id: '7.1.1', name: 'Gender equity promotion measures', type: 'textarea', description: 'Describe gender sensitization programs' },
          { id: '7.1.2', name: 'Facilities for differently-abled', type: 'select', options: ['Yes', 'Partial', 'No'], description: 'Divyangjan accessibility' },
          { id: '7.1.3', name: 'Alternate energy sources', type: 'select', options: ['Solar', 'Biogas', 'Both', 'None'], description: 'Renewable energy usage' },
          { id: '7.1.4', name: 'Energy from renewable sources (%)', type: 'percentage', unit: '%', description: 'Green energy percentage' },
          { id: '7.1.5', name: 'Rainwater harvesting', type: 'select', options: ['Yes', 'No'], description: 'Water conservation' },
          { id: '7.1.6', name: 'Waste management system', type: 'select', options: ['Yes', 'No'], description: 'Waste disposal mechanism' },
          { id: '7.1.7', name: 'Green campus initiatives', type: 'textarea', description: 'Describe environmental initiatives' },
        ]
      },
      {
        code: '7.2',
        name: 'Best Practices',
        description: 'Two best practices that have contributed to institutional objectives.',
        maxMarks: 15,
        dataOwners: ['IQAC', 'Principal', 'HODs'],
        requiredDocs: ['Best practice documentation', 'Impact evidence', 'Photos/testimonials'],
        metrics: [
          { id: '7.2.1', name: 'Best Practice 1 - Title', type: 'text', description: 'Name of first best practice' },
          { id: '7.2.2', name: 'Best Practice 1 - Objectives', type: 'textarea', description: 'Goals and purpose' },
          { id: '7.2.3', name: 'Best Practice 1 - Context & Practice', type: 'textarea', description: 'Implementation details' },
          { id: '7.2.4', name: 'Best Practice 1 - Evidence of Success', type: 'textarea', description: 'Impact and outcomes' },
          { id: '7.2.5', name: 'Best Practice 2 - Title', type: 'text', description: 'Name of second best practice' },
          { id: '7.2.6', name: 'Best Practice 2 - Objectives', type: 'textarea', description: 'Goals and purpose' },
          { id: '7.2.7', name: 'Best Practice 2 - Context & Practice', type: 'textarea', description: 'Implementation details' },
          { id: '7.2.8', name: 'Best Practice 2 - Evidence of Success', type: 'textarea', description: 'Impact and outcomes' },
        ]
      },
      {
        code: '7.3',
        name: 'Institutional Distinctiveness',
        description: 'Unique feature that distinguishes the institution.',
        maxMarks: 15,
        dataOwners: ['Principal', 'IQAC', 'PR Cell'],
        requiredDocs: ['Distinctiveness document', 'Supporting evidence', 'Media coverage'],
        metrics: [
          { id: '7.3.1', name: 'Institutional Distinctiveness - Title', type: 'text', description: 'Name your unique feature' },
          { id: '7.3.2', name: 'Institutional Distinctiveness - Description', type: 'textarea', description: 'Describe what makes your institution unique' },
          { id: '7.3.3', name: 'Evidence and Impact', type: 'textarea', description: 'Provide evidence of distinctiveness' },
        ]
      },
    ],
    folderStructure: ['Criterion 7/', '├── 7.1 Institutional Values/', '│   ├── Gender Equity/', '│   ├── Environment/', '│   └── Inclusivity/', '├── 7.2 Best Practices/', '└── 7.3 Distinctiveness/'],
    proTips: [
      'Document unique initiatives with photos',
      'Quantify impact of best practices',
      'Show evidence of green campus',
      'Highlight awards/recognition received'
    ]
  }
}

interface CriterionData {
  number: number
  name: string
  marks: number
  icon: string
  color: string
  purpose: string
  keyIndicators: KeyIndicatorData[]
  folderStructure: string[]
  proTips: string[]
}

interface KeyIndicatorData {
  code: string
  name: string
  description: string
  maxMarks: number
  dataOwners: string[]
  requiredDocs: string[]
  metrics: MetricData[]
}

interface MetricData {
  id: string
  name: string
  type: 'number' | 'percentage' | 'text' | 'textarea' | 'select' | 'ratio'
  unit?: string
  description: string
  options?: string[]
}

interface UploadedDocument {
  id: string
  name: string
  size: number
  type: string
  kiCode: string
  docType: string
  uploadedAt: Date
  file?: File
}

const ICONS: Record<string, any> = {
  BookOpen, GraduationCap, FileText, Building2, Users, Shield, Leaf
}

export default function CriterionPage() {
  const router = useRouter()
  const params = useParams()
  const criterionId = parseInt(params.id as string)

  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDocument[]>([])
  const [uploadingFor, setUploadingFor] = useState<{ kiCode: string; docType: string } | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [stepStatus, setStepStatus] = useState<Record<number, 'pending' | 'in_progress' | 'completed'>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  const criterion = CRITERIA_DATA[criterionId]

  useEffect(() => {
    if (criterion) {
      loadCriterionData()
    }
  }, [criterionId])

  const loadCriterionData = async () => {
    setIsLoading(true)
    try {
      await new Promise(r => setTimeout(r, 300))
      const initialData: Record<string, string> = {}
      const initialStatus: Record<number, 'pending' | 'in_progress' | 'completed'> = {}
      criterion?.keyIndicators.forEach((ki, index) => {
        ki.metrics.forEach(m => {
          initialData[m.id] = ''
        })
        initialStatus[index] = 'pending'
      })
      setFormData(initialData)
      setStepStatus(initialStatus)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await new Promise(r => setTimeout(r, 1000))
      // Mark current step as completed if all fields filled
      const currentKI = criterion?.keyIndicators[currentStep]
      if (currentKI) {
        const allFilled = currentKI.metrics.every(m => formData[m.id] && formData[m.id].trim() !== '')
        setStepStatus(prev => ({
          ...prev,
          [currentStep]: allFilled ? 'completed' : 'in_progress'
        }))
      }
      alert('Data saved successfully!')
    } finally {
      setIsSaving(false)
    }
  }

  const updateField = (id: string, value: string) => {
    setFormData(prev => ({ ...prev, [id]: value }))
    // Mark step as in progress
    if (stepStatus[currentStep] === 'pending') {
      setStepStatus(prev => ({ ...prev, [currentStep]: 'in_progress' }))
    }
  }

  const handleUploadClick = (kiCode: string, docType: string) => {
    setUploadingFor({ kiCode, docType })
    fileInputRef.current?.click()
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0 || !uploadingFor) return

    setIsUploading(true)
    try {
      const newDocs: UploadedDocument[] = []
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        const doc: UploadedDocument = {
          id: `${Date.now()}-${i}`,
          name: file.name,
          size: file.size,
          type: file.type,
          kiCode: uploadingFor.kiCode,
          docType: uploadingFor.docType,
          uploadedAt: new Date(),
          file: file
        }
        newDocs.push(doc)
      }
      await new Promise(r => setTimeout(r, 500))
      setUploadedDocs(prev => [...prev, ...newDocs])
    } finally {
      setIsUploading(false)
      setUploadingFor(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDeleteDoc = (docId: string) => {
    if (confirm('Are you sure you want to delete this document?')) {
      setUploadedDocs(prev => prev.filter(d => d.id !== docId))
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const goToNextStep = () => {
    if (criterion && currentStep < criterion.keyIndicators.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const goToPrevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const getStepProgress = (stepIndex: number) => {
    if (!criterion) return 0
    const ki = criterion.keyIndicators[stepIndex]
    const filledFields = ki.metrics.filter(m => formData[m.id] && formData[m.id].trim() !== '').length
    return Math.round((filledFields / ki.metrics.length) * 100)
  }

  const getOverallProgress = () => {
    if (!criterion) return 0
    const totalFields = criterion.keyIndicators.reduce((sum, ki) => sum + ki.metrics.length, 0)
    const filledFields = Object.values(formData).filter(v => v && v.trim() !== '').length
    return totalFields > 0 ? Math.round((filledFields / totalFields) * 100) : 0
  }

  const renderInput = (metric: MetricData) => {
    const value = formData[metric.id] || ''
    switch (metric.type) {
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => updateField(metric.id, e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded text-sm px-2.5 py-1.5 focus:outline-none focus:border-orange-500"
          >
            <option value="">Select...</option>
            {metric.options?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        )
      case 'textarea':
        return (
          <textarea
            value={value}
            onChange={(e) => updateField(metric.id, e.target.value)}
            placeholder={metric.description}
            rows={2}
            className="w-full bg-slate-800 border border-slate-700 rounded text-sm px-2.5 py-1.5 focus:outline-none focus:border-orange-500 resize-none"
          />
        )
      default:
        return (
          <div className="flex items-center gap-2">
            <input
              type={metric.type === 'number' || metric.type === 'percentage' || metric.type === 'ratio' ? 'number' : 'text'}
              value={value}
              onChange={(e) => updateField(metric.id, e.target.value)}
              placeholder="Enter value"
              className="flex-1 bg-slate-800 border border-slate-700 rounded text-sm px-2.5 py-1.5 focus:outline-none focus:border-orange-500"
            />
            {metric.unit && (
              <span className="text-xs text-slate-400 bg-slate-700 px-2 py-1.5 rounded min-w-[50px] text-center">
                {metric.unit}
              </span>
            )}
          </div>
        )
    }
  }

  if (!criterion) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold mb-2">Criterion Not Found</h1>
          <Link href="/accreditation/criteria" className="text-orange-500 hover:underline">Back to Criteria</Link>
        </div>
      </div>
    )
  }

  const CriterionIcon = ICONS[criterion.icon] || FileText
  const currentKI = criterion.keyIndicators[currentStep]
  const overallProgress = getOverallProgress()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.gif"
        className="hidden"
      />

      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/95 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-3 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={() => router.push('/accreditation/criteria')} className="p-1.5 hover:bg-slate-800 rounded transition-colors">
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div className="p-1.5 bg-orange-500/20 rounded-lg">
                <CriterionIcon className="w-4 h-4 text-orange-500" />
              </div>
              <div>
                <h1 className="font-semibold text-sm">C{criterion.number}: {criterion.name}</h1>
                <p className="text-xs text-slate-400">{criterion.marks} Marks • {criterion.keyIndicators.length} KIs</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <div className="text-xs text-slate-400">Progress</div>
                <div className="text-sm font-bold text-orange-500">{overallProgress}%</div>
              </div>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 rounded text-sm font-medium transition-colors"
              >
                {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stepper */}
      <div className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-6xl mx-auto px-3 py-2">
          <div className="flex items-center gap-1 overflow-x-auto">
            {criterion.keyIndicators.map((ki, index) => {
              const isActive = index === currentStep
              const isCompleted = stepStatus[index] === 'completed'
              const isInProgress = stepStatus[index] === 'in_progress'

              return (
                <button
                  key={ki.code}
                  onClick={() => setCurrentStep(index)}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded transition-all text-xs whitespace-nowrap ${
                    isActive ? 'bg-orange-500/20 text-orange-400' : 'hover:bg-slate-800 text-slate-400'
                  }`}
                >
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    isCompleted
                      ? 'bg-green-500 text-white'
                      : isActive
                        ? 'bg-orange-500 text-white'
                        : isInProgress
                          ? 'bg-yellow-500/30 text-yellow-400'
                          : 'bg-slate-700 text-slate-400'
                  }`}>
                    {isCompleted ? <Check className="w-3 h-3" /> : ki.code}
                  </div>
                  <span className="hidden md:inline">{ki.name.length > 15 ? ki.name.substring(0, 13) + '...' : ki.name}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-3 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Main Form */}
          <div className="lg:col-span-3 space-y-3">
            {/* Current KI Header - Compact */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                  {currentKI.code}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-sm font-semibold">{currentKI.name}</h2>
                    <span className="text-xs bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded">{currentKI.maxMarks}M</span>
                    <span className="text-xs bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">{getStepProgress(currentStep)}%</span>
                  </div>
                  <p className="text-xs text-slate-400 truncate">{currentKI.description}</p>
                </div>
                <div className="flex flex-wrap gap-1">
                  {currentKI.dataOwners.slice(0, 2).map((owner, i) => (
                    <span key={i} className="text-xs bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded">{owner}</span>
                  ))}
                  {currentKI.dataOwners.length > 2 && (
                    <span className="text-xs text-slate-500">+{currentKI.dataOwners.length - 2}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Metrics Form - Compact */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
              <h3 className="text-xs font-semibold mb-2 flex items-center gap-1.5 text-slate-300">
                <ClipboardList className="w-3.5 h-3.5 text-orange-500" />
                Quantitative Metrics
              </h3>
              <div className="space-y-2">
                {currentKI.metrics.map((metric) => (
                  <div key={metric.id} className="flex items-center gap-2">
                    <span className="text-orange-500 font-mono text-xs bg-orange-500/10 px-1.5 py-0.5 rounded w-10 text-center flex-shrink-0">
                      {metric.id}
                    </span>
                    <span className="text-xs text-slate-300 min-w-[120px] max-w-[200px] truncate flex-shrink-0" title={metric.name}>
                      {metric.name}
                    </span>
                    <div className="flex-1">
                      {renderInput(metric)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Supporting Documents - Compact */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
              <h3 className="text-xs font-semibold mb-2 flex items-center gap-1.5 text-slate-300">
                <FolderOpen className="w-3.5 h-3.5 text-green-500" />
                Documents
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {currentKI.requiredDocs.map((doc, i) => {
                  const uploadedForDoc = uploadedDocs.filter(d => d.kiCode === currentKI.code && d.docType === doc)
                  return (
                    <div key={i} className="bg-slate-800 rounded p-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-300 truncate flex-1">{doc}</span>
                        <button
                          onClick={() => handleUploadClick(currentKI.code, doc)}
                          disabled={isUploading}
                          className="flex items-center gap-1 text-xs text-orange-400 hover:text-orange-300 disabled:opacity-50 ml-2"
                        >
                          {isUploading && uploadingFor?.docType === doc ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Upload className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                      {uploadedForDoc.length > 0 && (
                        <div className="mt-1 space-y-1">
                          {uploadedForDoc.map(uploadedDoc => (
                            <div key={uploadedDoc.id} className="flex items-center justify-between text-xs bg-slate-700/50 rounded px-1.5 py-1">
                              <div className="flex items-center gap-1 flex-1 min-w-0">
                                <File className="w-3 h-3 text-blue-400 flex-shrink-0" />
                                <span className="truncate">{uploadedDoc.name}</span>
                              </div>
                              <button
                                onClick={() => handleDeleteDoc(uploadedDoc.id)}
                                className="text-slate-400 hover:text-red-400 flex-shrink-0"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Navigation - Compact */}
            <div className="flex items-center justify-between pt-2">
              <button
                onClick={goToPrevStep}
                disabled={currentStep === 0}
                className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded text-sm transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Prev
              </button>

              <span className="text-xs text-slate-500">
                {currentStep + 1}/{criterion.keyIndicators.length}
              </span>

              {currentStep === criterion.keyIndicators.length - 1 ? (
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1 px-3 py-1.5 bg-green-500 hover:bg-green-600 rounded text-sm transition-colors"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Done
                </button>
              ) : (
                <button
                  onClick={goToNextStep}
                  className="flex items-center gap-1 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 rounded text-sm transition-colors"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Sidebar - Compact */}
          <div className="space-y-3">
            {/* Progress Overview */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
              <h3 className="text-xs font-semibold mb-2 text-slate-300">Progress</h3>
              <div className="space-y-1.5">
                {criterion.keyIndicators.map((ki, index) => {
                  const progress = getStepProgress(index)
                  const isActive = index === currentStep
                  return (
                    <button
                      key={ki.code}
                      onClick={() => setCurrentStep(index)}
                      className={`w-full flex items-center gap-2 p-1.5 rounded transition-colors ${
                        isActive ? 'bg-orange-500/20' : 'hover:bg-slate-800'
                      }`}
                    >
                      <span className="text-xs font-medium w-6">{ki.code}</span>
                      <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${progress === 100 ? 'bg-green-500' : 'bg-orange-500'}`}
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 w-8">{progress}%</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Pro Tips - Compact */}
            <div className="bg-slate-900 border border-orange-500/30 rounded-lg p-3">
              <h3 className="text-xs font-semibold mb-2 flex items-center gap-1 text-orange-400">
                <Award className="w-3 h-3" />
                Tips
              </h3>
              <ul className="space-y-1">
                {criterion.proTips.slice(0, 3).map((tip, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-slate-400">
                    <CheckCircle2 className="w-3 h-3 text-green-500 mt-0.5 flex-shrink-0" />
                    <span className="line-clamp-2">{tip}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Quick Navigation - Compact */}
            <div className="flex gap-1">
              {criterionId > 1 && (
                <Link
                  href={`/accreditation/criterion/${criterionId - 1}`}
                  className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-slate-800 rounded hover:bg-slate-700 text-xs transition-colors"
                >
                  <ArrowLeft className="w-3 h-3" /> C{criterionId - 1}
                </Link>
              )}
              {criterionId < 7 && (
                <Link
                  href={`/accreditation/criterion/${criterionId + 1}`}
                  className="flex-1 flex items-center justify-center gap-1 py-1.5 bg-slate-800 rounded hover:bg-slate-700 text-xs transition-colors"
                >
                  C{criterionId + 1} <ArrowRight className="w-3 h-3" />
                </Link>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
