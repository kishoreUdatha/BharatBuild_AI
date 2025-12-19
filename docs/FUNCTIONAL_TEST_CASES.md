# BharatBuild AI - Functional Test Cases

## Document Info
- **Version:** 1.0
- **Last Updated:** 2024-12-18
- **Total Test Cases:** 85+

---

## Table of Contents
1. [Authentication & Authorization](#1-authentication--authorization)
2. [Payment & Premium Features](#2-payment--premium-features)
3. [Project Generation](#3-project-generation)
4. [Code Editor & File Management](#4-code-editor--file-management)
5. [Project Execution (Run)](#5-project-execution-run)
6. [Document Generation](#6-document-generation)
7. [Download & Export](#7-download--export)
8. [User Dashboard](#8-user-dashboard)
9. [API Security](#9-api-security)
10. [UI/UX Components](#10-uiux-components)

---

## 1. Authentication & Authorization

### TC-AUTH-001: User Registration
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | User is on registration page |
| **Test Steps** | 1. Enter valid email<br>2. Enter password (min 8 chars)<br>3. Enter full name<br>4. Click Register |
| **Expected Result** | User account created, verification email sent |
| **Postconditions** | User exists in database with `is_active=false` |

### TC-AUTH-002: User Registration - Invalid Email
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Enter invalid email format<br>2. Click Register |
| **Expected Result** | Error message: "Invalid email format" |

### TC-AUTH-003: User Registration - Weak Password
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Enter password less than 8 characters<br>2. Click Register |
| **Expected Result** | Error message: "Password must be at least 8 characters" |

### TC-AUTH-004: User Login - Valid Credentials
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | User account exists and is verified |
| **Test Steps** | 1. Enter valid email<br>2. Enter valid password<br>3. Click Login |
| **Expected Result** | User logged in, redirected to dashboard, JWT token stored |

### TC-AUTH-005: User Login - Invalid Credentials
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Enter valid email<br>2. Enter wrong password<br>3. Click Login |
| **Expected Result** | Error message: "Invalid credentials" |

### TC-AUTH-006: User Login - Rate Limiting
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Attempt login with wrong password 6 times |
| **Expected Result** | Error: "Too many attempts. Try again in X minutes" |

### TC-AUTH-007: User Logout
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | User is logged in |
| **Test Steps** | 1. Click user menu<br>2. Click Logout |
| **Expected Result** | JWT token cleared, redirected to login page, project store cleared |

### TC-AUTH-008: Password Reset Request
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Click "Forgot Password"<br>2. Enter registered email<br>3. Click Submit |
| **Expected Result** | Email sent with reset link |

### TC-AUTH-009: Session Isolation on Logout
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | User A logged in with projects |
| **Test Steps** | 1. User A logs out<br>2. User B logs in |
| **Expected Result** | User B sees only their projects, not User A's |

---

## 2. Payment & Premium Features

### TC-PAY-001: Free User - Project Limit Check
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Free user with 1 completed project |
| **Test Steps** | 1. Try to create new project |
| **Expected Result** | Error: "Project limit reached. Upgrade to Premium" |

### TC-PAY-002: Premium User - Project Limit Check
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Premium user (token purchase) with 1 completed project |
| **Test Steps** | 1. Try to create new project |
| **Expected Result** | Error: "Project limit reached" (limit is 1 per purchase) |

### TC-PAY-003: Free User - Run Button Disabled
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Free user logged in, project loaded |
| **Test Steps** | 1. Navigate to Build page<br>2. Check Run button state |
| **Expected Result** | Run button shows "Run (Premium)" with lock icon, links to /pricing |

### TC-PAY-004: Free User - Export Button Disabled
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Free user logged in, project loaded |
| **Test Steps** | 1. Check Export button in header |
| **Expected Result** | Export button shows "Export (Premium)" with lock icon |

### TC-PAY-005: Free User - Code Copy Blocked
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Free user logged in, code editor open |
| **Test Steps** | 1. Select code in editor<br>2. Press Ctrl+C |
| **Expected Result** | Copy blocked, "Copy restricted" banner visible |

### TC-PAY-006: Free User - Code Cut Blocked
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Select code in editor<br>2. Press Ctrl+X |
| **Expected Result** | Cut operation blocked |

### TC-PAY-007: Free User - Context Menu Copy Disabled
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Right-click in code editor<br>2. Check context menu |
| **Expected Result** | Copy/Cut options not visible in context menu |

### TC-PAY-008: Free User - Document Download Blocked (Project Selector)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click Project dropdown<br>2. Hover over Documents |
| **Expected Result** | Shows "Premium Feature" message with upgrade button |

### TC-PAY-009: Free User - Document Download Blocked (Build Panel)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Navigate to Documents tab<br>2. Click download on any document |
| **Expected Result** | Lock icon shown, links to /pricing |

### TC-PAY-010: Free User - Download All Blocked
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Navigate to Documents tab<br>2. Check "Download All" button |
| **Expected Result** | Shows "Download All (Premium)" with lock icon |

### TC-PAY-011: Free User - Dashboard Download Blocked
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Navigate to Dashboard<br>2. Select project<br>3. View documents<br>4. Try download |
| **Expected Result** | Lock icon shown, upgrade prompt displayed |

### TC-PAY-012: Premium User - All Features Enabled
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | User with token purchase |
| **Test Steps** | 1. Check Run button<br>2. Check Export button<br>3. Check Copy functionality<br>4. Check Downloads |
| **Expected Result** | All features enabled and functional |

### TC-PAY-013: Token Purchase Flow
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click "Upgrade to Premium"<br>2. Select token package<br>3. Complete payment |
| **Expected Result** | Tokens added, features unlocked, confirmation email sent |

---

## 3. Project Generation

### TC-PROJ-001: Create New Project
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | User logged in, under project limit |
| **Test Steps** | 1. Enter project description<br>2. Click Generate |
| **Expected Result** | Project stages progress (Abstract → Plan → Build → Documents → Summary) |

### TC-PROJ-002: Project Generation - Stage Progress
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Start project generation<br>2. Monitor left panel |
| **Expected Result** | Each stage shows progress, completed stages show checkmark |

### TC-PROJ-003: User Prompt Display
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Enter project description<br>2. Submit |
| **Expected Result** | User prompt appears as right-aligned violet bubble in left panel |

### TC-PROJ-004: Project Files Generated
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Complete project generation<br>2. Check File Explorer |
| **Expected Result** | Project files visible in file tree (frontend/backend structure) |

### TC-PROJ-005: Code Editor Display
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click on a file in File Explorer |
| **Expected Result** | File content displayed in Monaco editor with syntax highlighting |

### TC-PROJ-006: Project Switch
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Open Project dropdown<br>2. Select different project |
| **Expected Result** | New project loaded, files updated, editor cleared |

### TC-PROJ-007: Auto-Save Functionality
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Edit file in code editor<br>2. Wait 2 seconds |
| **Expected Result** | "Saving..." indicator, then "Saved" with green checkmark |

---

## 4. Code Editor & File Management

### TC-EDIT-001: Open File in Editor
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click file in File Explorer |
| **Expected Result** | File opens in editor with correct syntax highlighting |

### TC-EDIT-002: Multiple Tabs
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Open multiple files |
| **Expected Result** | Each file opens in separate tab |

### TC-EDIT-003: Close Tab
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Click X on file tab |
| **Expected Result** | Tab closed, next tab becomes active |

### TC-EDIT-004: Unsaved Changes Indicator
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Edit file content |
| **Expected Result** | Tab shows dot/asterisk indicating unsaved changes |

### TC-EDIT-005: Markdown Preview
| Field | Value |
|-------|-------|
| **Priority** | Low |
| **Test Steps** | 1. Open .md file<br>2. Toggle preview mode |
| **Expected Result** | Split view showing markdown source and rendered preview |

### TC-EDIT-006: Theme Toggle
| Field | Value |
|-------|-------|
| **Priority** | Low |
| **Test Steps** | 1. Click theme toggle in editor header |
| **Expected Result** | Editor switches between dark/light themes |

---

## 5. Project Execution (Run)

### TC-RUN-001: Run Project (Premium User)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Premium user, project with valid code |
| **Test Steps** | 1. Click Run button |
| **Expected Result** | Terminal opens, npm install runs, dev server starts, preview URL displayed |

### TC-RUN-002: Stop Project
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Project running |
| **Test Steps** | 1. Click Stop button |
| **Expected Result** | Docker container stopped, terminal shows "Stopped" |

### TC-RUN-003: Live Preview
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Project running |
| **Test Steps** | 1. Click Preview tab |
| **Expected Result** | Running application displayed in iframe |

### TC-RUN-004: Terminal Output Streaming
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Run project<br>2. Watch terminal |
| **Expected Result** | Real-time streaming of npm/build output |

### TC-RUN-005: Auto-Fixer on Error (Premium)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Premium user, project with intentional error |
| **Test Steps** | 1. Run project<br>2. Wait for error |
| **Expected Result** | Auto-fixer detects error, proposes fix, applies fix, restarts |

### TC-RUN-006: Run Button Blocked (Free User)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Free user |
| **Test Steps** | 1. Click Run button |
| **Expected Result** | Button shows lock, redirects to /pricing |

### TC-RUN-007: Backend API - Run Blocked Without code_execution Feature
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Free user calls POST /api/v1/execution/run/{project_id} directly |
| **Expected Result** | 403 Forbidden: "Feature 'code_execution' requires Premium plan" |

---

## 6. Document Generation

### TC-DOC-001: Generate Project Report
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Premium user, project code generated |
| **Test Steps** | 1. Navigate to Documents tab<br>2. Click "Generate Project Report" |
| **Expected Result** | 60-80 page report generated, saved to S3 |

### TC-DOC-002: Generate SRS Document
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click "Generate SRS" |
| **Expected Result** | IEEE 830 compliant SRS document generated |

### TC-DOC-003: Generate PPT Presentation
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click "Generate PPT" |
| **Expected Result** | 20-25 slide presentation generated (.pptx) |

### TC-DOC-004: Generate Viva Q&A
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Click "Generate Viva Q&A" |
| **Expected Result** | Comprehensive Q&A document generated |

### TC-DOC-005: Document Generation Progress
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Start document generation<br>2. Watch progress |
| **Expected Result** | SSE stream shows section-by-section progress |

### TC-DOC-006: Project Completion After All Documents
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Generate all 4 document types |
| **Expected Result** | Project status changes to COMPLETED, counts against project limit |

### TC-DOC-007: Document Generation Blocked (Free User)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Free user tries to generate document |
| **Expected Result** | 403: "Document generation requires Premium plan" |

---

## 7. Download & Export

### TC-DL-001: Download Single Document (Premium)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | Premium user, document generated |
| **Test Steps** | 1. Click download button on document |
| **Expected Result** | Document downloaded (.docx/.pptx) |

### TC-DL-002: Download All Documents (Premium)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click "Download All" |
| **Expected Result** | ZIP file downloaded with all documents |

### TC-DL-003: Export Project as ZIP (Premium)
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Click Export button |
| **Expected Result** | ZIP file downloaded with all project files (excluding node_modules) |

### TC-DL-004: Download Blocked (Free User) - Frontend
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Free user clicks download button |
| **Expected Result** | Lock icon shown, redirects to /pricing |

### TC-DL-005: Download Blocked (Free User) - Backend API
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Free user calls GET /api/v1/documents/download/{project_id}/srs directly |
| **Expected Result** | 403 Forbidden: "Feature 'download_files' requires Premium plan" |

### TC-DL-006: Export Blocked (Free User) - Backend API
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Free user calls GET /api/v1/execution/export/{project_id} directly |
| **Expected Result** | 403 Forbidden: "Feature 'download_files' requires Premium plan" |

### TC-DL-007: Download from Project Selector Dropdown
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Open project dropdown<br>2. Click Documents<br>3. Click document type |
| **Expected Result** | Premium: downloads file. Free: shows upgrade prompt |

---

## 8. User Dashboard

### TC-DASH-001: View Projects List
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Preconditions** | User logged in with projects |
| **Test Steps** | 1. Navigate to Dashboard |
| **Expected Result** | List of user's projects displayed with status |

### TC-DASH-002: Project Card Actions
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Click "Open" on project card |
| **Expected Result** | Navigates to Build page with project loaded |

### TC-DASH-003: View Project Documents
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Click "Documents" on project card |
| **Expected Result** | Documents panel opens showing available documents |

### TC-DASH-004: Token Usage Display
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Check token analytics section |
| **Expected Result** | Shows tokens used, remaining, usage breakdown |

### TC-DASH-005: User Profile Update
| Field | Value |
|-------|-------|
| **Priority** | Low |
| **Test Steps** | 1. Navigate to Profile<br>2. Update college name<br>3. Save |
| **Expected Result** | Profile updated, used in document generation |

---

## 9. API Security

### TC-SEC-001: Unauthenticated API Access
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Call protected endpoint without JWT token |
| **Expected Result** | 401 Unauthorized |

### TC-SEC-002: Access Another User's Project
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. User A tries to access User B's project via API |
| **Expected Result** | 404 Not Found (not 403, to prevent enumeration) |

### TC-SEC-003: Rate Limiting - Login Endpoint
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Make 6 login requests in 1 minute |
| **Expected Result** | 429 Too Many Requests with Retry-After header |

### TC-SEC-004: Rate Limiting - AI Endpoints
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Free user makes 61 API calls in 1 minute |
| **Expected Result** | 429 Too Many Requests |

### TC-SEC-005: SQL Injection Prevention
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Enter SQL injection in project name: `'; DROP TABLE users; --` |
| **Expected Result** | Input sanitized, no SQL executed |

### TC-SEC-006: XSS Prevention
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Enter `<script>alert('xss')</script>` in project description |
| **Expected Result** | Script tags escaped, not executed |

### TC-SEC-007: JWT Token Expiry
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Wait for token to expire<br>2. Make API call |
| **Expected Result** | 401 Unauthorized, user prompted to login again |

---

## 10. UI/UX Components

### TC-UI-001: Responsive Layout - Desktop
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. View app on 1920x1080 screen |
| **Expected Result** | Left panel (22%), Right panel (78%), all elements visible |

### TC-UI-002: Responsive Layout - Mobile
| Field | Value |
|-------|-------|
| **Priority** | Low |
| **Test Steps** | 1. View app on mobile screen |
| **Expected Result** | Panels stack vertically, touch-friendly buttons |

### TC-UI-003: Loading States
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Start any async operation |
| **Expected Result** | Loading spinner shown, buttons disabled |

### TC-UI-004: Error Messages
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Trigger an error (e.g., network failure) |
| **Expected Result** | User-friendly error message displayed |

### TC-UI-005: Dark Theme Consistency
| Field | Value |
|-------|-------|
| **Priority** | Low |
| **Test Steps** | 1. Check all pages in dark mode |
| **Expected Result** | Consistent dark theme colors throughout |

### TC-UI-006: Premium Feature Visual Indicators
| Field | Value |
|-------|-------|
| **Priority** | High |
| **Test Steps** | 1. Check all locked features as free user |
| **Expected Result** | All locked features show amber/gold color, lock icon, links to /pricing |

### TC-UI-007: Chat Message Alignment
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Enter prompt in chat input |
| **Expected Result** | User message appears right-aligned in violet bubble |

### TC-UI-008: Project Stages Progress Bar
| Field | Value |
|-------|-------|
| **Priority** | Medium |
| **Test Steps** | 1. Generate project<br>2. Watch progress bar |
| **Expected Result** | Progress bar fills as stages complete |

---

## Test Execution Summary Template

| Category | Total | Passed | Failed | Blocked | Not Run |
|----------|-------|--------|--------|---------|---------|
| Authentication | 9 | | | | |
| Payment & Premium | 13 | | | | |
| Project Generation | 7 | | | | |
| Code Editor | 6 | | | | |
| Project Execution | 7 | | | | |
| Document Generation | 7 | | | | |
| Download & Export | 7 | | | | |
| User Dashboard | 5 | | | | |
| API Security | 7 | | | | |
| UI/UX | 8 | | | | |
| **TOTAL** | **76** | | | | |

---

## Defect Severity Definitions

| Severity | Definition | Example |
|----------|------------|---------|
| **Critical** | System crash, data loss, security breach | User can access another user's data |
| **High** | Feature completely broken | Run button doesn't work for premium users |
| **Medium** | Feature partially broken, workaround exists | Auto-save takes 10 seconds instead of 2 |
| **Low** | Cosmetic issue, minor inconvenience | Button color slightly off |

---

## Test Environment Requirements

### Frontend Testing
- Browser: Chrome 120+, Firefox 120+, Safari 17+
- Screen: 1920x1080 (desktop), 375x812 (mobile)

### Backend Testing
- API Client: Postman, curl, or httpie
- Database: PostgreSQL with test data

### User Accounts Needed
1. Free user (no purchases)
2. Premium user (with token purchase)
3. Admin user
4. User with expired tokens

---

## Notes

1. **Payment tests** require sandbox/test payment gateway
2. **Rate limiting tests** should be run in isolation
3. **Security tests** should be performed by security team
4. **Performance tests** not included (separate document)
