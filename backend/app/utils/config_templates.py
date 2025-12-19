"""
Default templates for essential config files.

These templates provide working default content when the AI fails to generate
essential config files like tsconfig.json, tailwind.config.js, etc.

Used by:
- Dynamic Orchestrator (to verify essential files exist after generation)
- SimpleFixer (to create missing config files)
"""

# React + Vite + TypeScript project templates
VITE_REACT_TEMPLATES = {
    "tsconfig.json": """{
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
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
""",

    "tsconfig.node.json": """{
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
""",

    "tailwind.config.js": """/** @type {import('tailwindcss').Config} */
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
""",

    "postcss.config.js": """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""",

    "vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
""",

    "index.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""",

    "src/main.tsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
""",

    "src/App.tsx": """function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-800">Welcome to React</h1>
        <p className="mt-2 text-gray-600">Edit src/App.tsx to get started</p>
      </div>
    </div>
  )
}

export default App
""",

    "src/index.css": """@tailwind base;
@tailwind components;
@tailwind utilities;
""",
}

# Next.js templates
NEXTJS_TEMPLATES = {
    "tsconfig.json": """{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
""",

    "tailwind.config.ts": """import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
export default config
""",

    "postcss.config.js": """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""",

    "next.config.js": """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig
""",
}

# FastAPI templates
FASTAPI_TEMPLATES = {
    "requirements.txt": """fastapi>=0.100.0
uvicorn[standard]>=0.22.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
alembic>=1.11.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
""",

    "main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
""",
}

# Spring Boot templates
SPRING_BOOT_TEMPLATES = {
    "pom.xml": """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
        <relativePath/>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>app</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>app</name>
    <description>Spring Boot Application</description>
    <properties>
        <java.version>17</java.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
""",

    "src/main/resources/application.properties": """spring.application.name=app
server.port=8080
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.h2.console.enabled=true
""",
}


def get_template(file_path: str, project_type: str = "vite-react") -> str | None:
    """
    Get default template content for a config file.

    Args:
        file_path: Path to the file (e.g., "tsconfig.json", "frontend/tailwind.config.js")
        project_type: Type of project ("vite-react", "nextjs", "fastapi", "spring")

    Returns:
        Template content or None if no template available
    """
    # Normalize path - extract just the filename for matching
    filename = file_path.replace("\\", "/").split("/")[-1]

    # Also check for src/ prefixed files
    if "src/" in file_path:
        # Get the src-relative path
        src_idx = file_path.find("src/")
        src_path = file_path[src_idx:]
        filename = src_path  # Use full src/... path for matching

    templates = {}

    if project_type in ["vite-react", "react", "vite"]:
        templates = VITE_REACT_TEMPLATES
    elif project_type in ["nextjs", "next"]:
        templates = NEXTJS_TEMPLATES
    elif project_type in ["fastapi", "python"]:
        templates = FASTAPI_TEMPLATES
    elif project_type in ["spring", "spring-boot", "java"]:
        templates = SPRING_BOOT_TEMPLATES

    # Try exact match first
    if filename in templates:
        return templates[filename]

    # Try without extension variations
    if filename.replace(".ts", ".js") in templates:
        return templates[filename.replace(".ts", ".js")]

    return None


def get_all_essential_files(project_type: str = "vite-react") -> dict:
    """
    Get all essential file templates for a project type.

    Returns:
        Dict mapping file paths to content
    """
    if project_type in ["vite-react", "react", "vite"]:
        return VITE_REACT_TEMPLATES.copy()
    elif project_type in ["nextjs", "next"]:
        return NEXTJS_TEMPLATES.copy()
    elif project_type in ["fastapi", "python"]:
        return FASTAPI_TEMPLATES.copy()
    elif project_type in ["spring", "spring-boot", "java"]:
        return SPRING_BOOT_TEMPLATES.copy()
    return {}
