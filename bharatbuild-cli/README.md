# BharatBuild CLI

AI-powered CLI for Indian developers, students, and founders. Interact with all BharatBuild platform modes directly from your terminal.

## Installation

```bash
npm install -g @bharatbuild/cli
```

Or build from source:

```bash
cd bharatbuild-cli
npm install
npm run build
npm link
```

## Quick Start

```bash
# Login
bharatbuild login

# Start interactive REPL (default: developer mode)
bharatbuild

# Direct mode entry
bharatbuild student
bharatbuild developer
bharatbuild founder
bharatbuild college
bharatbuild api-partner

# One-shot commands
bharatbuild student "hospital management system"
bharatbuild developer "build a todo app in React"
bharatbuild founder "create PRD for food delivery app"
```

## Platform Modes

### 🎓 Student Mode
For engineering students building academic projects.

```bash
bharatbuild student
```

Features:
- **Full project generation** — SRS + UML + code + report + PPT + viva Q&A
- **SRS only** — IEEE-format Software Requirements Specification
- **UML only** — class, sequence, ER, use-case diagrams
- **Code only** — working source code with proper structure
- **Documentation** — project report, README, API docs
- **Viva Q&A** — 30+ expected viva questions with answers

### 💻 Developer Mode
Bolt.new-style AI code generation for developers.

```bash
bharatbuild developer "build a full-stack task manager with React and FastAPI"
```

Features:
- Streaming code generation
- Conversational project building
- File-by-file creation with progress
- Project management (list, download, delete)
- Continue existing projects

### 🚀 Founder Mode
Tools for startup founders.

```bash
bharatbuild founder "create PRD for an online tutoring platform"
```

Features:
- PRD (Product Requirements Document) generation
- Business Plan creation
- GTM (Go-To-Market) strategy
- MVP planning
- Pitch deck outline
- General founder assistant chat

### 🏫 College Mode
For college admins and faculty.

```bash
bharatbuild college
```

Features:
- Dashboard stats (students, projects, usage)
- Student list with plan and project count
- All projects monitoring across batches
- Analytics dashboard
- Campus drive status

### 🔌 API Partner Mode
For developers using BharatBuild's API.

```bash
bharatbuild api-partner
```

Features:
- View token balance
- List API keys (masked)
- Create new API keys
- Revoke API keys
- Usage history
- API documentation links

## All Commands

```
bharatbuild                    Interactive REPL
bharatbuild login              Login to your account
bharatbuild login -t <token>   Login with token
bharatbuild logout             Clear credentials
bharatbuild register           Create new account
bharatbuild whoami             Show account info
bharatbuild projects           List your projects
bharatbuild download <id>      Download project as ZIP
bharatbuild delete <id>        Delete project
bharatbuild tokens             Show token balance
bharatbuild doctor             Environment diagnostics

# Mode shortcuts
bharatbuild student [prompt]
bharatbuild developer [prompt]   (alias: dev)
bharatbuild founder [prompt]
bharatbuild college
bharatbuild api-partner          (alias: api)
```

## REPL Commands

Inside the interactive REPL:

```
/mode student        Switch to student mode
/mode developer      Switch to developer mode
/mode founder        Switch to founder mode
/mode college        Switch to college mode
/mode api-partner    Switch to API partner mode
/menu                Show interactive menu for current mode
/help                Show all commands
/login               Login or re-authenticate
/logout              Clear credentials
/whoami              Show current user
/projects            List your projects
/tokens              Show token balance
/exit                Exit CLI
```

## Configuration

Config is stored in `~/.bharatbuild/config.json`.

**Environment variables:**
```bash
BHARATBUILD_API_URL=http://localhost:8000   # Backend URL
BHARATBUILD_TOKEN=<token>                   # Auth token
BHARATBUILD_MODEL=sonnet                    # AI model (haiku/sonnet)
BHARATBUILD_VERBOSE=true                    # Verbose mode
```

## Development

```bash
# Build TypeScript
npm run build

# Watch mode
npm run watch

# Run directly (dev)
npm run dev

# Type check
npx tsc --noEmit
```

## Architecture

```
bharatbuild-cli/src/
├── index.ts              # CLI entry point (commander)
├── config/
│   ├── config.ts         # Config load/save
│   ├── constants.ts      # Constants
│   └── defaults.ts       # Default values
├── api/
│   ├── client.ts         # HTTP + SSE client
│   └── auth.ts           # Auth manager
├── ui/
│   ├── repl.ts           # Interactive REPL
│   └── spinner.ts        # Spinner, progress, banner
├── modes/
│   ├── student.ts        # 🎓 Student mode
│   ├── developer.ts      # 💻 Developer mode
│   ├── founder.ts        # 🚀 Founder mode
│   ├── college.ts        # 🏫 College mode
│   └── api-partner.ts    # 🔌 API Partner mode
├── commands/
│   └── login.ts          # Login/register helpers
└── runtime/              # Agent runtime (existing)
```

## License

MIT
