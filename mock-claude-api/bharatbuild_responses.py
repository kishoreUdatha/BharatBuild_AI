"""
BharatBuild AI Mock Responses
=============================
Realistic mock responses matching BharatBuild's XML format:
- <plan> for Planner Agent
- <file> for Writer Agent
- <fix> for Fixer Agent
- <thinking>, <terminal>, <error> for various agents
"""

# ============================================
# PLANNER AGENT RESPONSES
# ============================================

PLANNER_RESPONSE_REACT_APP = """<plan>
  <project_name>Modern React Application</project_name>
  <project_description>A beautiful, responsive React application built with TypeScript, Vite, and Tailwind CSS. Features a modern dark theme with glassmorphism effects.</project_description>
  <project_type>Commercial Application</project_type>
  <complexity>Intermediate</complexity>

  <tech_stack>
    <category name="Frontend">React 18, Vite, TypeScript</category>
    <category name="Styling">Tailwind CSS, Lucide Icons</category>
    <category name="State">React Hooks (useState, useEffect)</category>
  </tech_stack>

  <files>
    <file path="package.json" priority="1">
      <description>NPM configuration with React 18, Vite, TypeScript, Tailwind CSS, and Lucide React icons</description>
    </file>
    <file path="index.html" priority="2">
      <description>HTML entry point with root div and Vite module script</description>
    </file>
    <file path="vite.config.ts" priority="3">
      <description>Vite configuration with React plugin and path aliases</description>
    </file>
    <file path="tailwind.config.js" priority="4">
      <description>Tailwind CSS configuration with custom colors, animations, and dark theme</description>
    </file>
    <file path="postcss.config.js" priority="5">
      <description>PostCSS configuration for Tailwind CSS processing</description>
    </file>
    <file path="tsconfig.json" priority="6">
      <description>TypeScript configuration with strict mode and React JSX support</description>
    </file>
    <file path="tsconfig.node.json" priority="7">
      <description>TypeScript configuration for Vite node environment</description>
    </file>
    <file path="src/main.tsx" priority="8">
      <description>React entry point that renders App component to root element</description>
    </file>
    <file path="src/index.css" priority="9">
      <description>Global CSS with Tailwind directives, custom animations, and dark theme styles</description>
    </file>
    <file path="src/App.tsx" priority="10">
      <description>Main App component with routing, state management, and layout structure</description>
    </file>
    <file path="src/components/Header.tsx" priority="11">
      <description>Navigation header with logo, menu items, and responsive mobile menu</description>
    </file>
    <file path="src/components/Hero.tsx" priority="12">
      <description>Hero section with gradient background, headline, and CTA buttons</description>
    </file>
    <file path="src/components/Features.tsx" priority="13">
      <description>Features grid showcasing key functionality with icons and descriptions</description>
    </file>
    <file path="src/components/Footer.tsx" priority="14">
      <description>Footer with links, social icons, and copyright information</description>
    </file>
  </files>

  <features>
    <feature icon="🎨" name="Modern UI">Beautiful dark theme with glassmorphism and gradient effects</feature>
    <feature icon="⚡" name="Fast Performance">Vite-powered with lazy loading and code splitting</feature>
    <feature icon="📱" name="Responsive">Mobile-first design that works on all devices</feature>
    <feature icon="🔧" name="TypeScript">Full type safety with TypeScript strict mode</feature>
  </features>
</plan>"""

PLANNER_RESPONSE_TODO_APP = """<plan>
  <project_name>Task Manager Pro</project_name>
  <project_description>A feature-rich todo application with categories, priorities, due dates, and local storage persistence. Built with React and TypeScript.</project_description>
  <project_type>Prototype/MVP</project_type>
  <complexity>Intermediate</complexity>

  <tech_stack>
    <category name="Frontend">React 18, Vite, TypeScript</category>
    <category name="Styling">Tailwind CSS, Lucide Icons</category>
    <category name="Storage">localStorage for persistence</category>
  </tech_stack>

  <files>
    <file path="package.json" priority="1">
      <description>NPM configuration with React, TypeScript, Tailwind, and date-fns for date handling</description>
    </file>
    <file path="index.html" priority="2">
      <description>HTML entry point with root div</description>
    </file>
    <file path="vite.config.ts" priority="3">
      <description>Vite configuration with React plugin</description>
    </file>
    <file path="tailwind.config.js" priority="4">
      <description>Tailwind config with custom colors for priority levels</description>
    </file>
    <file path="postcss.config.js" priority="5">
      <description>PostCSS configuration</description>
    </file>
    <file path="tsconfig.json" priority="6">
      <description>TypeScript configuration</description>
    </file>
    <file path="src/main.tsx" priority="7">
      <description>React entry point</description>
    </file>
    <file path="src/index.css" priority="8">
      <description>Global styles with Tailwind and custom animations</description>
    </file>
    <file path="src/App.tsx" priority="9">
      <description>Main app with todo state management and filtering logic</description>
    </file>
    <file path="src/types/index.ts" priority="10">
      <description>TypeScript interfaces for Todo, Category, and Priority types</description>
    </file>
    <file path="src/components/TodoList.tsx" priority="11">
      <description>List component displaying todos with drag-drop reordering</description>
    </file>
    <file path="src/components/TodoItem.tsx" priority="12">
      <description>Individual todo item with checkbox, edit, and delete actions</description>
    </file>
    <file path="src/components/AddTodo.tsx" priority="13">
      <description>Form for adding new todos with category and priority selection</description>
    </file>
    <file path="src/components/FilterBar.tsx" priority="14">
      <description>Filter controls for status, category, and priority</description>
    </file>
    <file path="src/hooks/useLocalStorage.ts" priority="15">
      <description>Custom hook for persistent localStorage state</description>
    </file>
  </files>

  <features>
    <feature icon="✅" name="Task Management">Create, edit, and delete tasks with ease</feature>
    <feature icon="🏷️" name="Categories">Organize tasks into custom categories</feature>
    <feature icon="⭐" name="Priorities">Set high, medium, or low priority levels</feature>
    <feature icon="💾" name="Persistence">Tasks saved to localStorage automatically</feature>
  </features>
</plan>"""

PLANNER_RESPONSE_ACADEMIC = """<plan>
  <project_name>Student Project Portal</project_name>
  <project_description>A comprehensive academic project management system for college students. Includes project submission, tracking, and documentation features.</project_description>
  <project_type>Academic/Student Project</project_type>
  <complexity>Advanced</complexity>

  <tech_stack>
    <category name="Frontend">React 18, Vite, TypeScript</category>
    <category name="Styling">Tailwind CSS, Lucide Icons</category>
    <category name="State">React Context API</category>
  </tech_stack>

  <files>
    <file path="package.json" priority="1">
      <description>NPM configuration with all dependencies</description>
    </file>
    <file path="index.html" priority="2">
      <description>HTML entry point</description>
    </file>
    <file path="vite.config.ts" priority="3">
      <description>Vite configuration</description>
    </file>
    <file path="tailwind.config.js" priority="4">
      <description>Tailwind configuration</description>
    </file>
    <file path="postcss.config.js" priority="5">
      <description>PostCSS configuration</description>
    </file>
    <file path="tsconfig.json" priority="6">
      <description>TypeScript configuration</description>
    </file>
    <file path="src/main.tsx" priority="7">
      <description>React entry point</description>
    </file>
    <file path="src/index.css" priority="8">
      <description>Global styles</description>
    </file>
    <file path="src/App.tsx" priority="9">
      <description>Main application component</description>
    </file>
    <file path="src/components/Dashboard.tsx" priority="10">
      <description>Student dashboard with project overview</description>
    </file>
    <file path="src/components/ProjectCard.tsx" priority="11">
      <description>Project card displaying status and details</description>
    </file>
    <file path="src/components/SubmissionForm.tsx" priority="12">
      <description>Form for submitting new projects</description>
    </file>
    <file path="docs/SRS.md" priority="20">
      <description>Software Requirements Specification document</description>
    </file>
    <file path="docs/ARCHITECTURE.md" priority="21">
      <description>System architecture and design documentation</description>
    </file>
    <file path="README.md" priority="22">
      <description>Project overview and setup instructions</description>
    </file>
  </files>

  <features>
    <feature icon="📚" name="Academic Focus">Designed for college project requirements</feature>
    <feature icon="📝" name="Documentation">Includes SRS and architecture docs</feature>
    <feature icon="📊" name="Progress Tracking">Track project milestones and deadlines</feature>
    <feature icon="👥" name="Collaboration">Team management features</feature>
  </features>
</plan>"""


# ============================================
# WRITER AGENT RESPONSES
# ============================================

WRITER_RESPONSE_PACKAGE_JSON = """<file path="package.json">
{
  "name": "bharatbuild-project",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "lucide-react": "^0.312.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.12"
  }
}
</file>"""

WRITER_RESPONSE_INDEX_HTML = """<file path="index.html">
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BharatBuild Project</title>
  </head>
  <body class="bg-gray-900 text-white">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
</file>"""

WRITER_RESPONSE_VITE_CONFIG = """<file path="vite.config.ts">
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true
  }
})
</file>"""

WRITER_RESPONSE_TAILWIND_CONFIG = """<file path="tailwind.config.js">
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          500: '#8b5cf6',
          600: '#7c3aed',
        },
        dark: {
          900: '#0a0a0f',
          800: '#111827',
          700: '#1a1a2e',
        }
      },
      animation: {
        'blob': 'blob 7s infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        blob: {
          '0%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
          '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
          '100%': { transform: 'translate(0px, 0px) scale(1)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      }
    },
  },
  plugins: [],
}
</file>"""

WRITER_RESPONSE_APP_TSX = """<file path="src/App.tsx">
import { useState } from 'react'
import { Home, Settings, User, Bell, Menu, X } from 'lucide-react'

function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-gray-900">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/5 backdrop-blur-xl border-b border-white/10">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <span className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                BharatBuild
              </span>
            </div>

            <div className="hidden md:flex items-center space-x-8">
              <a href="#" className="text-gray-300 hover:text-white transition-colors flex items-center gap-2">
                <Home size={18} /> Home
              </a>
              <a href="#" className="text-gray-300 hover:text-white transition-colors flex items-center gap-2">
                <User size={18} /> About
              </a>
              <a href="#" className="text-gray-300 hover:text-white transition-colors flex items-center gap-2">
                <Settings size={18} /> Settings
              </a>
            </div>

            <button
              className="md:hidden text-gray-300 hover:text-white"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="pt-16">
        <section className="min-h-screen flex items-center justify-center px-4">
          <div className="text-center max-w-4xl mx-auto">
            <h1 className="text-5xl md:text-7xl font-bold text-white mb-6">
              Build Something
              <span className="block bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                Amazing
              </span>
            </h1>
            <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
              Create stunning applications with modern technologies.
              Fast, beautiful, and production-ready.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="px-8 py-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-purple-500/50 hover:scale-105 transition-all">
                Get Started
              </button>
              <button className="px-8 py-4 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all">
                Learn More
              </button>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-20 px-4">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-3xl font-bold text-white text-center mb-12">Features</h2>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                { icon: '⚡', title: 'Lightning Fast', desc: 'Optimized for performance' },
                { icon: '🎨', title: 'Beautiful UI', desc: 'Modern design patterns' },
                { icon: '🔧', title: 'Easy to Use', desc: 'Developer friendly' },
              ].map((feature, i) => (
                <div
                  key={i}
                  className="p-6 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 hover:border-purple-500/50 transition-all"
                >
                  <div className="text-4xl mb-4">{feature.icon}</div>
                  <h3 className="text-xl font-bold text-white mb-2">{feature.title}</h3>
                  <p className="text-gray-400">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="py-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 text-center text-gray-400">
          <p>&copy; 2024 BharatBuild. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

export default App
</file>"""

WRITER_RESPONSE_MAIN_TSX = """<file path="src/main.tsx">
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
</file>"""

WRITER_RESPONSE_INDEX_CSS = """<file path="src/index.css">
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #0a0a0f;
  --bg-secondary: #111827;
  --text-primary: #ffffff;
  --text-secondary: #9ca3af;
  --accent-purple: #8b5cf6;
  --accent-pink: #ec4899;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--accent-purple);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--accent-pink);
}

/* Glassmorphism utility */
.glass {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Gradient text utility */
.gradient-text {
  background: linear-gradient(to right, var(--accent-purple), var(--accent-pink));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Animation utilities */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out forwards;
}
</file>"""


# ============================================
# FIXER AGENT RESPONSES
# ============================================

FIXER_RESPONSE = """<fix>
  <analysis>The error occurred because the component was missing a required import statement and had an incorrect type definition.</analysis>

  <patch file="src/App.tsx">
--- src/App.tsx
+++ src/App.tsx
@@ -1,4 +1,5 @@
 import { useState } from 'react'
+import { useEffect } from 'react'
 import { Home, Settings, User } from 'lucide-react'

 function App() {
@@ -10,7 +11,7 @@
-  const [count, setCount] = useState(0)
+  const [count, setCount] = useState<number>(0)

   return (
  </patch>

  <notes>Added missing useEffect import and fixed the useState type annotation to be explicit.</notes>
</fix>"""


# ============================================
# VERIFIER AGENT RESPONSES
# ============================================

VERIFIER_RESPONSE_SUCCESS = """{
  "status": "success",
  "files_verified": 10,
  "issues": [],
  "summary": "All files pass verification. No syntax errors or missing dependencies detected."
}"""

VERIFIER_RESPONSE_ISSUES = """{
  "status": "issues_found",
  "files_verified": 10,
  "issues": [
    {
      "file": "src/App.tsx",
      "line": 15,
      "severity": "error",
      "message": "Missing import for 'useEffect'"
    },
    {
      "file": "src/components/Header.tsx",
      "line": 8,
      "severity": "warning",
      "message": "Unused variable 'isOpen'"
    }
  ],
  "summary": "Found 1 error and 1 warning that need to be addressed."
}"""


# ============================================
# TERMINAL / SHELL RESPONSES
# ============================================

TERMINAL_RESPONSE = """<terminal>
npm install
npm run dev
</terminal>"""


# ============================================
# THINKING RESPONSES
# ============================================

THINKING_RESPONSE = """<thinking>
Analyzing the user request to determine the best approach:

1. Project Type: This appears to be a web application project
2. Tech Stack: React with TypeScript and Tailwind CSS is optimal
3. Complexity: Intermediate - requires multiple components
4. Key Features: Modern UI, responsive design, dark theme

I will create a comprehensive file structure with:
- Configuration files (package.json, vite.config.ts, tailwind.config.js)
- Entry files (main.tsx, App.tsx)
- Reusable components (Header, Footer, Features)
- Styling (index.css with Tailwind)
</thinking>"""


# ============================================
# RESPONSE SELECTOR
# ============================================

def get_bharatbuild_response(system_prompt: str, user_prompt: str) -> str:
    """
    Select appropriate mock response based on system prompt and user input.
    Matches BharatBuild's agent-specific response formats.
    """
    system_lower = system_prompt.lower() if system_prompt else ""
    user_lower = user_prompt.lower() if user_prompt else ""

    # Detect agent type from system prompt
    if "planner" in system_lower or "planner agent" in system_lower:
        # Return planner-style <plan> response
        if any(word in user_lower for word in ["todo", "task", "list"]):
            return PLANNER_RESPONSE_TODO_APP
        elif any(word in user_lower for word in ["academic", "student", "college", "university"]):
            return PLANNER_RESPONSE_ACADEMIC
        else:
            return PLANNER_RESPONSE_REACT_APP

    elif "writer" in system_lower or "writer agent" in system_lower:
        # Return writer-style <file> response based on requested file
        if "package.json" in user_lower:
            return WRITER_RESPONSE_PACKAGE_JSON
        elif "index.html" in user_lower:
            return WRITER_RESPONSE_INDEX_HTML
        elif "vite.config" in user_lower:
            return WRITER_RESPONSE_VITE_CONFIG
        elif "tailwind.config" in user_lower:
            return WRITER_RESPONSE_TAILWIND_CONFIG
        elif "app.tsx" in user_lower:
            return WRITER_RESPONSE_APP_TSX
        elif "main.tsx" in user_lower:
            return WRITER_RESPONSE_MAIN_TSX
        elif "index.css" in user_lower:
            return WRITER_RESPONSE_INDEX_CSS
        else:
            # Default component
            return WRITER_RESPONSE_APP_TSX

    elif "fixer" in system_lower or "fix" in system_lower:
        return FIXER_RESPONSE

    elif "verifier" in system_lower or "verify" in system_lower:
        if any(word in user_lower for word in ["error", "issue", "problem"]):
            return VERIFIER_RESPONSE_ISSUES
        return VERIFIER_RESPONSE_SUCCESS

    elif "runner" in system_lower or "terminal" in system_lower:
        return TERMINAL_RESPONSE

    elif "documenter" in system_lower or "document" in system_lower or "documentation" in system_lower:
        return DOCUMENTER_RESPONSE

    # Default: thinking + planner response
    return THINKING_RESPONSE + "\n\n" + PLANNER_RESPONSE_REACT_APP


# ============================================
# DOCUMENTER AGENT RESPONSES
# ============================================

DOCUMENTER_RESPONSE = """<documents>
  <front_matter>
    <cover_page>
# [COLLEGE_NAME]
## [UNIVERSITY_NAME]
### Department of Computer Science and Engineering

---

# PROJECT REPORT
## On
# [PROJECT_NAME]

**Submitted in partial fulfillment of the requirements for the award of the degree of**

### Bachelor of Technology
### in
### Computer Science and Engineering

**Submitted By:**

| S.No | Name | Roll Number |
|------|------|-------------|
| 1 | [STUDENT_NAME_1] | [ROLL_NO_1] |
| 2 | [STUDENT_NAME_2] | [ROLL_NO_2] |
| 3 | [STUDENT_NAME_3] | [ROLL_NO_3] |
| 4 | [STUDENT_NAME_4] | [ROLL_NO_4] |

**Under the Guidance of**
**[GUIDE_NAME]**
**[GUIDE_DESIGNATION]**

**Academic Year: 2024-2025**
    </cover_page>

    <certificate>
# CERTIFICATE

This is to certify that the project entitled **"[PROJECT_NAME]"** is a bonafide work carried out by the following students:

| S.No | Name | Roll Number |
|------|------|-------------|
| 1 | [STUDENT_NAME_1] | [ROLL_NO_1] |
| 2 | [STUDENT_NAME_2] | [ROLL_NO_2] |
| 3 | [STUDENT_NAME_3] | [ROLL_NO_3] |
| 4 | [STUDENT_NAME_4] | [ROLL_NO_4] |

in partial fulfillment of the requirements for the award of the degree of **Bachelor of Technology in Computer Science and Engineering** from **[UNIVERSITY_NAME]** during the academic year **2024-2025**.

This project work has not been submitted elsewhere for any other degree or diploma.

---

**Project Guide**                    **Head of Department**                    **Principal**
[GUIDE_NAME]                         [HOD_NAME]                                [PRINCIPAL_NAME]
[GUIDE_DESIGNATION]                  Professor & HOD, CSE                      [COLLEGE_NAME]

---

**External Examiner**
Date: ____________
    </certificate>

    <declaration>
# DECLARATION

We, the undersigned, hereby declare that:

1. The project entitled **"[PROJECT_NAME]"** submitted to **[COLLEGE_NAME]** affiliated to **[UNIVERSITY_NAME]** is a record of original work done by us under the guidance of **[GUIDE_NAME]**, [GUIDE_DESIGNATION], Department of Computer Science and Engineering.

2. This project work has not been submitted to any other University or Institution for the award of any degree or diploma.

3. We have followed all the guidelines and regulations prescribed by the university for the preparation of this project report.

4. All the sources of information and literature used in this project have been duly acknowledged.

**Place:** [CITY]
**Date:** [DATE]

---

**Student Signatures:**

1. [STUDENT_NAME_1] - [ROLL_NO_1]
2. [STUDENT_NAME_2] - [ROLL_NO_2]
3. [STUDENT_NAME_3] - [ROLL_NO_3]
4. [STUDENT_NAME_4] - [ROLL_NO_4]
    </declaration>

    <acknowledgement>
# ACKNOWLEDGEMENT

We would like to express our sincere gratitude to our project guide **[GUIDE_NAME]**, [GUIDE_DESIGNATION], Department of Computer Science and Engineering, for the valuable guidance, constant encouragement, and support throughout the development of this project.

We extend our heartfelt thanks to **[HOD_NAME]**, Professor and Head, Department of Computer Science and Engineering, for providing us with the necessary facilities and support to carry out this project work.

We are deeply grateful to **[PRINCIPAL_NAME]**, Principal, [COLLEGE_NAME], for providing us with an excellent academic environment and infrastructure.

We would like to thank all the faculty members of the Department of Computer Science and Engineering for their valuable suggestions and encouragement during the project.

We also thank the non-teaching staff of the department for their cooperation and assistance in completing this project successfully.

Finally, we express our gratitude to our parents, family members, and friends for their continuous support, motivation, and encouragement throughout this project.

---

**[STUDENT_NAMES]**
    </acknowledgement>

    <table_of_contents>
# TABLE OF CONTENTS

| Chapter | Title | Page No. |
|---------|-------|----------|
| | Certificate | ii |
| | Declaration | iii |
| | Acknowledgement | iv |
| | Abstract | v |
| | List of Figures | vii |
| | List of Tables | viii |
| | List of Abbreviations | ix |
| 1 | Introduction | 1 |
| 1.1 | Overview | 1 |
| 1.2 | Problem Statement | 3 |
| 1.3 | Objectives | 4 |
| 1.4 | Scope of the Project | 5 |
| 1.5 | Methodology | 6 |
| 1.6 | Organization of Report | 7 |
| 2 | Literature Survey | 8 |
| 2.1 | Existing Systems Analysis | 8 |
| 2.2 | Comparative Analysis | 13 |
| 2.3 | Technology Review | 15 |
| 2.4 | Research Gap | 17 |
| 3 | System Analysis & Requirements | 18 |
| 3.1 | Introduction | 18 |
| 3.2 | Overall Description | 19 |
| 3.3 | Functional Requirements | 21 |
| 3.4 | Non-Functional Requirements | 28 |
| 4 | System Design | 30 |
| 4.1 | System Architecture | 30 |
| 4.2 | UML Diagrams | 32 |
| 4.3 | Database Design | 38 |
| 4.4 | User Interface Design | 40 |
| 5 | Implementation | 42 |
| 5.1 | Development Environment | 42 |
| 5.2 | Module Description | 43 |
| 5.3 | API Documentation | 48 |
| 5.4 | Security Implementation | 50 |
| 6 | Testing & Results | 52 |
| 6.1 | Testing Methodology | 52 |
| 6.2 | Test Cases | 53 |
| 6.3 | Test Results | 57 |
| 6.4 | Screenshots | 58 |
| 7 | Conclusion & Future Scope | 60 |
| 7.1 | Conclusion | 60 |
| 7.2 | Future Enhancements | 62 |
| | References | 64 |
| | Appendices | 67 |
    </table_of_contents>

    <list_of_figures>
# LIST OF FIGURES

| Figure No. | Title | Page No. |
|------------|-------|----------|
| 4.1 | System Architecture Diagram | 30 |
| 4.2 | Use Case Diagram | 32 |
| 4.3 | Class Diagram | 34 |
| 4.4 | Sequence Diagram - User Login | 35 |
| 4.5 | Sequence Diagram - Main Feature | 36 |
| 4.6 | Activity Diagram | 37 |
| 4.7 | ER Diagram | 38 |
| 4.8 | Home Page Wireframe | 40 |
| 4.9 | Dashboard Wireframe | 41 |
| 6.1 | Login Page Screenshot | 58 |
| 6.2 | Dashboard Screenshot | 58 |
| 6.3 | Feature Screenshot | 59 |
    </list_of_figures>

    <list_of_tables>
# LIST OF TABLES

| Table No. | Title | Page No. |
|-----------|-------|----------|
| 2.1 | Comparative Analysis of Existing Systems | 13 |
| 3.1 | Functional Requirements Summary | 21 |
| 3.2 | Non-Functional Requirements Summary | 28 |
| 4.1 | Database Tables Description | 39 |
| 5.1 | API Endpoints | 48 |
| 6.1 | Test Cases | 53 |
| 6.2 | Test Results Summary | 57 |
    </list_of_tables>

    <list_of_abbreviations>
# LIST OF ABBREVIATIONS

| Abbreviation | Full Form |
|--------------|-----------|
| API | Application Programming Interface |
| CSS | Cascading Style Sheets |
| DB | Database |
| HTML | HyperText Markup Language |
| HTTP | HyperText Transfer Protocol |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| REST | Representational State Transfer |
| SRS | Software Requirements Specification |
| UI | User Interface |
| UML | Unified Modeling Language |
| URL | Uniform Resource Locator |
    </list_of_abbreviations>
  </front_matter>

  <abstract>
# ABSTRACT

**Background:** In today's digital era, web applications have become essential tools for managing information and streamlining processes. The rapid advancement in web technologies has enabled developers to create sophisticated, user-friendly applications that can handle complex operations efficiently.

**Problem Statement:** Traditional methods of managing [domain-specific tasks] are often time-consuming, error-prone, and lack real-time accessibility. There is a pressing need for a modern, efficient solution that can address these limitations while providing a seamless user experience.

**Objectives:**
- To develop a responsive web application using modern technologies
- To implement secure user authentication and authorization
- To provide an intuitive user interface for efficient task management
- To ensure data persistence and reliability

**Methodology:** The project follows an agile development methodology with iterative development cycles. The frontend is developed using React with TypeScript and Tailwind CSS, while the backend utilizes a RESTful API architecture. The application employs modern security practices including JWT-based authentication.

**Results:** The developed system successfully addresses the identified problems by providing a fast, secure, and user-friendly platform. Performance testing shows response times under 200ms, and the system can handle concurrent users efficiently.

**Conclusion:** This project demonstrates the successful implementation of a modern web application that meets all specified requirements while maintaining high standards of security, usability, and performance.

**Keywords:** React, TypeScript, Web Application, REST API, User Authentication, Responsive Design
  </abstract>

  <chapter1_introduction>
# CHAPTER 1: INTRODUCTION

## 1.1 Overview

The digital transformation of various sectors has created unprecedented demand for web-based solutions that can streamline operations, enhance productivity, and provide seamless user experiences. Modern web applications leverage cutting-edge technologies to deliver responsive, interactive, and feature-rich platforms accessible from any device with an internet connection.

The evolution of frontend frameworks like React, Vue, and Angular has revolutionized how developers approach user interface development. These frameworks enable the creation of dynamic, single-page applications (SPAs) that provide desktop-like experiences within web browsers. Combined with powerful backend technologies and cloud infrastructure, today's web applications can handle complex business logic while maintaining excellent performance.

This project aims to develop a comprehensive web application that addresses specific challenges in [domain]. By leveraging modern technologies and best practices in software engineering, the application provides users with an efficient, intuitive platform for managing their tasks and achieving their goals.

## 1.2 Problem Statement

Despite the availability of numerous solutions in the market, several challenges persist:

1. **Usability Issues:** Many existing systems have complex, non-intuitive interfaces that require extensive training for effective use.

2. **Performance Limitations:** Legacy systems often suffer from slow response times and inability to handle concurrent users effectively.

3. **Security Concerns:** Inadequate security measures in some solutions expose user data to potential breaches.

4. **Limited Accessibility:** Many solutions lack responsive design, making them difficult to use on mobile devices.

5. **Integration Challenges:** Existing systems often operate in silos, making data integration and workflow automation difficult.

## 1.3 Objectives

### Primary Objectives:
1. To design and develop a user-friendly web application with intuitive navigation
2. To implement robust authentication and authorization mechanisms
3. To create a responsive design that works seamlessly across devices
4. To ensure data integrity and security through encryption and validation

### Secondary Objectives:
1. To optimize application performance for fast load times
2. To implement comprehensive error handling and logging
3. To create detailed documentation for future maintenance

## 1.4 Scope of the Project

### Inclusions:
- User registration and authentication system
- Dashboard with key metrics and navigation
- Core feature modules as per requirements
- Admin panel for system management
- Reporting and analytics features

### Exclusions:
- Native mobile applications (mobile-responsive web only)
- Third-party payment integration
- Multi-language support (English only for initial release)

### Target Users:
- End users seeking to manage their tasks efficiently
- Administrators requiring oversight and control capabilities
- System operators for maintenance and support

## 1.5 Methodology

The project follows an Agile development methodology with two-week sprint cycles:

**Phase 1: Requirements & Analysis (Week 1-2)**
- Stakeholder interviews and requirements gathering
- Analysis of existing solutions
- Technology stack selection

**Phase 2: Design (Week 3-4)**
- System architecture design
- Database schema design
- UI/UX wireframing

**Phase 3: Implementation (Week 5-10)**
- Frontend development with React/TypeScript
- Backend API development
- Database implementation
- Integration testing

**Phase 4: Testing & Deployment (Week 11-12)**
- Comprehensive testing
- Bug fixes and optimization
- Documentation and deployment

## 1.6 Organization of Report

This report is organized into seven chapters:

- **Chapter 1: Introduction** - Project overview, objectives, and scope
- **Chapter 2: Literature Survey** - Analysis of existing systems and technologies
- **Chapter 3: System Analysis & Requirements** - Detailed SRS documentation
- **Chapter 4: System Design** - Architecture and UML diagrams
- **Chapter 5: Implementation** - Development details and code snippets
- **Chapter 6: Testing & Results** - Test cases and outcomes
- **Chapter 7: Conclusion** - Summary and future enhancements
  </chapter1_introduction>

  <chapter2_literature_survey>
# CHAPTER 2: LITERATURE SURVEY

## 2.1 Introduction

This chapter presents a comprehensive review of existing systems, technologies, and research relevant to the proposed project. The literature survey helps identify the strengths and weaknesses of current solutions, informing the design decisions for our implementation.

## 2.2 Existing Systems Analysis

### System 1: [Existing Solution A]
**Features:** User management, basic task tracking, reporting
**Pros:** Established user base, reliable infrastructure
**Cons:** Outdated UI, limited customization, slow performance

### System 2: [Existing Solution B]
**Features:** Modern interface, cloud-based, mobile app
**Pros:** Good UX, responsive design, regular updates
**Cons:** Expensive pricing, limited features in free tier

### System 3: [Existing Solution C]
**Features:** Open source, customizable, self-hosted option
**Pros:** Cost-effective, community support, flexibility
**Cons:** Complex setup, requires technical expertise

## 2.3 Comparative Analysis

| Feature | Solution A | Solution B | Solution C | Proposed System |
|---------|-----------|-----------|-----------|-----------------|
| Modern UI | No | Yes | Partial | Yes |
| Responsive | No | Yes | Yes | Yes |
| Security | Basic | Good | Variable | Excellent |
| Performance | Poor | Good | Good | Excellent |
| Cost | Medium | High | Low | Low |

## 2.4 Technology Review

### Frontend Technologies:
- **React:** Component-based architecture, virtual DOM, large ecosystem
- **Vue.js:** Progressive framework, easy learning curve
- **Angular:** Full-featured, TypeScript-first

### Backend Technologies:
- **Node.js/Express:** JavaScript runtime, non-blocking I/O
- **Python/FastAPI:** High performance, automatic API documentation
- **Java/Spring Boot:** Enterprise-grade, robust security

## 2.5 Research Gap & Motivation

Based on the analysis, we identified the following gaps:
1. Lack of intuitive, modern user interfaces in affordable solutions
2. Insufficient focus on mobile responsiveness
3. Limited integration capabilities
4. Inadequate security measures in open-source alternatives

Our proposed system addresses these gaps by combining modern frontend technologies with robust backend architecture.
  </chapter2_literature_survey>

  <chapter3_system_analysis>
# CHAPTER 3: SYSTEM ANALYSIS & REQUIREMENTS (IEEE 830-1998 SRS)

## 3.1 Introduction

### 3.1.1 Purpose
This Software Requirements Specification (SRS) document describes the functional and non-functional requirements for the [PROJECT_NAME] system.

### 3.1.2 Scope
The system provides a web-based platform for users to manage their tasks efficiently with features including user authentication, dashboard, task management, and reporting.

### 3.1.3 Definitions
- **User:** Any person registered in the system
- **Admin:** User with elevated privileges
- **Task:** A unit of work to be tracked

## 3.2 Overall Description

### 3.2.1 Product Perspective
The system is a standalone web application accessible via modern browsers. It interacts with a database for data persistence and uses REST APIs for client-server communication.

### 3.2.2 User Characteristics
- **End Users:** Basic computer literacy, familiar with web applications
- **Administrators:** Technical background, system management experience

## 3.3 Functional Requirements

### FR-001: User Registration
**Description:** The system shall allow new users to create an account
**Input:** Email, password, name
**Process:** Validate inputs, check email uniqueness, hash password, create record
**Output:** Success message or validation errors
**Priority:** High

### FR-002: User Login
**Description:** The system shall authenticate registered users
**Input:** Email, password
**Process:** Validate credentials, generate JWT token
**Output:** Access token or error message
**Priority:** High

### FR-003: Password Reset
**Description:** The system shall allow users to reset forgotten passwords
**Input:** Registered email
**Process:** Generate reset token, send email with reset link
**Output:** Confirmation message
**Priority:** Medium

[... Additional 27 functional requirements FR-004 through FR-030 ...]

## 3.4 Non-Functional Requirements

### NFR-001: Response Time
**Description:** The system shall respond to user requests within 200ms
**Priority:** High

### NFR-002: Concurrent Users
**Description:** The system shall support at least 100 concurrent users
**Priority:** High

### NFR-003: Availability
**Description:** The system shall maintain 99.5% uptime
**Priority:** High

[... Additional non-functional requirements NFR-004 through NFR-015 ...]
  </chapter3_system_analysis>

  <chapter4_system_design>
# CHAPTER 4: SYSTEM DESIGN

## 4.1 System Architecture

The system follows a three-tier architecture:
1. **Presentation Layer:** React frontend with TypeScript
2. **Business Logic Layer:** REST API backend
3. **Data Layer:** PostgreSQL database

## 4.2 UML Diagrams

### 4.2.1 Use Case Diagram

```mermaid
graph TD
    subgraph Actors
        User((User))
        Admin((Admin))
    end
    subgraph "System Boundary"
        UC1[Register]
        UC2[Login]
        UC3[Manage Tasks]
        UC4[View Dashboard]
        UC5[Generate Reports]
        UC6[Manage Users]
    end
    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    Admin --> UC5
    Admin --> UC6
```

### 4.2.2 Class Diagram

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String password
        +String name
        +DateTime createdAt
        +login()
        +logout()
    }
    class Task {
        +UUID id
        +String title
        +String description
        +Status status
        +DateTime dueDate
        +create()
        +update()
        +delete()
    }
    User "1" --> "*" Task : creates
```

### 4.2.3 Sequence Diagram - User Login

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant D as Database

    U->>F: Enter credentials
    F->>A: POST /auth/login
    A->>D: Query user
    D-->>A: User record
    A->>A: Verify password
    A-->>F: JWT Token
    F-->>U: Redirect to dashboard
```

### 4.2.4 ER Diagram

```mermaid
erDiagram
    USERS ||--o{ TASKS : creates
    USERS {
        uuid id PK
        string email UK
        string password
        string name
        datetime created_at
    }
    TASKS {
        uuid id PK
        uuid user_id FK
        string title
        text description
        string status
        datetime due_date
    }
```

## 4.3 Database Design

### Users Table
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| password | VARCHAR(255) | NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| created_at | TIMESTAMP | DEFAULT NOW() |

## 4.4 User Interface Design

The UI follows modern design principles with:
- Dark theme with glassmorphism effects
- Responsive layout using Tailwind CSS
- Consistent component styling
- Intuitive navigation patterns
  </chapter4_system_design>

  <chapter5_implementation>
# CHAPTER 5: IMPLEMENTATION

## 5.1 Development Environment

**Hardware:**
- Processor: Intel Core i5 or equivalent
- RAM: 8GB minimum
- Storage: 256GB SSD

**Software:**
- OS: Windows 11 / macOS / Linux
- IDE: VS Code
- Runtime: Node.js 18+
- Database: PostgreSQL 15+
- Version Control: Git

## 5.2 Module Description

### Module 1: Authentication
Handles user registration, login, and session management.

```typescript
// Example: Login function
async function login(email: string, password: string) {
  const user = await db.users.findByEmail(email);
  if (!user || !verifyPassword(password, user.password)) {
    throw new Error('Invalid credentials');
  }
  return generateJWT(user);
}
```

### Module 2: Dashboard
Displays key metrics and provides navigation to features.

### Module 3: Task Management
CRUD operations for user tasks.

## 5.3 API Documentation

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| /auth/register | POST | Register new user | No |
| /auth/login | POST | User login | No |
| /tasks | GET | List user tasks | Yes |
| /tasks | POST | Create task | Yes |
| /tasks/:id | PUT | Update task | Yes |
| /tasks/:id | DELETE | Delete task | Yes |

## 5.4 Security Implementation

- **Password Hashing:** bcrypt with salt rounds
- **JWT Tokens:** Signed with secret key, 24h expiry
- **Input Validation:** All inputs sanitized
- **HTTPS:** TLS encryption for all traffic
  </chapter5_implementation>

  <chapter6_testing>
# CHAPTER 6: TESTING & RESULTS

## 6.1 Testing Methodology

Testing was conducted at multiple levels:
1. **Unit Testing:** Individual functions and components
2. **Integration Testing:** API endpoints and database
3. **System Testing:** End-to-end workflows
4. **UAT:** User acceptance testing

**Tools Used:** Jest, React Testing Library, Postman

## 6.2 Test Cases

| TC-ID | Description | Input | Expected | Actual | Status |
|-------|-------------|-------|----------|--------|--------|
| TC-001 | User Registration | Valid data | Success message | Success | Pass |
| TC-002 | Registration with existing email | Duplicate email | Error message | Error shown | Pass |
| TC-003 | Login with valid credentials | Valid email/password | JWT token | Token received | Pass |
| TC-004 | Login with invalid password | Wrong password | Error | Error shown | Pass |
| TC-005 | Create new task | Task data | Task created | Created | Pass |
| TC-006 | Update task status | Status change | Updated status | Updated | Pass |
| TC-007 | Delete task | Task ID | Task removed | Removed | Pass |
| TC-008 | View dashboard | Logged in user | Dashboard loads | Loaded | Pass |
| TC-009 | Logout | Logged in user | Session ended | Logged out | Pass |
| TC-010 | Password reset | Valid email | Reset email sent | Email sent | Pass |

[... Additional test cases TC-011 through TC-020 ...]

## 6.3 Test Results Summary

| Metric | Value |
|--------|-------|
| Total Test Cases | 20 |
| Passed | 19 |
| Failed | 1 |
| Pass Rate | 95% |

## 6.4 Screenshots

**Figure 6.1: Login Page**
The login page features a clean design with email and password fields, along with OAuth options for Google and GitHub login.

**Figure 6.2: Dashboard**
The dashboard displays key metrics, recent activity, and quick action buttons for common tasks.
  </chapter6_testing>

  <chapter7_conclusion>
# CHAPTER 7: CONCLUSION & FUTURE SCOPE

## 7.1 Conclusion

This project successfully developed a comprehensive web application that addresses the identified problems in the domain. The key achievements include:

1. **Modern User Interface:** Implemented a responsive, intuitive UI using React and Tailwind CSS that provides excellent user experience across devices.

2. **Robust Security:** Implemented industry-standard security measures including JWT authentication, password hashing, and input validation.

3. **High Performance:** Achieved response times under 200ms through optimized database queries and efficient frontend rendering.

4. **Scalable Architecture:** Designed a modular architecture that can be easily extended with new features.

### Challenges Faced:
- Integrating multiple authentication methods
- Optimizing database queries for large datasets
- Ensuring cross-browser compatibility

### Learnings:
- Importance of proper planning and requirement analysis
- Value of iterative development and testing
- Significance of code organization and documentation

## 7.2 Future Enhancements

1. **Mobile Application:** Develop native iOS and Android apps for better mobile experience

2. **AI Integration:** Implement AI-powered features like smart suggestions and automation

3. **Multi-language Support:** Add internationalization for global users

4. **Advanced Analytics:** Enhanced reporting with data visualization

5. **Third-party Integrations:** Connect with popular tools like Slack, Google Calendar
  </chapter7_conclusion>

  <references>
# REFERENCES

[1] React Documentation, "Getting Started with React," React.dev, 2024. [Online]. Available: https://react.dev

[2] TypeScript Handbook, "TypeScript for JavaScript Programmers," TypeScript, 2024. [Online]. Available: https://www.typescriptlang.org/docs

[3] Tailwind CSS Documentation, "Utility-First CSS Framework," Tailwind Labs, 2024. [Online]. Available: https://tailwindcss.com

[4] IEEE, "IEEE Recommended Practice for Software Requirements Specifications," IEEE Std 830-1998.

[5] M. Fowler, "Patterns of Enterprise Application Architecture," Addison-Wesley, 2002.

[6] R. C. Martin, "Clean Code: A Handbook of Agile Software Craftsmanship," Pearson, 2008.

[7] E. Gamma et al., "Design Patterns: Elements of Reusable Object-Oriented Software," Addison-Wesley, 1994.

[8] PostgreSQL Documentation, "PostgreSQL 15 Documentation," PostgreSQL Global Development Group, 2024.

[9] JWT.io, "Introduction to JSON Web Tokens," Auth0, 2024. [Online]. Available: https://jwt.io

[10] OWASP, "OWASP Top Ten Web Application Security Risks," OWASP Foundation, 2024.

[11] Node.js Documentation, "Node.js v18 Documentation," OpenJS Foundation, 2024.

[12] Vite Documentation, "Next Generation Frontend Tooling," Vite, 2024.

[13] Git Documentation, "Git Reference Manual," Software Freedom Conservancy, 2024.

[14] Jest Documentation, "Delightful JavaScript Testing," Meta Open Source, 2024.

[15] MDN Web Docs, "Web technology for developers," Mozilla, 2024.
  </references>

  <viva_questions>
# VIVA QUESTIONS AND ANSWERS

## Q1: What is the main objective of your project?
**Answer:** The main objective is to develop a modern web application that provides users with an efficient platform for managing their tasks. The system aims to address limitations in existing solutions by offering an intuitive user interface, robust security, and excellent performance. We focused on creating a responsive design that works seamlessly across devices while implementing industry-standard security practices.

## Q2: Why did you choose React for the frontend?
**Answer:** We chose React for several reasons: First, its component-based architecture promotes code reusability and maintainability. Second, the virtual DOM provides excellent performance by minimizing actual DOM manipulations. Third, React has a large ecosystem with extensive libraries and tools. Fourth, TypeScript integration provides type safety and better developer experience. Finally, React's popularity ensures strong community support and abundant learning resources.

## Q3: Explain the authentication flow in your application.
**Answer:** Our authentication uses JWT (JSON Web Tokens). When a user logs in, the server validates credentials against the database. Upon successful validation, the server generates a JWT containing the user ID and role, signed with a secret key. This token is sent to the client and stored in localStorage. For subsequent requests, the token is included in the Authorization header. The server validates the token signature and expiry before processing requests.

## Q4: How did you ensure security in your application?
**Answer:** We implemented multiple security measures: passwords are hashed using bcrypt with salt rounds; JWT tokens have expiration times; all inputs are validated and sanitized to prevent SQL injection and XSS attacks; HTTPS encrypts data in transit; CORS is configured to allow only authorized origins; sensitive routes require authentication middleware.

## Q5: What was the most challenging part of the project?
**Answer:** The most challenging aspect was implementing real-time updates while maintaining performance. We had to optimize database queries, implement efficient state management on the frontend, and ensure the UI remained responsive even with large datasets. We addressed this through pagination, lazy loading, and memoization techniques.

[... Additional 25 questions and answers ...]
  </viva_questions>

  <ppt_slides>
# PRESENTATION SLIDES

## Slide 1: Title
**[PROJECT_NAME]**
A Modern Web Application

Team Members: [STUDENT_NAMES]
Guide: [GUIDE_NAME]
[COLLEGE_NAME]
Academic Year: 2024-2025

## Slide 2: Introduction & Problem Statement
**Current Challenges:**
- Outdated interfaces in existing solutions
- Poor mobile responsiveness
- Security vulnerabilities
- Limited customization options

## Slide 3: Objectives
**Primary Objectives:**
- Develop user-friendly web application
- Implement secure authentication
- Create responsive design
- Ensure data integrity

## Slide 4: Technology Stack
**Frontend:** React, TypeScript, Tailwind CSS
**Backend:** REST API
**Database:** PostgreSQL
**Security:** JWT, bcrypt

## Slide 5: System Architecture
[Architecture diagram placeholder]
Three-tier architecture: Presentation, Business Logic, Data Layer

## Slide 6: Key Features
- User Authentication (Email + OAuth)
- Interactive Dashboard
- Task Management
- Reporting & Analytics

## Slide 7: Database Design
[ER Diagram placeholder]
Core entities: Users, Tasks, Categories

## Slide 8: Screenshots - Login
[Login page screenshot placeholder]

## Slide 9: Screenshots - Dashboard
[Dashboard screenshot placeholder]

## Slide 10: Testing Results
- Total Test Cases: 20
- Passed: 19
- Pass Rate: 95%
- Average Response Time: 180ms

## Slide 11: Conclusion
Successfully developed a modern, secure, and user-friendly web application meeting all specified requirements.

## Slide 12: Future Scope
- Mobile Application
- AI Integration
- Multi-language Support
- Advanced Analytics

## Slide 13: References
[Key references listed]

## Slide 14: Thank You
**Questions?**
Thank you for your attention!
  </ppt_slides>
</documents>"""


def get_response_for_file(file_path: str) -> str:
    """Get mock response for a specific file path."""
    file_lower = file_path.lower()

    if "package.json" in file_lower:
        return WRITER_RESPONSE_PACKAGE_JSON
    elif "index.html" in file_lower:
        return WRITER_RESPONSE_INDEX_HTML
    elif "vite.config" in file_lower:
        return WRITER_RESPONSE_VITE_CONFIG
    elif "tailwind.config" in file_lower:
        return WRITER_RESPONSE_TAILWIND_CONFIG
    elif "postcss.config" in file_lower:
        return """<file path="postcss.config.js">
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
</file>"""
    elif "tsconfig.json" in file_lower and "node" not in file_lower:
        return """<file path="tsconfig.json">
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
</file>"""
    elif "tsconfig.node" in file_lower:
        return """<file path="tsconfig.node.json">
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
</file>"""
    elif "main.tsx" in file_lower:
        return WRITER_RESPONSE_MAIN_TSX
    elif "index.css" in file_lower:
        return WRITER_RESPONSE_INDEX_CSS
    elif "app.tsx" in file_lower:
        return WRITER_RESPONSE_APP_TSX
    else:
        return WRITER_RESPONSE_APP_TSX
