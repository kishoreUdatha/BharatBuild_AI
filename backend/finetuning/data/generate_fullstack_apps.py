#!/usr/bin/env python3
"""
Generate Comprehensive Full-Stack Application Training Examples

Stacks covered:
1. MERN (MongoDB, Express, React, Node)
2. PERN (PostgreSQL, Express, React, Node)
3. Next.js Full-Stack (with Prisma)
4. Vue 3 + FastAPI
5. Angular + NestJS
6. React + Spring Boot
7. React + Django REST
8. Vue + Laravel
9. SvelteKit + Go
10. Next.js + Supabase
11. React + .NET Core
12. Nuxt 3 + FastAPI
"""

import json
import random
from pathlib import Path
from typing import List, Dict

OUTPUT_DIR = Path(__file__).parent / "fullstack_apps"

# Application domains
APPS = [
    ("Task Management App", "task", "tasks"),
    ("E-Commerce Store", "product", "products"),
    ("Blog Platform", "post", "posts"),
    ("Social Network", "user", "users"),
    ("Job Board", "job", "jobs"),
    ("Real Estate Listing", "property", "properties"),
    ("Restaurant Booking", "booking", "bookings"),
    ("Fitness Tracker", "workout", "workouts"),
    ("Invoice Manager", "invoice", "invoices"),
    ("Project Management", "project", "projects"),
    ("Learning Platform", "course", "courses"),
    ("Event Management", "event", "events"),
    ("Inventory System", "item", "items"),
    ("Customer Support", "ticket", "tickets"),
    ("Recipe App", "recipe", "recipes"),
]


def generate_mern_stack(app_name: str, entity: str, entities: str) -> Dict:
    """Generate MERN Stack (MongoDB, Express, React, Node) example"""

    prompt = f"Create a complete MERN stack {app_name} with React frontend, Express.js backend, MongoDB database, and JWT authentication"

    response = f"""I'll create a complete MERN stack {app_name}.

## Project Structure

```
{entity}-app/
├── client/                 # React Frontend
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── {entity.title()}List.jsx
│   │   │   ├── {entity.title()}Form.jsx
│   │   │   ├── {entity.title()}Card.jsx
│   │   │   ├── Navbar.jsx
│   │   │   └── PrivateRoute.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   └── {entity.title()}Detail.jsx
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   └── use{entity.title()}s.js
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── server/                 # Express Backend
│   ├── config/
│   │   └── db.js
│   ├── controllers/
│   │   ├── authController.js
│   │   └── {entity}Controller.js
│   ├── middleware/
│   │   ├── auth.js
│   │   └── errorHandler.js
│   ├── models/
│   │   ├── User.js
│   │   └── {entity.title()}.js
│   ├── routes/
│   │   ├── auth.js
│   │   └── {entities}.js
│   ├── server.js
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Backend - server/server.js

```javascript
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Connect to MongoDB
mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

// Routes
app.use('/api/auth', require('./routes/auth'));
app.use('/api/{entities}', require('./routes/{entities}'));

// Error handler
app.use(require('./middleware/errorHandler'));

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${{PORT}}`));
```

## Backend - server/models/{entity.title()}.js

```javascript
const mongoose = require('mongoose');

const {entity}Schema = new mongoose.Schema({{
  title: {{
    type: String,
    required: [true, 'Title is required'],
    trim: true,
    maxlength: [100, 'Title cannot exceed 100 characters']
  }},
  description: {{
    type: String,
    required: [true, 'Description is required']
  }},
  status: {{
    type: String,
    enum: ['active', 'inactive', 'pending'],
    default: 'active'
  }},
  user: {{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  }},
  createdAt: {{
    type: Date,
    default: Date.now
  }}
}});

module.exports = mongoose.model('{entity.title()}', {entity}Schema);
```

## Backend - server/models/User.js

```javascript
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const userSchema = new mongoose.Schema({{
  name: {{
    type: String,
    required: [true, 'Name is required']
  }},
  email: {{
    type: String,
    required: [true, 'Email is required'],
    unique: true,
    lowercase: true
  }},
  password: {{
    type: String,
    required: [true, 'Password is required'],
    minlength: 6,
    select: false
  }},
  createdAt: {{
    type: Date,
    default: Date.now
  }}
}});

// Hash password before saving
userSchema.pre('save', async function(next) {{
  if (!this.isModified('password')) return next();
  this.password = await bcrypt.hash(this.password, 10);
  next();
}});

// Generate JWT token
userSchema.methods.generateToken = function() {{
  return jwt.sign({{ id: this._id }}, process.env.JWT_SECRET, {{
    expiresIn: process.env.JWT_EXPIRE || '7d'
  }});
}};

// Compare password
userSchema.methods.comparePassword = async function(candidatePassword) {{
  return await bcrypt.compare(candidatePassword, this.password);
}};

module.exports = mongoose.model('User', userSchema);
```

## Backend - server/controllers/{entity}Controller.js

```javascript
const {entity.title()} = require('../models/{entity.title()}');

// @desc    Get all {entities}
// @route   GET /api/{entities}
exports.get{entity.title()}s = async (req, res, next) => {{
  try {{
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const skip = (page - 1) * limit;

    const query = {{ user: req.user.id }};

    if (req.query.status) {{
      query.status = req.query.status;
    }}

    if (req.query.search) {{
      query.title = {{ $regex: req.query.search, $options: 'i' }};
    }}

    const {entities} = await {entity.title()}.find(query)
      .sort({{ createdAt: -1 }})
      .skip(skip)
      .limit(limit);

    const total = await {entity.title()}.countDocuments(query);

    res.json({{
      success: true,
      data: {entities},
      pagination: {{
        page,
        limit,
        total,
        pages: Math.ceil(total / limit)
      }}
    }});
  }} catch (error) {{
    next(error);
  }}
}};

// @desc    Get single {entity}
// @route   GET /api/{entities}/:id
exports.get{entity.title()} = async (req, res, next) => {{
  try {{
    const {entity} = await {entity.title()}.findOne({{
      _id: req.params.id,
      user: req.user.id
    }});

    if (!{entity}) {{
      return res.status(404).json({{ success: false, message: '{entity.title()} not found' }});
    }}

    res.json({{ success: true, data: {entity} }});
  }} catch (error) {{
    next(error);
  }}
}};

// @desc    Create {entity}
// @route   POST /api/{entities}
exports.create{entity.title()} = async (req, res, next) => {{
  try {{
    req.body.user = req.user.id;
    const {entity} = await {entity.title()}.create(req.body);
    res.status(201).json({{ success: true, data: {entity} }});
  }} catch (error) {{
    next(error);
  }}
}};

// @desc    Update {entity}
// @route   PUT /api/{entities}/:id
exports.update{entity.title()} = async (req, res, next) => {{
  try {{
    let {entity} = await {entity.title()}.findOne({{
      _id: req.params.id,
      user: req.user.id
    }});

    if (!{entity}) {{
      return res.status(404).json({{ success: false, message: '{entity.title()} not found' }});
    }}

    {entity} = await {entity.title()}.findByIdAndUpdate(req.params.id, req.body, {{
      new: true,
      runValidators: true
    }});

    res.json({{ success: true, data: {entity} }});
  }} catch (error) {{
    next(error);
  }}
}};

// @desc    Delete {entity}
// @route   DELETE /api/{entities}/:id
exports.delete{entity.title()} = async (req, res, next) => {{
  try {{
    const {entity} = await {entity.title()}.findOneAndDelete({{
      _id: req.params.id,
      user: req.user.id
    }});

    if (!{entity}) {{
      return res.status(404).json({{ success: false, message: '{entity.title()} not found' }});
    }}

    res.json({{ success: true, data: {{}} }});
  }} catch (error) {{
    next(error);
  }}
}};
```

## Backend - server/routes/{entities}.js

```javascript
const express = require('express');
const router = express.Router();
const {{ protect }} = require('../middleware/auth');
const {{
  get{entity.title()}s,
  get{entity.title()},
  create{entity.title()},
  update{entity.title()},
  delete{entity.title()}
}} = require('../controllers/{entity}Controller');

router.use(protect);

router.route('/')
  .get(get{entity.title()}s)
  .post(create{entity.title()});

router.route('/:id')
  .get(get{entity.title()})
  .put(update{entity.title()})
  .delete(delete{entity.title()});

module.exports = router;
```

## Backend - server/middleware/auth.js

```javascript
const jwt = require('jsonwebtoken');
const User = require('../models/User');

exports.protect = async (req, res, next) => {{
  let token;

  if (req.headers.authorization?.startsWith('Bearer')) {{
    token = req.headers.authorization.split(' ')[1];
  }}

  if (!token) {{
    return res.status(401).json({{ success: false, message: 'Not authorized' }});
  }}

  try {{
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = await User.findById(decoded.id);
    next();
  }} catch (error) {{
    return res.status(401).json({{ success: false, message: 'Not authorized' }});
  }}
}};
```

## Frontend - client/src/services/api.js

```javascript
import axios from 'axios';

const api = axios.create({{
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
}});

// Add token to requests
api.interceptors.request.use((config) => {{
  const token = localStorage.getItem('token');
  if (token) {{
    config.headers.Authorization = `Bearer ${{token}}`;
  }}
  return config;
}});

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {{
    if (error.response?.status === 401) {{
      localStorage.removeItem('token');
      window.location.href = '/login';
    }}
    return Promise.reject(error);
  }}
);

export default api;
```

## Frontend - client/src/hooks/use{entity.title()}s.js

```javascript
import {{ useState, useEffect, useCallback }} from 'react';
import api from '../services/api';

export function use{entity.title()}s() {{
  const [{entities}, set{entity.title()}s] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({{
    page: 1,
    limit: 10,
    total: 0
  }});

  const fetch{entity.title()}s = useCallback(async (params = {{}}) => {{
    try {{
      setLoading(true);
      const {{ data }} = await api.get('/{entities}', {{ params }});
      set{entity.title()}s(data.data);
      setPagination(data.pagination);
    }} catch (err) {{
      setError(err.response?.data?.message || 'Error fetching {entities}');
    }} finally {{
      setLoading(false);
    }}
  }}, []);

  const create{entity.title()} = async ({entity}Data) => {{
    const {{ data }} = await api.post('/{entities}', {entity}Data);
    set{entity.title()}s(prev => [data.data, ...prev]);
    return data.data;
  }};

  const update{entity.title()} = async (id, {entity}Data) => {{
    const {{ data }} = await api.put(`/{entities}/${{id}}`, {entity}Data);
    set{entity.title()}s(prev => prev.map(item =>
      item._id === id ? data.data : item
    ));
    return data.data;
  }};

  const delete{entity.title()} = async (id) => {{
    await api.delete(`/{entities}/${{id}}`);
    set{entity.title()}s(prev => prev.filter(item => item._id !== id));
  }};

  useEffect(() => {{
    fetch{entity.title()}s();
  }}, [fetch{entity.title()}s]);

  return {{
    {entities},
    loading,
    error,
    pagination,
    fetch{entity.title()}s,
    create{entity.title()},
    update{entity.title()},
    delete{entity.title()}
  }};
}}
```

## Frontend - client/src/context/AuthContext.jsx

```jsx
import {{ createContext, useState, useEffect }} from 'react';
import api from '../services/api';

export const AuthContext = createContext();

export function AuthProvider({{ children }}) {{
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    const token = localStorage.getItem('token');
    if (token) {{
      loadUser();
    }} else {{
      setLoading(false);
    }}
  }}, []);

  const loadUser = async () => {{
    try {{
      const {{ data }} = await api.get('/auth/me');
      setUser(data.data);
    }} catch (error) {{
      localStorage.removeItem('token');
    }} finally {{
      setLoading(false);
    }}
  }};

  const login = async (email, password) => {{
    const {{ data }} = await api.post('/auth/login', {{ email, password }});
    localStorage.setItem('token', data.token);
    setUser(data.user);
    return data;
  }};

  const register = async (name, email, password) => {{
    const {{ data }} = await api.post('/auth/register', {{ name, email, password }});
    localStorage.setItem('token', data.token);
    setUser(data.user);
    return data;
  }};

  const logout = () => {{
    localStorage.removeItem('token');
    setUser(null);
  }};

  return (
    <AuthContext.Provider value={{{{ user, loading, login, register, logout }}}}>
      {{children}}
    </AuthContext.Provider>
  );
}}
```

## Frontend - client/src/components/{entity.title()}List.jsx

```jsx
import {{ useState }} from 'react';
import {{ use{entity.title()}s }} from '../hooks/use{entity.title()}s';
import {entity.title()}Card from './{entity.title()}Card';
import {entity.title()}Form from './{entity.title()}Form';

export default function {entity.title()}List() {{
  const {{ {entities}, loading, create{entity.title()}, update{entity.title()}, delete{entity.title()} }} = use{entity.title()}s();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);

  const handleSubmit = async (data) => {{
    if (editing) {{
      await update{entity.title()}(editing._id, data);
    }} else {{
      await create{entity.title()}(data);
    }}
    setShowForm(false);
    setEditing(null);
  }};

  if (loading) return <div className="text-center py-10">Loading...</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">My {entity.title()}s</h1>
        <button
          onClick={{() => setShowForm(true)}}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Add {entity.title()}
        </button>
      </div>

      {{showForm && (
        <{entity.title()}Form
          {entity}={{editing}}
          onSubmit={{handleSubmit}}
          onCancel={{() => {{ setShowForm(false); setEditing(null); }}}}
        />
      )}}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {{{entities}.map({entity} => (
          <{entity.title()}Card
            key={{{entity}._id}}
            {entity}={{{entity}}}
            onEdit={{() => {{ setEditing({entity}); setShowForm(true); }}}}
            onDelete={{() => delete{entity.title()}({entity}._id)}}
          />
        ))}}
      </div>
    </div>
  );
}}
```

## Frontend - client/src/App.jsx

```jsx
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom';
import {{ AuthProvider }} from './context/AuthContext';
import Navbar from './components/Navbar';
import PrivateRoute from './components/PrivateRoute';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';

export default function App() {{
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/" element={{<Home />}} />
          <Route path="/login" element={{<Login />}} />
          <Route path="/register" element={{<Register />}} />
          <Route path="/dashboard" element={{
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          }} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}}
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:6
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password

  server:
    build: ./server
    ports:
      - "5000:5000"
    environment:
      - MONGODB_URI=mongodb://admin:password@mongodb:27017/{entity}_db?authSource=admin
      - JWT_SECRET=your_jwt_secret_key
      - PORT=5000
    depends_on:
      - mongodb

  client:
    build: ./client
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:5000/api
    depends_on:
      - server

volumes:
  mongodb_data:
```

## server/package.json

```json
{{
  "name": "{entity}-app-server",
  "version": "1.0.0",
  "scripts": {{
    "start": "node server.js",
    "dev": "nodemon server.js"
  }},
  "dependencies": {{
    "bcryptjs": "^2.4.3",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "express": "^4.18.2",
    "jsonwebtoken": "^9.0.2",
    "mongoose": "^8.0.3"
  }},
  "devDependencies": {{
    "nodemon": "^3.0.2"
  }}
}}
```

This MERN stack application includes:
- **MongoDB** with Mongoose ODM
- **Express.js** REST API with JWT authentication
- **React** frontend with hooks and context
- **Full CRUD** operations
- **Docker Compose** for easy deployment
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer. Generate complete, production-ready applications with frontend, backend, database, and authentication."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_nextjs_fullstack(app_name: str, entity: str, entities: str) -> Dict:
    """Generate Next.js Full-Stack with Prisma example"""

    prompt = f"Create a complete Next.js 14 full-stack {app_name} with App Router, Prisma ORM, PostgreSQL, NextAuth.js authentication, and Tailwind CSS"

    response = f"""I'll create a complete Next.js 14 full-stack {app_name}.

## Project Structure

```
{entity}-app/
├── prisma/
│   └── schema.prisma
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth/
│   │   │   │   └── [...nextauth]/
│   │   │   │       └── route.ts
│   │   │   └── {entities}/
│   │   │       ├── route.ts
│   │   │       └── [id]/
│   │   │           └── route.ts
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── register/
│   │   │       └── page.tsx
│   │   ├── dashboard/
│   │   │   ├── page.tsx
│   │   │   └── {entities}/
│   │   │       ├── page.tsx
│   │   │       ├── new/
│   │   │       │   └── page.tsx
│   │   │       └── [id]/
│   │   │           └── page.tsx
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Card.tsx
│   │   ├── {entity.title()}Form.tsx
│   │   ├── {entity.title()}List.tsx
│   │   └── Navbar.tsx
│   ├── lib/
│   │   ├── prisma.ts
│   │   ├── auth.ts
│   │   └── validations.ts
│   └── types/
│       └── index.ts
├── .env
├── docker-compose.yml
├── package.json
└── tailwind.config.js
```

## prisma/schema.prisma

```prisma
datasource db {{
  provider = "postgresql"
  url      = env("DATABASE_URL")
}}

generator client {{
  provider = "prisma-client-js"
}}

model User {{
  id            String    @id @default(cuid())
  name          String?
  email         String    @unique
  emailVerified DateTime?
  password      String?
  image         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  {entities}       {entity.title()}[]
  accounts      Account[]
  sessions      Session[]
}}

model Account {{
  id                String  @id @default(cuid())
  userId            String
  type              String
  provider          String
  providerAccountId String
  refresh_token     String? @db.Text
  access_token      String? @db.Text
  expires_at        Int?
  token_type        String?
  scope             String?
  id_token          String? @db.Text
  session_state     String?
  user              User    @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@unique([provider, providerAccountId])
}}

model Session {{
  id           String   @id @default(cuid())
  sessionToken String   @unique
  userId       String
  expires      DateTime
  user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
}}

model {entity.title()} {{
  id          String   @id @default(cuid())
  title       String
  description String?
  status      String   @default("active")
  userId      String
  user        User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  @@index([userId])
}}
```

## src/lib/prisma.ts

```typescript
import {{ PrismaClient }} from '@prisma/client';

const globalForPrisma = globalThis as unknown as {{
  prisma: PrismaClient | undefined;
}};

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
```

## src/lib/auth.ts

```typescript
import {{ NextAuthOptions }} from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import GoogleProvider from 'next-auth/providers/google';
import {{ PrismaAdapter }} from '@auth/prisma-adapter';
import bcrypt from 'bcryptjs';
import {{ prisma }} from './prisma';

export const authOptions: NextAuthOptions = {{
  adapter: PrismaAdapter(prisma),
  providers: [
    GoogleProvider({{
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }}),
    CredentialsProvider({{
      name: 'credentials',
      credentials: {{
        email: {{ label: 'Email', type: 'email' }},
        password: {{ label: 'Password', type: 'password' }},
      }},
      async authorize(credentials) {{
        if (!credentials?.email || !credentials?.password) {{
          throw new Error('Invalid credentials');
        }}

        const user = await prisma.user.findUnique({{
          where: {{ email: credentials.email }},
        }});

        if (!user || !user.password) {{
          throw new Error('Invalid credentials');
        }}

        const isValid = await bcrypt.compare(credentials.password, user.password);

        if (!isValid) {{
          throw new Error('Invalid credentials');
        }}

        return {{
          id: user.id,
          email: user.email,
          name: user.name,
        }};
      }},
    }}),
  ],
  session: {{
    strategy: 'jwt',
  }},
  pages: {{
    signIn: '/login',
  }},
  callbacks: {{
    async session({{ session, token }}) {{
      if (session.user) {{
        session.user.id = token.sub!;
      }}
      return session;
    }},
  }},
}};
```

## src/app/api/{entities}/route.ts

```typescript
import {{ NextRequest, NextResponse }} from 'next/server';
import {{ getServerSession }} from 'next-auth';
import {{ prisma }} from '@/lib/prisma';
import {{ authOptions }} from '@/lib/auth';
import {{ z }} from 'zod';

const {entity}Schema = z.object({{
  title: z.string().min(1).max(100),
  description: z.string().optional(),
  status: z.enum(['active', 'inactive', 'pending']).optional(),
}});

export async function GET(request: NextRequest) {{
  try {{
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {{
      return NextResponse.json({{ error: 'Unauthorized' }}, {{ status: 401 }});
    }}

    const {{ searchParams }} = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '10');
    const search = searchParams.get('search') || '';

    const where = {{
      userId: session.user.id,
      ...(search && {{
        title: {{ contains: search, mode: 'insensitive' as const }},
      }}),
    }};

    const [{entities}, total] = await Promise.all([
      prisma.{entity}.findMany({{
        where,
        orderBy: {{ createdAt: 'desc' }},
        skip: (page - 1) * limit,
        take: limit,
      }}),
      prisma.{entity}.count({{ where }}),
    ]);

    return NextResponse.json({{
      data: {entities},
      pagination: {{ page, limit, total, pages: Math.ceil(total / limit) }},
    }});
  }} catch (error) {{
    return NextResponse.json({{ error: 'Internal server error' }}, {{ status: 500 }});
  }}
}}

export async function POST(request: NextRequest) {{
  try {{
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {{
      return NextResponse.json({{ error: 'Unauthorized' }}, {{ status: 401 }});
    }}

    const body = await request.json();
    const validatedData = {entity}Schema.parse(body);

    const {entity} = await prisma.{entity}.create({{
      data: {{
        ...validatedData,
        userId: session.user.id,
      }},
    }});

    return NextResponse.json({{ data: {entity} }}, {{ status: 201 }});
  }} catch (error) {{
    if (error instanceof z.ZodError) {{
      return NextResponse.json({{ error: error.errors }}, {{ status: 400 }});
    }}
    return NextResponse.json({{ error: 'Internal server error' }}, {{ status: 500 }});
  }}
}}
```

## src/app/api/{entities}/[id]/route.ts

```typescript
import {{ NextRequest, NextResponse }} from 'next/server';
import {{ getServerSession }} from 'next-auth';
import {{ prisma }} from '@/lib/prisma';
import {{ authOptions }} from '@/lib/auth';

export async function GET(
  request: NextRequest,
  {{ params }}: {{ params: {{ id: string }} }}
) {{
  try {{
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {{
      return NextResponse.json({{ error: 'Unauthorized' }}, {{ status: 401 }});
    }}

    const {entity} = await prisma.{entity}.findFirst({{
      where: {{
        id: params.id,
        userId: session.user.id,
      }},
    }});

    if (!{entity}) {{
      return NextResponse.json({{ error: 'Not found' }}, {{ status: 404 }});
    }}

    return NextResponse.json({{ data: {entity} }});
  }} catch (error) {{
    return NextResponse.json({{ error: 'Internal server error' }}, {{ status: 500 }});
  }}
}}

export async function PUT(
  request: NextRequest,
  {{ params }}: {{ params: {{ id: string }} }}
) {{
  try {{
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {{
      return NextResponse.json({{ error: 'Unauthorized' }}, {{ status: 401 }});
    }}

    const body = await request.json();

    const {entity} = await prisma.{entity}.updateMany({{
      where: {{
        id: params.id,
        userId: session.user.id,
      }},
      data: body,
    }});

    if ({entity}.count === 0) {{
      return NextResponse.json({{ error: 'Not found' }}, {{ status: 404 }});
    }}

    const updated = await prisma.{entity}.findUnique({{
      where: {{ id: params.id }},
    }});

    return NextResponse.json({{ data: updated }});
  }} catch (error) {{
    return NextResponse.json({{ error: 'Internal server error' }}, {{ status: 500 }});
  }}
}}

export async function DELETE(
  request: NextRequest,
  {{ params }}: {{ params: {{ id: string }} }}
) {{
  try {{
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {{
      return NextResponse.json({{ error: 'Unauthorized' }}, {{ status: 401 }});
    }}

    const {entity} = await prisma.{entity}.deleteMany({{
      where: {{
        id: params.id,
        userId: session.user.id,
      }},
    }});

    if ({entity}.count === 0) {{
      return NextResponse.json({{ error: 'Not found' }}, {{ status: 404 }});
    }}

    return NextResponse.json({{ success: true }});
  }} catch (error) {{
    return NextResponse.json({{ error: 'Internal server error' }}, {{ status: 500 }});
  }}
}}
```

## src/app/dashboard/{entities}/page.tsx

```tsx
import {{ getServerSession }} from 'next-auth';
import {{ redirect }} from 'next/navigation';
import {{ authOptions }} from '@/lib/auth';
import {{ prisma }} from '@/lib/prisma';
import {entity.title()}List from '@/components/{entity.title()}List';

export default async function {entity.title()}sPage() {{
  const session = await getServerSession(authOptions);

  if (!session) {{
    redirect('/login');
  }}

  const {entities} = await prisma.{entity}.findMany({{
    where: {{ userId: session.user.id }},
    orderBy: {{ createdAt: 'desc' }},
  }});

  return (
    <div className="container mx-auto px-4 py-8">
      <{entity.title()}List initial{entity.title()}s={{{entities}}} />
    </div>
  );
}}
```

## src/components/{entity.title()}List.tsx

```tsx
'use client';

import {{ useState }} from 'react';
import {{ useRouter }} from 'next/navigation';
import {entity.title()}Form from './{entity.title()}Form';
import Card from './ui/Card';
import Button from './ui/Button';

interface {entity.title()} {{
  id: string;
  title: string;
  description: string | null;
  status: string;
  createdAt: Date;
}}

export default function {entity.title()}List({{ initial{entity.title()}s }}: {{ initial{entity.title()}s: {entity.title()}[] }}) {{
  const [{entities}, set{entity.title()}s] = useState(initial{entity.title()}s);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<{entity.title()} | null>(null);
  const router = useRouter();

  const handleCreate = async (data: any) => {{
    const res = await fetch('/api/{entities}', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(data),
    }});

    if (res.ok) {{
      const {{ data: new{entity.title()} }} = await res.json();
      set{entity.title()}s([new{entity.title()}, ...{entities}]);
      setShowForm(false);
    }}
  }};

  const handleDelete = async (id: string) => {{
    if (!confirm('Are you sure?')) return;

    const res = await fetch(`/api/{entities}/${{id}}`, {{ method: 'DELETE' }});

    if (res.ok) {{
      set{entity.title()}s({entities}.filter(item => item.id !== id));
    }}
  }};

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">My {entity.title()}s</h1>
        <Button onClick={{() => setShowForm(true)}}>
          Add {entity.title()}
        </Button>
      </div>

      {{showForm && (
        <div className="mb-6">
          <{entity.title()}Form
            onSubmit={{handleCreate}}
            onCancel={{() => setShowForm(false)}}
          />
        </div>
      )}}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {{{entities}.map({entity} => (
          <Card key={{{entity}.id}} className="p-4">
            <h3 className="font-semibold">{{{entity}.title}}</h3>
            <p className="text-gray-600 text-sm">{{{entity}.description}}</p>
            <div className="flex gap-2 mt-4">
              <Button size="sm" variant="outline" onClick={{() => router.push(`/dashboard/{entities}/${{{entity}.id}}`)}}>
                Edit
              </Button>
              <Button size="sm" variant="danger" onClick={{() => handleDelete({entity}.id)}}>
                Delete
              </Button>
            </div>
          </Card>
        ))}}
      </div>
    </div>
  );
}}
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {entity}_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/{entity}_db
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=your-secret-key
    depends_on:
      - postgres

volumes:
  postgres_data:
```

## package.json

```json
{{
  "name": "{entity}-nextjs-app",
  "version": "1.0.0",
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "db:push": "prisma db push",
    "db:studio": "prisma studio"
  }},
  "dependencies": {{
    "@auth/prisma-adapter": "^1.0.0",
    "@prisma/client": "^5.7.0",
    "bcryptjs": "^2.4.3",
    "next": "14.0.4",
    "next-auth": "^4.24.5",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zod": "^3.22.4"
  }},
  "devDependencies": {{
    "@types/bcryptjs": "^2.4.6",
    "@types/node": "^20.10.5",
    "@types/react": "^18.2.45",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "prisma": "^5.7.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.3"
  }}
}}
```

This Next.js 14 full-stack application includes:
- **App Router** with server and client components
- **Prisma ORM** with PostgreSQL
- **NextAuth.js** with credentials and OAuth
- **API Routes** with validation (Zod)
- **Tailwind CSS** styling
- **Docker Compose** deployment
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer specializing in Next.js. Generate complete, production-ready applications."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_vue_fastapi(app_name: str, entity: str, entities: str) -> Dict:
    """Generate Vue 3 + FastAPI example"""

    prompt = f"Create a complete Vue 3 + FastAPI {app_name} with Composition API, Pinia store, FastAPI backend, PostgreSQL, and JWT authentication"

    response = f"""I'll create a complete Vue 3 + FastAPI {app_name}.

## Project Structure

```
{entity}-app/
├── frontend/           # Vue 3 Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── {entity.title()}List.vue
│   │   │   ├── {entity.title()}Form.vue
│   │   │   └── {entity.title()}Card.vue
│   │   ├── views/
│   │   │   ├── HomeView.vue
│   │   │   ├── LoginView.vue
│   │   │   └── DashboardView.vue
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   └── {entities}.ts
│   │   ├── composables/
│   │   │   └── use{entity.title()}s.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── App.vue
│   │   └── main.ts
│   └── package.json
├── backend/            # FastAPI Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       └── {entities}.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   └── {entity}.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   └── {entity}.py
│   │   └── main.py
│   └── requirements.txt
└── docker-compose.yml
```

## Backend - app/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, {entities}
from app.core.config import settings
from app.core.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="{app_name} API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router({entities}.router, prefix="/api/{entities}", tags=["{entity.title()}s"])

@app.get("/health")
async def health():
    return {{"status": "healthy"}}
```

## Backend - app/models/{entity}.py

```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class {entity.title()}(Base):
    __tablename__ = "{entities}"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="active")
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="{entities}")
```

## Backend - app/schemas/{entity}.py

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class {entity.title()}Base(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[str] = "active"

class {entity.title()}Create({entity.title()}Base):
    pass

class {entity.title()}Update(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[str] = None

class {entity.title()}Response({entity.title()}Base):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class {entity.title()}ListResponse(BaseModel):
    data: list[{entity.title()}Response]
    total: int
    page: int
    limit: int
```

## Backend - app/api/routes/{entities}.py

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db, get_current_user
from app.models.{entity} import {entity.title()}
from app.models.user import User
from app.schemas.{entity} import (
    {entity.title()}Create,
    {entity.title()}Update,
    {entity.title()}Response,
    {entity.title()}ListResponse,
)

router = APIRouter()

@router.get("/", response_model={entity.title()}ListResponse)
async def list_{entities}(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query({entity.title()}).filter({entity.title()}.user_id == current_user.id)

    if search:
        query = query.filter({entity.title()}.title.ilike(f"%{{search}}%"))
    if status:
        query = query.filter({entity.title()}.status == status)

    total = query.count()
    {entities} = query.offset((page - 1) * limit).limit(limit).all()

    return {entity.title()}ListResponse(
        data={entities},
        total=total,
        page=page,
        limit=limit
    )

@router.get("/{{id}}", response_model={entity.title()}Response)
async def get_{entity}(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    {entity} = db.query({entity.title()}).filter(
        {entity.title()}.id == id,
        {entity.title()}.user_id == current_user.id
    ).first()

    if not {entity}:
        raise HTTPException(status_code=404, detail="{entity.title()} not found")

    return {entity}

@router.post("/", response_model={entity.title()}Response, status_code=201)
async def create_{entity}(
    data: {entity.title()}Create,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    {entity} = {entity.title()}(**data.model_dump(), user_id=current_user.id)
    db.add({entity})
    db.commit()
    db.refresh({entity})
    return {entity}

@router.put("/{{id}}", response_model={entity.title()}Response)
async def update_{entity}(
    id: str,
    data: {entity.title()}Update,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    {entity} = db.query({entity.title()}).filter(
        {entity.title()}.id == id,
        {entity.title()}.user_id == current_user.id
    ).first()

    if not {entity}:
        raise HTTPException(status_code=404, detail="{entity.title()} not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr({entity}, key, value)

    db.commit()
    db.refresh({entity})
    return {entity}

@router.delete("/{{id}}", status_code=204)
async def delete_{entity}(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    {entity} = db.query({entity.title()}).filter(
        {entity.title()}.id == id,
        {entity.title()}.user_id == current_user.id
    ).first()

    if not {entity}:
        raise HTTPException(status_code=404, detail="{entity.title()} not found")

    db.delete({entity})
    db.commit()
```

## Frontend - src/stores/{entities}.ts

```typescript
import {{ defineStore }} from 'pinia';
import {{ ref, computed }} from 'vue';
import api from '@/services/api';

interface {entity.title()} {{
  id: string;
  title: string;
  description: string | null;
  status: string;
  createdAt: string;
}}

export const use{entity.title()}Store = defineStore('{entities}', () => {{
  const {entities} = ref<{entity.title()}[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const pagination = ref({{ page: 1, limit: 10, total: 0 }});

  const fetch{entity.title()}s = async (params?: Record<string, any>) => {{
    loading.value = true;
    error.value = null;
    try {{
      const {{ data }} = await api.get('/{entities}', {{ params }});
      {entities}.value = data.data;
      pagination.value = {{
        page: data.page,
        limit: data.limit,
        total: data.total,
      }};
    }} catch (e: any) {{
      error.value = e.response?.data?.detail || 'Error fetching {entities}';
    }} finally {{
      loading.value = false;
    }}
  }};

  const create{entity.title()} = async (data: Partial<{entity.title()}>) => {{
    const {{ data: new{entity.title()} }} = await api.post('/{entities}', data);
    {entities}.value.unshift(new{entity.title()});
    return new{entity.title()};
  }};

  const update{entity.title()} = async (id: string, data: Partial<{entity.title()}>) => {{
    const {{ data: updated }} = await api.put(`/{entities}/${{id}}`, data);
    const index = {entities}.value.findIndex(item => item.id === id);
    if (index !== -1) {{
      {entities}.value[index] = updated;
    }}
    return updated;
  }};

  const delete{entity.title()} = async (id: string) => {{
    await api.delete(`/{entities}/${{id}}`);
    {entities}.value = {entities}.value.filter(item => item.id !== id);
  }};

  return {{
    {entities},
    loading,
    error,
    pagination,
    fetch{entity.title()}s,
    create{entity.title()},
    update{entity.title()},
    delete{entity.title()},
  }};
}});
```

## Frontend - src/components/{entity.title()}List.vue

```vue
<script setup lang="ts">
import {{ ref, onMounted }} from 'vue';
import {{ use{entity.title()}Store }} from '@/stores/{entities}';
import {entity.title()}Card from './{entity.title()}Card.vue';
import {entity.title()}Form from './{entity.title()}Form.vue';

const store = use{entity.title()}Store();
const showForm = ref(false);
const editing = ref(null);

onMounted(() => {{
  store.fetch{entity.title()}s();
}});

const handleSubmit = async (data: any) => {{
  if (editing.value) {{
    await store.update{entity.title()}(editing.value.id, data);
  }} else {{
    await store.create{entity.title()}(data);
  }}
  showForm.value = false;
  editing.value = null;
}};

const handleEdit = ({entity}: any) => {{
  editing.value = {entity};
  showForm.value = true;
}};

const handleDelete = async (id: string) => {{
  if (confirm('Are you sure?')) {{
    await store.delete{entity.title()}(id);
  }}
}};
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">My {entity.title()}s</h1>
      <button
        @click="showForm = true"
        class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
      >
        Add {entity.title()}
      </button>
    </div>

    <{entity.title()}Form
      v-if="showForm"
      :{entity}="editing"
      @submit="handleSubmit"
      @cancel="showForm = false; editing = null"
    />

    <div v-if="store.loading" class="text-center py-10">Loading...</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <{entity.title()}Card
        v-for="{entity} in store.{entities}"
        :key="{entity}.id"
        :{entity}="{entity}"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </div>
  </div>
</template>
```

## Frontend - src/services/api.ts

```typescript
import axios from 'axios';
import {{ useAuthStore }} from '@/stores/auth';

const api = axios.create({{
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
}});

api.interceptors.request.use((config) => {{
  const authStore = useAuthStore();
  if (authStore.token) {{
    config.headers.Authorization = `Bearer ${{authStore.token}}`;
  }}
  return config;
}});

api.interceptors.response.use(
  (response) => response,
  (error) => {{
    if (error.response?.status === 401) {{
      const authStore = useAuthStore();
      authStore.logout();
      window.location.href = '/login';
    }}
    return Promise.reject(error);
  }}
);

export default api;
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {entity}_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/{entity}_db
      - SECRET_KEY=your-secret-key
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000/api
    depends_on:
      - backend

volumes:
  postgres_data:
```

This Vue 3 + FastAPI application includes:
- **Vue 3** with Composition API and TypeScript
- **Pinia** for state management
- **FastAPI** with async endpoints
- **SQLAlchemy** ORM with PostgreSQL
- **JWT Authentication**
- **Docker Compose** deployment
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer specializing in Vue.js and Python. Generate complete, production-ready applications."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_angular_nestjs(app_name: str, entity: str, entities: str) -> Dict:
    """Generate Angular + NestJS example"""

    prompt = f"Create a complete Angular 17 + NestJS {app_name} with standalone components, NestJS backend, TypeORM, PostgreSQL, and JWT authentication"

    response = f"""I'll create a complete Angular 17 + NestJS {app_name}.

## Project Structure

```
{entity}-app/
├── frontend/           # Angular 17
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   ├── services/
│   │   │   │   │   ├── api.service.ts
│   │   │   │   │   └── auth.service.ts
│   │   │   │   ├── guards/
│   │   │   │   │   └── auth.guard.ts
│   │   │   │   └── interceptors/
│   │   │   │       └── auth.interceptor.ts
│   │   │   ├── features/
│   │   │   │   ├── auth/
│   │   │   │   │   ├── login/
│   │   │   │   │   └── register/
│   │   │   │   └── {entities}/
│   │   │   │       ├── {entity}-list/
│   │   │   │       ├── {entity}-form/
│   │   │   │       └── {entity}-detail/
│   │   │   ├── shared/
│   │   │   │   └── components/
│   │   │   ├── app.component.ts
│   │   │   ├── app.routes.ts
│   │   │   └── app.config.ts
│   │   └── main.ts
│   └── package.json
├── backend/            # NestJS
│   ├── src/
│   │   ├── auth/
│   │   │   ├── auth.controller.ts
│   │   │   ├── auth.service.ts
│   │   │   ├── auth.module.ts
│   │   │   └── jwt.strategy.ts
│   │   ├── {entities}/
│   │   │   ├── {entities}.controller.ts
│   │   │   ├── {entities}.service.ts
│   │   │   ├── {entities}.module.ts
│   │   │   ├── entities/{entity}.entity.ts
│   │   │   └── dto/
│   │   │       ├── create-{entity}.dto.ts
│   │   │       └── update-{entity}.dto.ts
│   │   ├── users/
│   │   │   └── ...
│   │   ├── app.module.ts
│   │   └── main.ts
│   └── package.json
└── docker-compose.yml
```

## Backend - src/{entities}/{entities}.controller.ts

```typescript
import {{
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  Param,
  Query,
  UseGuards,
  Request,
}} from '@nestjs/common';
import {{ JwtAuthGuard }} from '../auth/jwt-auth.guard';
import {{ {entity.title()}sService }} from './{entities}.service';
import {{ Create{entity.title()}Dto }} from './dto/create-{entity}.dto';
import {{ Update{entity.title()}Dto }} from './dto/update-{entity}.dto';

@Controller('{entities}')
@UseGuards(JwtAuthGuard)
export class {entity.title()}sController {{
  constructor(private readonly {entities}Service: {entity.title()}sService) {{}}

  @Get()
  async findAll(
    @Request() req,
    @Query('page') page: number = 1,
    @Query('limit') limit: number = 10,
    @Query('search') search?: string,
  ) {{
    return this.{entities}Service.findAll(req.user.id, {{ page, limit, search }});
  }}

  @Get(':id')
  async findOne(@Request() req, @Param('id') id: string) {{
    return this.{entities}Service.findOne(id, req.user.id);
  }}

  @Post()
  async create(@Request() req, @Body() create{entity.title()}Dto: Create{entity.title()}Dto) {{
    return this.{entities}Service.create(create{entity.title()}Dto, req.user.id);
  }}

  @Put(':id')
  async update(
    @Request() req,
    @Param('id') id: string,
    @Body() update{entity.title()}Dto: Update{entity.title()}Dto,
  ) {{
    return this.{entities}Service.update(id, update{entity.title()}Dto, req.user.id);
  }}

  @Delete(':id')
  async remove(@Request() req, @Param('id') id: string) {{
    return this.{entities}Service.remove(id, req.user.id);
  }}
}}
```

## Backend - src/{entities}/{entities}.service.ts

```typescript
import {{ Injectable, NotFoundException }} from '@nestjs/common';
import {{ InjectRepository }} from '@nestjs/typeorm';
import {{ Repository, Like }} from 'typeorm';
import {{ {entity.title()} }} from './entities/{entity}.entity';
import {{ Create{entity.title()}Dto }} from './dto/create-{entity}.dto';
import {{ Update{entity.title()}Dto }} from './dto/update-{entity}.dto';

@Injectable()
export class {entity.title()}sService {{
  constructor(
    @InjectRepository({entity.title()})
    private {entities}Repository: Repository<{entity.title()}>,
  ) {{}}

  async findAll(userId: string, options: {{ page: number; limit: number; search?: string }}) {{
    const {{ page, limit, search }} = options;

    const where: any = {{ userId }};
    if (search) {{
      where.title = Like(`%${{search}}%`);
    }}

    const [data, total] = await this.{entities}Repository.findAndCount({{
      where,
      order: {{ createdAt: 'DESC' }},
      skip: (page - 1) * limit,
      take: limit,
    }});

    return {{
      data,
      total,
      page,
      limit,
      pages: Math.ceil(total / limit),
    }};
  }}

  async findOne(id: string, userId: string) {{
    const {entity} = await this.{entities}Repository.findOne({{
      where: {{ id, userId }},
    }});

    if (!{entity}) {{
      throw new NotFoundException('{entity.title()} not found');
    }}

    return {entity};
  }}

  async create(create{entity.title()}Dto: Create{entity.title()}Dto, userId: string) {{
    const {entity} = this.{entities}Repository.create({{
      ...create{entity.title()}Dto,
      userId,
    }});
    return this.{entities}Repository.save({entity});
  }}

  async update(id: string, update{entity.title()}Dto: Update{entity.title()}Dto, userId: string) {{
    const {entity} = await this.findOne(id, userId);
    Object.assign({entity}, update{entity.title()}Dto);
    return this.{entities}Repository.save({entity});
  }}

  async remove(id: string, userId: string) {{
    const {entity} = await this.findOne(id, userId);
    await this.{entities}Repository.remove({entity});
    return {{ deleted: true }};
  }}
}}
```

## Backend - src/{entities}/entities/{entity}.entity.ts

```typescript
import {{
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn,
}} from 'typeorm';
import {{ User }} from '../../users/entities/user.entity';

@Entity('{entities}')
export class {entity.title()} {{
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  title: string;

  @Column({{ nullable: true }})
  description: string;

  @Column({{ default: 'active' }})
  status: string;

  @Column()
  userId: string;

  @ManyToOne(() => User, (user) => user.{entities})
  user: User;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}}
```

## Frontend - src/app/features/{entities}/{entity}-list/{entity}-list.component.ts

```typescript
import {{ Component, OnInit, inject, signal }} from '@angular/core';
import {{ CommonModule }} from '@angular/common';
import {{ RouterLink }} from '@angular/router';
import {{ {entity.title()}Service }} from '../../../core/services/{entity}.service';
import {{ {entity.title()}CardComponent }} from '../{entity}-card/{entity}-card.component';

@Component({{
  selector: 'app-{entity}-list',
  standalone: true,
  imports: [CommonModule, RouterLink, {entity.title()}CardComponent],
  template: `
    <div class="container mx-auto px-4 py-8">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">My {entity.title()}s</h1>
        <a routerLink="/{entities}/new" class="bg-blue-500 text-white px-4 py-2 rounded">
          Add {entity.title()}
        </a>
      </div>

      @if (loading()) {{
        <div class="text-center py-10">Loading...</div>
      }} @else {{
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          @for ({entity} of {entities}(); track {entity}.id) {{
            <app-{entity}-card
              [{entity}]="{entity}"
              (delete)="onDelete($event)"
            />
          }}
        </div>
      }}
    </div>
  `,
}})
export class {entity.title()}ListComponent implements OnInit {{
  private {entity}Service = inject({entity.title()}Service);

  {entities} = signal<any[]>([]);
  loading = signal(true);

  ngOnInit() {{
    this.load{entity.title()}s();
  }}

  async load{entity.title()}s() {{
    try {{
      const response = await this.{entity}Service.getAll();
      this.{entities}.set(response.data);
    }} finally {{
      this.loading.set(false);
    }}
  }}

  async onDelete(id: string) {{
    if (confirm('Are you sure?')) {{
      await this.{entity}Service.delete(id);
      this.{entities}.update({entities} => {entities}.filter(item => item.id !== id));
    }}
  }}
}}
```

## Frontend - src/app/core/services/{entity}.service.ts

```typescript
import {{ Injectable, inject }} from '@angular/core';
import {{ HttpClient }} from '@angular/common/http';
import {{ firstValueFrom }} from 'rxjs';
import {{ environment }} from '../../../environments/environment';

@Injectable({{
  providedIn: 'root',
}})
export class {entity.title()}Service {{
  private http = inject(HttpClient);
  private apiUrl = `${{environment.apiUrl}}/{entities}`;

  async getAll(params?: any) {{
    return firstValueFrom(this.http.get<any>(this.apiUrl, {{ params }}));
  }}

  async getOne(id: string) {{
    return firstValueFrom(this.http.get<any>(`${{this.apiUrl}}/${{id}}`));
  }}

  async create(data: any) {{
    return firstValueFrom(this.http.post<any>(this.apiUrl, data));
  }}

  async update(id: string, data: any) {{
    return firstValueFrom(this.http.put<any>(`${{this.apiUrl}}/${{id}}`, data));
  }}

  async delete(id: string) {{
    return firstValueFrom(this.http.delete<any>(`${{this.apiUrl}}/${{id}}`));
  }}
}}
```

## Frontend - src/app/app.routes.ts

```typescript
import {{ Routes }} from '@angular/router';
import {{ authGuard }} from './core/guards/auth.guard';

export const routes: Routes = [
  {{
    path: '',
    loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent),
  }},
  {{
    path: 'login',
    loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent),
  }},
  {{
    path: 'register',
    loadComponent: () => import('./features/auth/register/register.component').then(m => m.RegisterComponent),
  }},
  {{
    path: '{entities}',
    canActivate: [authGuard],
    children: [
      {{
        path: '',
        loadComponent: () => import('./features/{entities}/{entity}-list/{entity}-list.component').then(m => m.{entity.title()}ListComponent),
      }},
      {{
        path: 'new',
        loadComponent: () => import('./features/{entities}/{entity}-form/{entity}-form.component').then(m => m.{entity.title()}FormComponent),
      }},
      {{
        path: ':id',
        loadComponent: () => import('./features/{entities}/{entity}-detail/{entity}-detail.component').then(m => m.{entity.title()}DetailComponent),
      }},
      {{
        path: ':id/edit',
        loadComponent: () => import('./features/{entities}/{entity}-form/{entity}-form.component').then(m => m.{entity.title()}FormComponent),
      }},
    ],
  }},
];
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {entity}_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/{entity}_db
      - JWT_SECRET=your-secret-key
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "4200:4200"
    depends_on:
      - backend

volumes:
  postgres_data:
```

This Angular 17 + NestJS application includes:
- **Angular 17** with standalone components and signals
- **NestJS** with TypeORM
- **PostgreSQL** database
- **JWT Authentication**
- **Lazy-loaded routes**
- **Docker Compose** deployment
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer specializing in Angular and NestJS. Generate complete, production-ready applications."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_react_spring(app_name: str, entity: str, entities: str) -> Dict:
    """Generate React + Spring Boot example"""

    prompt = f"Create a complete React + Spring Boot {app_name} with React frontend, Spring Boot backend, JPA, MySQL, and Spring Security JWT"

    response = f"""I'll create a complete React + Spring Boot {app_name}.

## Project Structure

```
{entity}-app/
├── frontend/           # React
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── App.tsx
│   └── package.json
├── backend/            # Spring Boot
│   ├── src/main/java/com/{entity}app/
│   │   ├── config/
│   │   │   ├── SecurityConfig.java
│   │   │   └── JwtConfig.java
│   │   ├── controller/
│   │   │   ├── AuthController.java
│   │   │   └── {entity.title()}Controller.java
│   │   ├── service/
│   │   │   └── {entity.title()}Service.java
│   │   ├── repository/
│   │   │   └── {entity.title()}Repository.java
│   │   ├── model/
│   │   │   ├── User.java
│   │   │   └── {entity.title()}.java
│   │   ├── dto/
│   │   │   └── {entity.title()}Dto.java
│   │   └── Application.java
│   └── pom.xml
└── docker-compose.yml
```

## Backend - {entity.title()}Controller.java

```java
package com.{entity}app.controller;

import com.{entity}app.dto.{entity.title()}Dto;
import com.{entity}app.model.{entity.title()};
import com.{entity}app.service.{entity.title()}Service;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/{entities}")
@RequiredArgsConstructor
public class {entity.title()}Controller {{

    private final {entity.title()}Service {entity}Service;

    @GetMapping
    public ResponseEntity<Page<{entity.title()}>> getAll(
            @AuthenticationPrincipal UserDetails userDetails,
            Pageable pageable,
            @RequestParam(required = false) String search
    ) {{
        Page<{entity.title()}> {entities} = {entity}Service.findAll(userDetails.getUsername(), search, pageable);
        return ResponseEntity.ok({entities});
    }}

    @GetMapping("/{{id}}")
    public ResponseEntity<{entity.title()}> getOne(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable Long id
    ) {{
        {entity.title()} {entity} = {entity}Service.findById(id, userDetails.getUsername());
        return ResponseEntity.ok({entity});
    }}

    @PostMapping
    public ResponseEntity<{entity.title()}> create(
            @AuthenticationPrincipal UserDetails userDetails,
            @Valid @RequestBody {entity.title()}Dto dto
    ) {{
        {entity.title()} {entity} = {entity}Service.create(dto, userDetails.getUsername());
        return ResponseEntity.status(HttpStatus.CREATED).body({entity});
    }}

    @PutMapping("/{{id}}")
    public ResponseEntity<{entity.title()}> update(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable Long id,
            @Valid @RequestBody {entity.title()}Dto dto
    ) {{
        {entity.title()} {entity} = {entity}Service.update(id, dto, userDetails.getUsername());
        return ResponseEntity.ok({entity});
    }}

    @DeleteMapping("/{{id}}")
    public ResponseEntity<Void> delete(
            @AuthenticationPrincipal UserDetails userDetails,
            @PathVariable Long id
    ) {{
        {entity}Service.delete(id, userDetails.getUsername());
        return ResponseEntity.noContent().build();
    }}
}}
```

## Backend - {entity.title()}.java (Entity)

```java
package com.{entity}app.model;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "{entities}")
public class {entity.title()} {{

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(length = 20)
    private String status = "active";

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}}
```

## Backend - {entity.title()}Service.java

```java
package com.{entity}app.service;

import com.{entity}app.dto.{entity.title()}Dto;
import com.{entity}app.exception.ResourceNotFoundException;
import com.{entity}app.model.{entity.title()};
import com.{entity}app.model.User;
import com.{entity}app.repository.{entity.title()}Repository;
import com.{entity}app.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class {entity.title()}Service {{

    private final {entity.title()}Repository {entity}Repository;
    private final UserRepository userRepository;

    public Page<{entity.title()}> findAll(String username, String search, Pageable pageable) {{
        User user = getUserByUsername(username);
        if (search != null && !search.isEmpty()) {{
            return {entity}Repository.findByUserAndTitleContainingIgnoreCase(user, search, pageable);
        }}
        return {entity}Repository.findByUser(user, pageable);
    }}

    public {entity.title()} findById(Long id, String username) {{
        User user = getUserByUsername(username);
        return {entity}Repository.findByIdAndUser(id, user)
                .orElseThrow(() -> new ResourceNotFoundException("{entity.title()} not found"));
    }}

    @Transactional
    public {entity.title()} create({entity.title()}Dto dto, String username) {{
        User user = getUserByUsername(username);
        {entity.title()} {entity} = new {entity.title()}();
        {entity}.setTitle(dto.getTitle());
        {entity}.setDescription(dto.getDescription());
        {entity}.setStatus(dto.getStatus() != null ? dto.getStatus() : "active");
        {entity}.setUser(user);
        return {entity}Repository.save({entity});
    }}

    @Transactional
    public {entity.title()} update(Long id, {entity.title()}Dto dto, String username) {{
        {entity.title()} {entity} = findById(id, username);
        if (dto.getTitle() != null) {entity}.setTitle(dto.getTitle());
        if (dto.getDescription() != null) {entity}.setDescription(dto.getDescription());
        if (dto.getStatus() != null) {entity}.setStatus(dto.getStatus());
        return {entity}Repository.save({entity});
    }}

    @Transactional
    public void delete(Long id, String username) {{
        {entity.title()} {entity} = findById(id, username);
        {entity}Repository.delete({entity});
    }}

    private User getUserByUsername(String username) {{
        return userRepository.findByEmail(username)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));
    }}
}}
```

## Backend - pom.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>

    <groupId>com.{entity}app</groupId>
    <artifactId>{entity}-app</artifactId>
    <version>1.0.0</version>

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
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-api</artifactId>
            <version>0.12.3</version>
        </dependency>
        <dependency>
            <groupId>mysql</groupId>
            <artifactId>mysql-connector-java</artifactId>
            <version>8.0.33</version>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
    </dependencies>
</project>
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: {entity}_db
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/{entity}_db
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=password
      - JWT_SECRET=your-secret-key
    depends_on:
      - mysql

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  mysql_data:
```

This React + Spring Boot application includes:
- **React** frontend with hooks
- **Spring Boot 3** with Spring Security
- **JPA** with MySQL
- **JWT Authentication**
- **Docker Compose** deployment
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer specializing in React and Spring Boot. Generate complete, production-ready applications."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_all_examples() -> List[Dict]:
    """Generate all full-stack examples"""
    examples = []

    for app_name, entity, entities in APPS:
        # Generate for each stack
        examples.append(generate_mern_stack(app_name, entity, entities))
        examples.append(generate_nextjs_fullstack(app_name, entity, entities))
        examples.append(generate_vue_fastapi(app_name, entity, entities))
        examples.append(generate_angular_nestjs(app_name, entity, entities))
        examples.append(generate_react_spring(app_name, entity, entities))

    return examples


def main():
    print("=" * 70)
    print("GENERATING FULL-STACK APPLICATION EXAMPLES")
    print("=" * 70)

    examples = generate_all_examples()
    print(f"\nGenerated {len(examples)} examples")

    # Save
    OUTPUT_DIR.mkdir(exist_ok=True)

    random.shuffle(examples)
    eval_size = max(5, len(examples) // 10)

    eval_examples = examples[:eval_size]
    train_examples = examples[eval_size:]

    with open(OUTPUT_DIR / "train.jsonl", 'w', encoding='utf-8') as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    with open(OUTPUT_DIR / "eval.jsonl", 'w', encoding='utf-8') as f:
        for ex in eval_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nSaved to {OUTPUT_DIR}")
    print(f"  Train: {len(train_examples)}")
    print(f"  Eval: {len(eval_examples)}")
    print(f"\nStacks covered:")
    print("  - MERN (MongoDB, Express, React, Node)")
    print("  - Next.js + Prisma + PostgreSQL")
    print("  - Vue 3 + FastAPI + PostgreSQL")
    print("  - Angular 17 + NestJS + PostgreSQL")
    print("  - React + Spring Boot + MySQL")


if __name__ == "__main__":
    main()
