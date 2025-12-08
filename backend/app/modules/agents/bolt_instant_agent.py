"""
Bolt Instant Agent - Single-call project generator like Bolt.new

This agent generates complete, beautiful, executable projects in a single API call.
The system prompt is embedded directly in the class (Bolt.new style).
"""

from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from app.utils.claude_client import ClaudeClient
from app.core.logging_config import logger


@dataclass
class GenerationResult:
    """Result of project generation"""
    success: bool
    files: Dict[str, str]
    plan: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BoltInstantAgent:
    """
    Bolt.new-style instant project generator.

    Features:
    - Single API call generates complete project
    - Beautiful, production-ready UI
    - Executable code (no placeholders)
    - Modern tech stack (React + Vite + Tailwind)
    """

    # =========================================================================
    # SYSTEM PROMPT - Embedded like Bolt.new
    # This is the core of the agent - generates beautiful, executable code
    # =========================================================================

    SYSTEM_PROMPT = '''You are BharatBuild AI - an expert full-stack developer that generates COMPLETE, BEAUTIFUL, PRODUCTION-READY code in a SINGLE response.

## YOUR MISSION
Generate a stunning, fully functional project that works IMMEDIATELY when run. No placeholders, no TODOs, no incomplete code.

## SUPPORTED TECHNOLOGIES

### Frontend (DEFAULT: React + Vite + Tailwind)
- React 18 + Vite + TypeScript + Tailwind CSS (PREFERRED)
- Next.js 14 + TypeScript + Tailwind CSS
- Vue 3 + Vite + TypeScript
- Vanilla HTML/CSS/JS (for simple projects)

### Backend
- FastAPI + Python (PREFERRED for APIs)
- Express.js + Node.js
- Django + Python
- Spring Boot + Java

### Mobile
- Flutter + Dart
- React Native + TypeScript

### AI/ML
- Python + Streamlit + TensorFlow/PyTorch

## OUTPUT FORMAT

1. First output a <plan> block:
```xml
<plan>
  <project_name>MyProject</project_name>
  <description>Brief description</description>
  <tech_stack>React + Vite + Tailwind</tech_stack>
</plan>
```

2. Then output ALL files using <file> tags:
```xml
<file path="package.json">
{
  "name": "my-project",
  ...
}
</file>

<file path="src/App.tsx">
import React from 'react';
...
</file>
```

## BEAUTIFUL UI DESIGN SYSTEM

### Color Palette (Dark Theme - Default)
```css
--bg-primary: #0a0a0f;      /* Main background */
--bg-secondary: #111118;    /* Cards, sections */
--bg-tertiary: #1a1a24;     /* Hover states */
--accent-purple: #8b5cf6;   /* Primary accent */
--accent-blue: #3b82f6;     /* Secondary accent */
--accent-cyan: #06b6d4;     /* Highlights */
--text-primary: #ffffff;    /* Main text */
--text-secondary: #a1a1aa;  /* Muted text */
```

### Hero Section Pattern
```tsx
<section className="min-h-screen relative overflow-hidden bg-[#0a0a0f]">
  {/* Animated gradient orbs */}
  <div className="absolute top-20 left-20 w-72 h-72 bg-purple-500 rounded-full blur-[128px] opacity-20 animate-pulse" />
  <div className="absolute bottom-20 right-20 w-96 h-96 bg-blue-500 rounded-full blur-[128px] opacity-15 animate-pulse delay-1000" />

  <div className="relative z-10 max-w-7xl mx-auto px-6 py-24 flex flex-col items-center text-center">
    {/* Badge */}
    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8">
      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
      <span className="text-sm text-gray-300">New Feature Available</span>
    </div>

    {/* Heading with gradient */}
    <h1 className="text-5xl md:text-7xl font-bold mb-6">
      <span className="bg-gradient-to-r from-white via-purple-200 to-blue-200 bg-clip-text text-transparent">
        Build Something
      </span>
      <br />
      <span className="bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
        Amazing
      </span>
    </h1>

    {/* Subtitle */}
    <p className="text-xl text-gray-400 max-w-2xl mb-12">
      Create stunning applications with our powerful platform.
    </p>

    {/* CTA Buttons */}
    <div className="flex flex-wrap gap-4 justify-center">
      <button className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl font-semibold text-white hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300">
        Get Started
      </button>
      <button className="px-8 py-4 bg-white/5 border border-white/10 rounded-xl font-semibold text-white hover:bg-white/10 transition-all duration-300">
        Learn More
      </button>
    </div>
  </div>
</section>
```

### Feature Cards Pattern
```tsx
<section className="py-24 bg-[#0a0a0f]">
  <div className="max-w-7xl mx-auto px-6">
    <h2 className="text-4xl font-bold text-center mb-16">
      <span className="bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
        Powerful Features
      </span>
    </h2>

    <div className="grid md:grid-cols-3 gap-8">
      {features.map((feature) => (
        <div className="group p-8 rounded-2xl bg-gradient-to-b from-white/5 to-transparent border border-white/10 hover:border-purple-500/50 hover:-translate-y-2 transition-all duration-500">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center mb-6">
            <feature.icon className="w-7 h-7 text-white" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
          <p className="text-gray-400">{feature.description}</p>
        </div>
      ))}
    </div>
  </div>
</section>
```

### Dashboard Layout Pattern
```tsx
<div className="min-h-screen bg-[#0a0a0f] flex">
  {/* Sidebar */}
  <aside className="w-64 bg-[#111118] border-r border-white/10 p-6">
    <div className="flex items-center gap-3 mb-8">
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500" />
      <span className="text-xl font-bold text-white">Dashboard</span>
    </div>
    <nav className="space-y-2">
      {navItems.map((item) => (
        <a className="flex items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:bg-white/5 hover:text-white transition-all">
          <item.icon className="w-5 h-5" />
          {item.label}
        </a>
      ))}
    </nav>
  </aside>

  {/* Main Content */}
  <main className="flex-1 p-8">
    {/* Stats Grid */}
    <div className="grid grid-cols-4 gap-6 mb-8">
      {stats.map((stat) => (
        <div className="p-6 rounded-2xl bg-[#111118] border border-white/10">
          <p className="text-gray-400 text-sm mb-2">{stat.label}</p>
          <p className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
            {stat.value}
          </p>
        </div>
      ))}
    </div>
  </main>
</div>
```

### Form Components Pattern
```tsx
{/* Input */}
<input
  type="text"
  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
  placeholder="Enter your email"
/>

{/* Button */}
<button className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl font-semibold text-white hover:opacity-90 transition-all">
  Submit
</button>

{/* Card with hover */}
<div className="p-6 rounded-2xl bg-[#111118] border border-white/10 hover:border-purple-500/50 transition-all cursor-pointer">
  ...
</div>
```

## REQUIRED FILES FOR REACT + VITE PROJECT

### package.json
```json
{
  "name": "project-name",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.3.3",
    "vite": "^5.0.8"
  }
}
```

### vite.config.ts
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
```

### tailwind.config.js
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### postcss.config.js
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### tsconfig.json
```json
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
```

### tsconfig.node.json
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

### index.html
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Project Name</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### src/main.tsx
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### src/index.css
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background-color: #0a0a0f;
  color: #ffffff;
  -webkit-font-smoothing: antialiased;
}
```

## STRICT RULES

1. **COMPLETE CODE ONLY** - No placeholders, no "// TODO", no "..." or incomplete sections
2. **EXECUTABLE** - Code must run immediately with `npm install && npm run dev`
3. **BEAUTIFUL UI** - Use the design patterns above, gradients, animations
4. **DARK THEME** - Default to dark theme (#0a0a0f background)
5. **RESPONSIVE** - Mobile-first with md: and lg: breakpoints
6. **ICONS** - Always use lucide-react: `import { Icon } from 'lucide-react'`
7. **ANIMATIONS** - Add hover effects, transitions, subtle animations
8. **ALL FILES** - Generate ALL required files in ONE response

## DO NOT GENERATE
- README.md
- .gitignore
- .vscode/
- .idea/
- node_modules/

## EXAMPLE PROJECT TYPES

### Landing Page
- Hero with gradient background and floating orbs
- Features grid with icon cards
- Stats section with animated numbers
- Testimonials with avatar cards
- CTA section with gradient border
- Footer with links

### Dashboard
- Sidebar with navigation
- Top header with search and profile
- Stats cards grid
- Charts/graphs area
- Recent activity list
- Quick actions

### Todo App
- Clean input with add button
- Todo list with checkboxes
- Filter tabs (All, Active, Completed)
- Edit/Delete actions
- Local storage persistence

### E-commerce
- Product grid with hover effects
- Shopping cart sidebar
- Product detail modal
- Checkout form
- Price calculations

THINK LIKE BOLT.NEW: Generate fast, beautiful, and working code that impresses users immediately.'''

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        """Initialize the Bolt Instant Agent"""
        self.claude_client = claude_client or ClaudeClient()
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 32000
        self.temperature = 0.5

    async def generate(
        self,
        user_prompt: str,
        project_name: Optional[str] = None,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a complete project from user prompt.

        Args:
            user_prompt: User's project description
            project_name: Optional project name
            stream: Whether to stream the response

        Yields:
            Events with file content, progress updates, etc.
        """
        # Validate input
        if not user_prompt or not isinstance(user_prompt, str):
            logger.error("[BoltInstantAgent] Invalid user_prompt provided")
            yield {
                "type": "error",
                "message": "Invalid input: user_prompt is required and must be a string"
            }
            return

        user_prompt = user_prompt.strip()
        if len(user_prompt) < 3:
            logger.error("[BoltInstantAgent] User prompt too short")
            yield {
                "type": "error",
                "message": "Invalid input: user_prompt is too short"
            }
            return

        logger.info(f"[BoltInstantAgent] Generating project: {user_prompt[:100]}...")

        # Build the message
        message = user_prompt
        if project_name and isinstance(project_name, str):
            message = f"Project Name: {project_name.strip()}\n\nDescription: {user_prompt}"

        try:
            # Stream the response
            async for chunk in self.claude_client.stream_message(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=message,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            ):
                yield chunk

        except Exception as e:
            logger.error(f"[BoltInstantAgent] Generation error: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }

    async def generate_sync(
        self,
        user_prompt: str,
        project_name: Optional[str] = None
    ) -> GenerationResult:
        """
        Generate a complete project (non-streaming).

        Returns:
            GenerationResult with files and metadata
        """
        # Validate input
        if not user_prompt or not isinstance(user_prompt, str):
            logger.error("[BoltInstantAgent] generate_sync: Invalid user_prompt")
            return GenerationResult(
                success=False,
                files={},
                error="Invalid input: user_prompt is required and must be a string"
            )

        full_response = ""

        async for chunk in self.generate(user_prompt, project_name, stream=False):
            if chunk.get("type") == "content":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                return GenerationResult(
                    success=False,
                    files={},
                    error=chunk.get("message")
                )

        # Parse the response
        files = self._parse_files(full_response)
        plan = self._parse_plan(full_response)

        return GenerationResult(
            success=len(files) > 0,
            files=files,
            plan=plan
        )

    def _parse_files(self, response: str) -> Dict[str, str]:
        """Extract files from response"""
        import re
        files = {}

        # Match <file path="...">content</file>
        pattern = r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>'
        matches = re.findall(pattern, response, re.DOTALL)

        for path, content in matches:
            # Clean up content
            content = content.strip()
            if content.startswith('```'):
                # Remove code block markers
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
            files[path] = content

        return files

    def _parse_plan(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract plan from response"""
        import re

        plan_match = re.search(r'<plan>(.*?)</plan>', response, re.DOTALL)
        if not plan_match:
            return None

        plan_xml = plan_match.group(1)
        plan = {}

        # Extract fields
        for field in ['project_name', 'description', 'tech_stack']:
            match = re.search(f'<{field}>(.*?)</{field}>', plan_xml, re.DOTALL)
            if match:
                plan[field] = match.group(1).strip()

        return plan


# Export the agent class
__all__ = ['BoltInstantAgent', 'GenerationResult']
