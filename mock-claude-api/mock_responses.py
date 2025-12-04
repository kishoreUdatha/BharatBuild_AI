"""
Mock Response Templates for BharatBuild AI Testing
===================================================
Contains realistic mock responses for different types of requests.
"""

# Bolt-style project generation response
BOLT_PROJECT_RESPONSE = """I'll create this project for you.

<boltArtifact id="project-setup" title="Project Setup">
<boltAction type="file" filePath="package.json">
{
  "name": "my-react-app",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
</boltAction>

<boltAction type="file" filePath="index.html">
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>My React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
</boltAction>

<boltAction type="file" filePath="vite.config.js">
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
</boltAction>

<boltAction type="file" filePath="src/main.jsx">
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
</boltAction>

<boltAction type="file" filePath="src/App.jsx">
import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="app">
      <h1>Welcome to My React App</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          Count is {count}
        </button>
      </div>
    </div>
  )
}

export default App
</boltAction>

<boltAction type="file" filePath="src/index.css">
:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;
  color: #213547;
  background-color: #ffffff;
}

.app {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

h1 {
  font-size: 3.2em;
  line-height: 1.1;
}

.card {
  padding: 2em;
}

button {
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  font-family: inherit;
  background-color: #646cff;
  color: white;
  cursor: pointer;
  transition: border-color 0.25s;
}

button:hover {
  border-color: #646cff;
}
</boltAction>

<boltAction type="shell">
npm install
</boltAction>

<boltAction type="shell">
npm run dev
</boltAction>
</boltArtifact>

The project is now set up! You can see the live preview on the right."""


# Simple code generation response
CODE_GENERATION_RESPONSE = """Here's the implementation:

<boltArtifact id="code-implementation" title="Implementation">
<boltAction type="file" filePath="src/utils/helpers.js">
/**
 * Utility helper functions
 */

export function formatDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(new Date(date));
}

export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

export function generateId() {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}
</boltAction>
</boltArtifact>

I've created the utility functions. Let me know if you need any modifications!"""


# API endpoint generation
API_GENERATION_RESPONSE = """I'll create the API endpoint for you.

<boltArtifact id="api-endpoint" title="API Endpoint">
<boltAction type="file" filePath="src/api/users.js">
import express from 'express';

const router = express.Router();

// In-memory storage for demo
let users = [];

// GET all users
router.get('/', (req, res) => {
  res.json(users);
});

// GET user by ID
router.get('/:id', (req, res) => {
  const user = users.find(u => u.id === req.params.id);
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  res.json(user);
});

// POST create user
router.post('/', (req, res) => {
  const { name, email } = req.body;

  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email are required' });
  }

  const newUser = {
    id: Date.now().toString(),
    name,
    email,
    createdAt: new Date().toISOString()
  };

  users.push(newUser);
  res.status(201).json(newUser);
});

// PUT update user
router.put('/:id', (req, res) => {
  const index = users.findIndex(u => u.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: 'User not found' });
  }

  users[index] = { ...users[index], ...req.body };
  res.json(users[index]);
});

// DELETE user
router.delete('/:id', (req, res) => {
  const index = users.findIndex(u => u.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: 'User not found' });
  }

  users.splice(index, 1);
  res.status(204).send();
});

export default router;
</boltAction>
</boltArtifact>

The REST API endpoints are ready. They support CRUD operations for users."""


# Bug fix response
BUG_FIX_RESPONSE = """I found the issue. Let me fix it.

<boltArtifact id="bug-fix" title="Bug Fix">
<boltAction type="file" filePath="src/components/Form.jsx">
import { useState, useCallback } from 'react';

export default function Form({ onSubmit }) {
  const [formData, setFormData] = useState({
    name: '',
    email: ''
  });
  const [errors, setErrors] = useState({});

  const validate = useCallback(() => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\\S+@\\S+\\.\\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  const handleSubmit = (e) => {
    e.preventDefault();

    if (validate()) {
      onSubmit(formData);
      setFormData({ name: '', email: '' });
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <input
          name="name"
          value={formData.name}
          onChange={handleChange}
          placeholder="Name"
        />
        {errors.name && <span className="error">{errors.name}</span>}
      </div>
      <div>
        <input
          name="email"
          value={formData.email}
          onChange={handleChange}
          placeholder="Email"
        />
        {errors.email && <span className="error">{errors.email}</span>}
      </div>
      <button type="submit">Submit</button>
    </form>
  );
}
</boltAction>
</boltArtifact>

Fixed! The issues were:
1. Added proper form validation
2. Fixed the email regex pattern
3. Added error clearing on input change"""


# Planning response
PLANNING_RESPONSE = """## Project Plan

Based on your requirements, here's my recommended approach:

### Phase 1: Foundation
- Set up project structure
- Configure build tools and dependencies
- Create base components

### Phase 2: Core Features
- Implement main functionality
- Add state management
- Create API integrations

### Phase 3: UI/UX
- Design responsive layouts
- Add animations and transitions
- Implement dark mode

### Phase 4: Testing & Deployment
- Write unit tests
- Set up CI/CD
- Deploy to production

Should I start implementing Phase 1?"""


# Default conversational response
DEFAULT_RESPONSE = """I understand what you're looking for. Here's my analysis:

Based on the context provided, I can help you with this task. The approach I recommend involves:

1. **Understanding the requirements** - Making sure we have clarity on what needs to be built
2. **Planning the implementation** - Breaking down the work into manageable pieces
3. **Writing the code** - Implementing the solution step by step
4. **Testing and refinement** - Ensuring everything works correctly

Would you like me to proceed with the implementation, or would you prefer to discuss the approach further?"""


def get_response_for_prompt(prompt: str) -> str:
    """Select appropriate mock response based on prompt content."""
    prompt_lower = prompt.lower()

    # Check for project creation keywords
    if any(word in prompt_lower for word in ["create a", "build a", "make a", "new project", "generate"]):
        if any(word in prompt_lower for word in ["react", "vue", "angular", "app", "website", "application"]):
            return BOLT_PROJECT_RESPONSE

    # Check for code-related keywords
    if any(word in prompt_lower for word in ["function", "implement", "code", "write"]):
        return CODE_GENERATION_RESPONSE

    # Check for API keywords
    if any(word in prompt_lower for word in ["api", "endpoint", "rest", "crud", "route"]):
        return API_GENERATION_RESPONSE

    # Check for bug fix keywords
    if any(word in prompt_lower for word in ["fix", "bug", "error", "issue", "problem", "not working"]):
        return BUG_FIX_RESPONSE

    # Check for planning keywords
    if any(word in prompt_lower for word in ["plan", "design", "architecture", "approach", "strategy"]):
        return PLANNING_RESPONSE

    return DEFAULT_RESPONSE
