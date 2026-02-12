"""
Technology-Agnostic Training Data Generator
Generates code samples for ALL major tech stacks
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from itertools import product


# ============================================================================
# TECHNOLOGY DEFINITIONS
# ============================================================================

FRONTEND_FRAMEWORKS = {
    "react": {
        "name": "React",
        "language": "TypeScript",
        "styling": ["Tailwind CSS", "CSS Modules", "Styled Components", "Material UI", "Chakra UI"],
        "state": ["useState", "Redux", "Zustand", "Jotai", "React Query"],
        "form": ["react-hook-form", "Formik", "React Final Form"],
        "validation": ["Zod", "Yup", "Joi"],
    },
    "vue": {
        "name": "Vue.js",
        "language": "TypeScript",
        "styling": ["Tailwind CSS", "Vuetify", "PrimeVue", "Element Plus"],
        "state": ["Pinia", "Vuex"],
        "form": ["VeeValidate", "FormKit"],
        "validation": ["Zod", "Yup", "Vuelidate"],
    },
    "angular": {
        "name": "Angular",
        "language": "TypeScript",
        "styling": ["Angular Material", "Tailwind CSS", "PrimeNG", "NgBootstrap"],
        "state": ["NgRx", "Akita", "Services"],
        "form": ["Reactive Forms", "Template Forms"],
        "validation": ["Built-in Validators", "Custom Validators"],
    },
    "svelte": {
        "name": "Svelte",
        "language": "TypeScript",
        "styling": ["Tailwind CSS", "Skeleton UI", "Carbon Components"],
        "state": ["Svelte Stores", "Svelte Query"],
        "form": ["Felte", "Superforms"],
        "validation": ["Zod", "Yup"],
    },
    "nextjs": {
        "name": "Next.js",
        "language": "TypeScript",
        "styling": ["Tailwind CSS", "CSS Modules", "Styled Components"],
        "state": ["React Query", "SWR", "Zustand"],
        "form": ["react-hook-form", "Formik"],
        "validation": ["Zod", "Yup"],
    },
    "nuxt": {
        "name": "Nuxt.js",
        "language": "TypeScript",
        "styling": ["Tailwind CSS", "Vuetify", "UnoCSS"],
        "state": ["Pinia", "useState"],
        "form": ["VeeValidate", "FormKit"],
        "validation": ["Zod", "Yup"],
    },
}

BACKEND_FRAMEWORKS = {
    "fastapi": {
        "name": "FastAPI",
        "language": "Python",
        "orm": ["SQLAlchemy", "Tortoise ORM", "SQLModel"],
        "database": ["PostgreSQL", "MySQL", "SQLite", "MongoDB"],
        "auth": ["JWT", "OAuth2", "Session"],
    },
    "django": {
        "name": "Django",
        "language": "Python",
        "orm": ["Django ORM"],
        "database": ["PostgreSQL", "MySQL", "SQLite"],
        "auth": ["Django Auth", "JWT", "OAuth2"],
    },
    "flask": {
        "name": "Flask",
        "language": "Python",
        "orm": ["SQLAlchemy", "Flask-SQLAlchemy"],
        "database": ["PostgreSQL", "MySQL", "SQLite"],
        "auth": ["Flask-Login", "JWT", "OAuth2"],
    },
    "express": {
        "name": "Express.js",
        "language": "TypeScript",
        "orm": ["Prisma", "TypeORM", "Sequelize", "Mongoose"],
        "database": ["PostgreSQL", "MySQL", "MongoDB"],
        "auth": ["Passport.js", "JWT", "OAuth2"],
    },
    "nestjs": {
        "name": "NestJS",
        "language": "TypeScript",
        "orm": ["Prisma", "TypeORM", "MikroORM"],
        "database": ["PostgreSQL", "MySQL", "MongoDB"],
        "auth": ["Passport.js", "JWT", "Guards"],
    },
    "spring": {
        "name": "Spring Boot",
        "language": "Java",
        "orm": ["Spring Data JPA", "Hibernate"],
        "database": ["PostgreSQL", "MySQL", "H2"],
        "auth": ["Spring Security", "JWT", "OAuth2"],
    },
    "dotnet": {
        "name": ".NET Core",
        "language": "C#",
        "orm": ["Entity Framework Core", "Dapper"],
        "database": ["SQL Server", "PostgreSQL", "SQLite"],
        "auth": ["Identity", "JWT", "OAuth2"],
    },
    "go": {
        "name": "Go (Gin/Fiber)",
        "language": "Go",
        "orm": ["GORM", "sqlx", "ent"],
        "database": ["PostgreSQL", "MySQL", "SQLite"],
        "auth": ["JWT", "OAuth2"],
    },
    "rails": {
        "name": "Ruby on Rails",
        "language": "Ruby",
        "orm": ["Active Record"],
        "database": ["PostgreSQL", "MySQL", "SQLite"],
        "auth": ["Devise", "JWT", "OAuth2"],
    },
    "laravel": {
        "name": "Laravel",
        "language": "PHP",
        "orm": ["Eloquent"],
        "database": ["PostgreSQL", "MySQL", "SQLite"],
        "auth": ["Laravel Auth", "Sanctum", "Passport"],
    },
}

MOBILE_FRAMEWORKS = {
    "react_native": {
        "name": "React Native",
        "language": "TypeScript",
        "ui": ["React Native Paper", "NativeBase", "Tamagui"],
        "navigation": ["React Navigation"],
        "state": ["Redux", "Zustand", "React Query"],
    },
    "flutter": {
        "name": "Flutter",
        "language": "Dart",
        "ui": ["Material", "Cupertino", "GetWidget"],
        "state": ["Provider", "Riverpod", "Bloc", "GetX"],
    },
    "swift": {
        "name": "SwiftUI",
        "language": "Swift",
        "ui": ["SwiftUI"],
        "state": ["@State", "@ObservedObject", "Combine"],
    },
    "kotlin": {
        "name": "Kotlin Android",
        "language": "Kotlin",
        "ui": ["Jetpack Compose", "XML Views"],
        "state": ["ViewModel", "StateFlow", "LiveData"],
    },
    "expo": {
        "name": "Expo",
        "language": "TypeScript",
        "ui": ["Expo Components", "React Native Paper"],
        "navigation": ["Expo Router", "React Navigation"],
        "state": ["Zustand", "React Query"],
    },
}

# Sample entities to use across tech stacks
SAMPLE_ENTITIES = [
    ("User", "Users", [("name", "string"), ("email", "string"), ("password", "string"), ("role", "enum:admin,user"), ("isActive", "boolean")]),
    ("Product", "Products", [("name", "string"), ("price", "decimal"), ("description", "text"), ("stock", "number"), ("category", "string")]),
    ("Order", "Orders", [("orderNumber", "string"), ("total", "decimal"), ("status", "enum:pending,completed,cancelled"), ("items", "json")]),
    ("Customer", "Customers", [("name", "string"), ("email", "string"), ("phone", "string"), ("address", "text")]),
    ("Invoice", "Invoices", [("invoiceNumber", "string"), ("amount", "decimal"), ("dueDate", "date"), ("status", "enum:draft,sent,paid")]),
    ("Employee", "Employees", [("name", "string"), ("email", "string"), ("department", "string"), ("salary", "decimal"), ("joiningDate", "date")]),
    ("Project", "Projects", [("name", "string"), ("description", "text"), ("status", "enum:planning,active,completed"), ("deadline", "date")]),
    ("Task", "Tasks", [("title", "string"), ("description", "text"), ("priority", "enum:low,medium,high"), ("status", "enum:todo,inprogress,done")]),
    ("Booking", "Bookings", [("date", "date"), ("time", "string"), ("status", "enum:pending,confirmed,cancelled"), ("notes", "text")]),
    ("Appointment", "Appointments", [("scheduledAt", "datetime"), ("duration", "number"), ("status", "enum:scheduled,completed,cancelled")]),
]


# ============================================================================
# CODE GENERATORS FOR EACH TECH STACK
# ============================================================================

def generate_react_component(entity_name: str, attrs: list, styling: str = "Tailwind CSS") -> str:
    """Generate React TypeScript component"""
    return f'''```tsx
import React, {{ useState }} from 'react';
import {{ useForm }} from 'react-hook-form';
import {{ zodResolver }} from '@hookform/resolvers/zod';
import {{ z }} from 'zod';

const {entity_name.lower()}Schema = z.object({{
{chr(10).join([f"  {a[0]}: z.string()," for a in attrs[:5]])}
}});

type {entity_name}FormData = z.infer<typeof {entity_name.lower()}Schema>;

interface {entity_name}FormProps {{
  onSubmit: (data: {entity_name}FormData) => Promise<void>;
  initialData?: Partial<{entity_name}FormData>;
}}

export default function {entity_name}Form({{ onSubmit, initialData }}: {entity_name}FormProps) {{
  const [isLoading, setIsLoading] = useState(false);
  const {{ register, handleSubmit, formState: {{ errors }} }} = useForm<{entity_name}FormData>({{
    resolver: zodResolver({entity_name.lower()}Schema),
    defaultValues: initialData,
  }});

  const handleFormSubmit = async (data: {entity_name}FormData) => {{
    setIsLoading(true);
    try {{
      await onSubmit(data);
    }} finally {{
      setIsLoading(false);
    }}
  }};

  return (
    <form onSubmit={{handleSubmit(handleFormSubmit)}} className="space-y-4">
{chr(10).join([f'''      <div>
        <label className="block text-sm font-medium mb-1">{a[0].title()}</label>
        <input {{...register("{a[0]}")}} className="w-full px-3 py-2 border rounded-lg" />
        {{errors.{a[0]} && <p className="text-red-500 text-sm">{{errors.{a[0]}.message}}</p>}}
      </div>''' for a in attrs[:5]])}
      <button type="submit" disabled={{isLoading}} className="w-full py-2 bg-blue-600 text-white rounded-lg">
        {{isLoading ? 'Saving...' : 'Save {entity_name}'}}
      </button>
    </form>
  );
}}
```'''


def generate_vue_component(entity_name: str, attrs: list) -> str:
    """Generate Vue 3 TypeScript component"""
    return f'''```vue
<script setup lang="ts">
import {{ ref, reactive }} from 'vue';
import {{ useForm }} from 'vee-validate';
import {{ toTypedSchema }} from '@vee-validate/zod';
import {{ z }} from 'zod';

const schema = toTypedSchema(z.object({{
{chr(10).join([f"  {a[0]}: z.string()," for a in attrs[:5]])}
}}));

const {{ handleSubmit, errors, defineField }} = useForm({{
  validationSchema: schema,
}});

{chr(10).join([f"const [{a[0]}, {a[0]}Attrs] = defineField('{a[0]}');" for a in attrs[:5]])}

const isLoading = ref(false);

const emit = defineEmits<{{
  submit: [{entity_name.lower()}: Record<string, any>]
}}>();

const onSubmit = handleSubmit(async (values) => {{
  isLoading.value = true;
  try {{
    emit('submit', values);
  }} finally {{
    isLoading.value = false;
  }}
}});
</script>

<template>
  <form @submit="onSubmit" class="space-y-4">
{chr(10).join([f'''    <div>
      <label class="block text-sm font-medium mb-1">{a[0].title()}</label>
      <input v-model="{a[0]}" v-bind="{a[0]}Attrs" class="w-full px-3 py-2 border rounded-lg" />
      <p v-if="errors.{a[0]}" class="text-red-500 text-sm">{{{{ errors.{a[0]} }}}}</p>
    </div>''' for a in attrs[:5]])}
    <button type="submit" :disabled="isLoading" class="w-full py-2 bg-blue-600 text-white rounded-lg">
      {{{{ isLoading ? 'Saving...' : 'Save {entity_name}' }}}}
    </button>
  </form>
</template>
```'''


def generate_angular_component(entity_name: str, attrs: list) -> str:
    """Generate Angular TypeScript component"""
    return f'''```typescript
// {entity_name.lower()}-form.component.ts
import {{ Component, EventEmitter, Input, OnInit, Output }} from '@angular/core';
import {{ FormBuilder, FormGroup, Validators }} from '@angular/forms';

interface {entity_name} {{
{chr(10).join([f"  {a[0]}: string;" for a in attrs[:5]])}
}}

@Component({{
  selector: 'app-{entity_name.lower()}-form',
  templateUrl: './{entity_name.lower()}-form.component.html',
}})
export class {entity_name}FormComponent implements OnInit {{
  @Input() initialData?: Partial<{entity_name}>;
  @Output() formSubmit = new EventEmitter<{entity_name}>();

  form!: FormGroup;
  isLoading = false;

  constructor(private fb: FormBuilder) {{}}

  ngOnInit(): void {{
    this.form = this.fb.group({{
{chr(10).join([f"      {a[0]}: [this.initialData?.{a[0]} || '', Validators.required]," for a in attrs[:5]])}
    }});
  }}

  async onSubmit(): Promise<void> {{
    if (this.form.invalid) return;

    this.isLoading = true;
    try {{
      this.formSubmit.emit(this.form.value);
    }} finally {{
      this.isLoading = false;
    }}
  }}
}}
```

```html
<!-- {entity_name.lower()}-form.component.html -->
<form [formGroup]="form" (ngSubmit)="onSubmit()" class="space-y-4">
{chr(10).join([f'''  <div>
    <label class="block text-sm font-medium mb-1">{a[0].title()}</label>
    <input formControlName="{a[0]}" class="w-full px-3 py-2 border rounded-lg" />
    <p *ngIf="form.get('{a[0]}')?.errors?.['required']" class="text-red-500 text-sm">{a[0].title()} is required</p>
  </div>''' for a in attrs[:5]])}
  <button type="submit" [disabled]="isLoading || form.invalid" class="w-full py-2 bg-blue-600 text-white rounded-lg">
    {{{{ isLoading ? 'Saving...' : 'Save {entity_name}' }}}}
  </button>
</form>
```'''


def generate_svelte_component(entity_name: str, attrs: list) -> str:
    """Generate Svelte TypeScript component"""
    return f'''```svelte
<script lang="ts">
  import {{ createEventDispatcher }} from 'svelte';
  import {{ z }} from 'zod';

  export let initialData: Partial<{entity_name}> = {{}};

  interface {entity_name} {{
{chr(10).join([f"    {a[0]}: string;" for a in attrs[:5]])}
  }}

  const schema = z.object({{
{chr(10).join([f"    {a[0]}: z.string().min(1)," for a in attrs[:5]])}
  }});

  let formData: Partial<{entity_name}> = {{ ...initialData }};
  let errors: Record<string, string> = {{}};
  let isLoading = false;

  const dispatch = createEventDispatcher<{{ submit: {entity_name} }}>();

  async function handleSubmit() {{
    const result = schema.safeParse(formData);
    if (!result.success) {{
      errors = result.error.flatten().fieldErrors as Record<string, string>;
      return;
    }}

    isLoading = true;
    try {{
      dispatch('submit', result.data as {entity_name});
    }} finally {{
      isLoading = false;
    }}
  }}
</script>

<form on:submit|preventDefault={{handleSubmit}} class="space-y-4">
{chr(10).join([f'''  <div>
    <label class="block text-sm font-medium mb-1">{a[0].title()}</label>
    <input bind:value={{formData.{a[0]}}} class="w-full px-3 py-2 border rounded-lg" />
    {{#if errors.{a[0]}}}<p class="text-red-500 text-sm">{{errors.{a[0]}}}</p>{{/if}}
  </div>''' for a in attrs[:5]])}
  <button type="submit" disabled={{isLoading}} class="w-full py-2 bg-blue-600 text-white rounded-lg">
    {{isLoading ? 'Saving...' : 'Save {entity_name}'}}
  </button>
</form>
```'''


def generate_fastapi_crud(entity_name: str, entity_plural: str, attrs: list) -> str:
    """Generate FastAPI CRUD endpoints"""
    entity_lower = entity_name.lower()
    plural_lower = entity_plural.lower()

    return f'''```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.{entity_lower} import {entity_name}
from app.schemas.{entity_lower} import {entity_name}Create, {entity_name}Update, {entity_name}Response

router = APIRouter(prefix="/{plural_lower}", tags=["{entity_plural}"])


@router.get("/", response_model=List[{entity_name}Response])
async def list_{plural_lower}(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query({entity_name})
    if search:
        query = query.filter({entity_name}.name.ilike(f"%{{search}}%"))
    return query.offset(skip).limit(limit).all()


@router.get("/{{id}}", response_model={entity_name}Response)
async def get_{entity_lower}(id: UUID, db: Session = Depends(get_db)):
    {entity_lower} = db.query({entity_name}).filter({entity_name}.id == id).first()
    if not {entity_lower}:
        raise HTTPException(status_code=404, detail="{entity_name} not found")
    return {entity_lower}


@router.post("/", response_model={entity_name}Response, status_code=status.HTTP_201_CREATED)
async def create_{entity_lower}(data: {entity_name}Create, db: Session = Depends(get_db)):
    {entity_lower} = {entity_name}(**data.model_dump())
    db.add({entity_lower})
    db.commit()
    db.refresh({entity_lower})
    return {entity_lower}


@router.put("/{{id}}", response_model={entity_name}Response)
async def update_{entity_lower}(id: UUID, data: {entity_name}Update, db: Session = Depends(get_db)):
    {entity_lower} = db.query({entity_name}).filter({entity_name}.id == id).first()
    if not {entity_lower}:
        raise HTTPException(status_code=404, detail="{entity_name} not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr({entity_lower}, field, value)
    db.commit()
    db.refresh({entity_lower})
    return {entity_lower}


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{entity_lower}(id: UUID, db: Session = Depends(get_db)):
    {entity_lower} = db.query({entity_name}).filter({entity_name}.id == id).first()
    if not {entity_lower}:
        raise HTTPException(status_code=404, detail="{entity_name} not found")
    db.delete({entity_lower})
    db.commit()
```'''


def generate_django_crud(entity_name: str, entity_plural: str, attrs: list) -> str:
    """Generate Django REST Framework views"""
    entity_lower = entity_name.lower()
    plural_lower = entity_plural.lower()

    return f'''```python
# views.py
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import {entity_name}
from .serializers import {entity_name}Serializer


class {entity_name}ViewSet(viewsets.ModelViewSet):
    queryset = {entity_name}.objects.all()
    serializer_class = {entity_name}Serializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# serializers.py
from rest_framework import serializers
from .models import {entity_name}


class {entity_name}Serializer(serializers.ModelSerializer):
    class Meta:
        model = {entity_name}
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class {entity_name}(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
{chr(10).join([f"    {a[0]} = models.{'CharField(max_length=255)' if a[1] == 'string' else 'TextField()' if a[1] == 'text' else 'DecimalField(max_digits=10, decimal_places=2)' if a[1] == 'decimal' else 'IntegerField()' if a[1] == 'number' else 'BooleanField(default=False)' if a[1] == 'boolean' else 'DateField()' if a[1] == 'date' else 'DateTimeField()' if a[1] == 'datetime' else 'JSONField(default=dict)' if a[1] == 'json' else 'CharField(max_length=50)'}" for a in attrs[:5]])}
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return getattr(self, 'name', str(self.id))


# urls.py
from rest_framework.routers import DefaultRouter
from .views import {entity_name}ViewSet

router = DefaultRouter()
router.register('{plural_lower}', {entity_name}ViewSet)

urlpatterns = router.urls
```'''


def generate_express_crud(entity_name: str, entity_plural: str, attrs: list) -> str:
    """Generate Express.js TypeScript CRUD with Prisma"""
    entity_lower = entity_name.lower()
    plural_lower = entity_plural.lower()

    return f'''```typescript
// {entity_lower}.routes.ts
import {{ Router }} from 'express';
import {{ PrismaClient }} from '@prisma/client';
import {{ z }} from 'zod';
import {{ validateRequest }} from '../middleware/validate';

const router = Router();
const prisma = new PrismaClient();

const {entity_lower}Schema = z.object({{
{chr(10).join([f"  {a[0]}: z.string()," for a in attrs[:5]])}
}});

// List all
router.get('/', async (req, res) => {{
  const {{ page = 1, limit = 20, search }} = req.query;
  const skip = (Number(page) - 1) * Number(limit);

  const where = search ? {{
    OR: [
      {{ name: {{ contains: String(search), mode: 'insensitive' }} }},
    ],
  }} : {{}};

  const [{plural_lower}, total] = await Promise.all([
    prisma.{entity_lower}.findMany({{ where, skip, take: Number(limit) }}),
    prisma.{entity_lower}.count({{ where }}),
  ]);

  res.json({{ items: {plural_lower}, total, page: Number(page), limit: Number(limit) }});
}});

// Get by ID
router.get('/:id', async (req, res) => {{
  const {entity_lower} = await prisma.{entity_lower}.findUnique({{
    where: {{ id: req.params.id }},
  }});

  if (!{entity_lower}) {{
    return res.status(404).json({{ error: '{entity_name} not found' }});
  }}

  res.json({entity_lower});
}});

// Create
router.post('/', validateRequest({entity_lower}Schema), async (req, res) => {{
  const {entity_lower} = await prisma.{entity_lower}.create({{
    data: req.body,
  }});

  res.status(201).json({entity_lower});
}});

// Update
router.put('/:id', validateRequest({entity_lower}Schema.partial()), async (req, res) => {{
  const {entity_lower} = await prisma.{entity_lower}.update({{
    where: {{ id: req.params.id }},
    data: req.body,
  }});

  res.json({entity_lower});
}});

// Delete
router.delete('/:id', async (req, res) => {{
  await prisma.{entity_lower}.delete({{
    where: {{ id: req.params.id }},
  }});

  res.status(204).send();
}});

export default router;
```

```prisma
// schema.prisma
model {entity_name} {{
  id        String   @id @default(cuid())
{chr(10).join([f"  {a[0]}    String" for a in attrs[:5]])}
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}}
```'''


def generate_nestjs_crud(entity_name: str, entity_plural: str, attrs: list) -> str:
    """Generate NestJS TypeScript CRUD"""
    entity_lower = entity_name.lower()
    plural_lower = entity_plural.lower()

    return f'''```typescript
// {entity_lower}.controller.ts
import {{ Controller, Get, Post, Put, Delete, Body, Param, Query }} from '@nestjs/common';
import {{ {entity_name}Service }} from './{entity_lower}.service';
import {{ Create{entity_name}Dto, Update{entity_name}Dto }} from './{entity_lower}.dto';

@Controller('{plural_lower}')
export class {entity_name}Controller {{
  constructor(private readonly {entity_lower}Service: {entity_name}Service) {{}}

  @Get()
  findAll(@Query('page') page = 1, @Query('limit') limit = 20) {{
    return this.{entity_lower}Service.findAll(+page, +limit);
  }}

  @Get(':id')
  findOne(@Param('id') id: string) {{
    return this.{entity_lower}Service.findOne(id);
  }}

  @Post()
  create(@Body() dto: Create{entity_name}Dto) {{
    return this.{entity_lower}Service.create(dto);
  }}

  @Put(':id')
  update(@Param('id') id: string, @Body() dto: Update{entity_name}Dto) {{
    return this.{entity_lower}Service.update(id, dto);
  }}

  @Delete(':id')
  remove(@Param('id') id: string) {{
    return this.{entity_lower}Service.remove(id);
  }}
}}


// {entity_lower}.service.ts
import {{ Injectable, NotFoundException }} from '@nestjs/common';
import {{ PrismaService }} from '../prisma/prisma.service';
import {{ Create{entity_name}Dto, Update{entity_name}Dto }} from './{entity_lower}.dto';

@Injectable()
export class {entity_name}Service {{
  constructor(private prisma: PrismaService) {{}}

  async findAll(page: number, limit: number) {{
    const skip = (page - 1) * limit;
    const [items, total] = await Promise.all([
      this.prisma.{entity_lower}.findMany({{ skip, take: limit }}),
      this.prisma.{entity_lower}.count(),
    ]);
    return {{ items, total, page, limit }};
  }}

  async findOne(id: string) {{
    const {entity_lower} = await this.prisma.{entity_lower}.findUnique({{ where: {{ id }} }});
    if (!{entity_lower}) throw new NotFoundException('{entity_name} not found');
    return {entity_lower};
  }}

  create(dto: Create{entity_name}Dto) {{
    return this.prisma.{entity_lower}.create({{ data: dto }});
  }}

  update(id: string, dto: Update{entity_name}Dto) {{
    return this.prisma.{entity_lower}.update({{ where: {{ id }}, data: dto }});
  }}

  remove(id: string) {{
    return this.prisma.{entity_lower}.delete({{ where: {{ id }} }});
  }}
}}


// {entity_lower}.dto.ts
import {{ IsString, IsOptional }} from 'class-validator';

export class Create{entity_name}Dto {{
{chr(10).join([f"  @IsString()\n  {a[0]}: string;" for a in attrs[:5]])}
}}

export class Update{entity_name}Dto {{
{chr(10).join([f"  @IsOptional()\n  @IsString()\n  {a[0]}?: string;" for a in attrs[:5]])}
}}
```'''


def generate_spring_crud(entity_name: str, entity_plural: str, attrs: list) -> str:
    """Generate Spring Boot Java CRUD"""
    entity_lower = entity_name.lower()
    plural_lower = entity_plural.lower()

    return f'''```java
// {entity_name}.java (Entity)
package com.example.app.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "{plural_lower}")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class {entity_name} {{
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

{chr(10).join([f"    private String {a[0]};" for a in attrs[:5]])}

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {{ createdAt = updatedAt = LocalDateTime.now(); }}

    @PreUpdate
    protected void onUpdate() {{ updatedAt = LocalDateTime.now(); }}
}}


// {entity_name}Controller.java
package com.example.app.controller;

import com.example.app.dto.*;
import com.example.app.service.{entity_name}Service;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;
import java.util.UUID;

@RestController
@RequestMapping("/api/{plural_lower}")
@RequiredArgsConstructor
public class {entity_name}Controller {{
    private final {entity_name}Service service;

    @GetMapping
    public Page<{entity_name}Response> findAll(Pageable pageable) {{
        return service.findAll(pageable);
    }}

    @GetMapping("/{{id}}")
    public {entity_name}Response findById(@PathVariable UUID id) {{
        return service.findById(id);
    }}

    @PostMapping
    public ResponseEntity<{entity_name}Response> create(@Valid @RequestBody {entity_name}Request request) {{
        return ResponseEntity.status(HttpStatus.CREATED).body(service.create(request));
    }}

    @PutMapping("/{{id}}")
    public {entity_name}Response update(@PathVariable UUID id, @Valid @RequestBody {entity_name}Request request) {{
        return service.update(id, request);
    }}

    @DeleteMapping("/{{id}}")
    public ResponseEntity<Void> delete(@PathVariable UUID id) {{
        service.delete(id);
        return ResponseEntity.noContent().build();
    }}
}}


// {entity_name}Service.java
package com.example.app.service;

import com.example.app.dto.*;
import com.example.app.entity.{entity_name};
import com.example.app.repository.{entity_name}Repository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.*;
import org.springframework.stereotype.Service;
import jakarta.persistence.EntityNotFoundException;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class {entity_name}Service {{
    private final {entity_name}Repository repository;

    public Page<{entity_name}Response> findAll(Pageable pageable) {{
        return repository.findAll(pageable).map(this::toResponse);
    }}

    public {entity_name}Response findById(UUID id) {{
        return toResponse(repository.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("{entity_name} not found")));
    }}

    public {entity_name}Response create({entity_name}Request request) {{
        {entity_name} entity = {entity_name}.builder()
{chr(10).join([f"            .{a[0]}(request.get{a[0][0].upper() + a[0][1:]}())" for a in attrs[:5]])}
            .build();
        return toResponse(repository.save(entity));
    }}

    public {entity_name}Response update(UUID id, {entity_name}Request request) {{
        {entity_name} entity = repository.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("{entity_name} not found"));
{chr(10).join([f"        entity.set{a[0][0].upper() + a[0][1:]}(request.get{a[0][0].upper() + a[0][1:]}());" for a in attrs[:5]])}
        return toResponse(repository.save(entity));
    }}

    public void delete(UUID id) {{
        repository.deleteById(id);
    }}

    private {entity_name}Response toResponse({entity_name} entity) {{
        return {entity_name}Response.builder()
            .id(entity.getId())
{chr(10).join([f"            .{a[0]}(entity.get{a[0][0].upper() + a[0][1:]}())" for a in attrs[:5]])}
            .build();
    }}
}}
```'''


def generate_go_crud(entity_name: str, entity_plural: str, attrs: list) -> str:
    """Generate Go (Gin) CRUD"""
    entity_lower = entity_name.lower()
    plural_lower = entity_plural.lower()

    return f'''```go
// models/{entity_lower}.go
package models

import (
    "time"
    "github.com/google/uuid"
    "gorm.io/gorm"
)

type {entity_name} struct {{
    ID        uuid.UUID      `gorm:"type:uuid;primary_key" json:"id"`
{chr(10).join([f'    {a[0][0].upper() + a[0][1:]}     string `json:"{a[0]}"`' for a in attrs[:5]])}
    CreatedAt time.Time      `json:"createdAt"`
    UpdatedAt time.Time      `json:"updatedAt"`
    DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`
}}

func (e *{entity_name}) BeforeCreate(tx *gorm.DB) error {{
    e.ID = uuid.New()
    return nil
}}


// handlers/{entity_lower}.go
package handlers

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
    "your-app/models"
    "your-app/database"
)

func Get{entity_plural}(c *gin.Context) {{
    var {plural_lower} []models.{entity_name}
    database.DB.Find(&{plural_lower})
    c.JSON(http.StatusOK, gin.H{{"items": {plural_lower}}})
}}

func Get{entity_name}(c *gin.Context) {{
    id, _ := uuid.Parse(c.Param("id"))
    var {entity_lower} models.{entity_name}
    if err := database.DB.First(&{entity_lower}, "id = ?", id).Error; err != nil {{
        c.JSON(http.StatusNotFound, gin.H{{"error": "{entity_name} not found"}})
        return
    }}
    c.JSON(http.StatusOK, {entity_lower})
}}

func Create{entity_name}(c *gin.Context) {{
    var {entity_lower} models.{entity_name}
    if err := c.ShouldBindJSON(&{entity_lower}); err != nil {{
        c.JSON(http.StatusBadRequest, gin.H{{"error": err.Error()}})
        return
    }}
    database.DB.Create(&{entity_lower})
    c.JSON(http.StatusCreated, {entity_lower})
}}

func Update{entity_name}(c *gin.Context) {{
    id, _ := uuid.Parse(c.Param("id"))
    var {entity_lower} models.{entity_name}
    if err := database.DB.First(&{entity_lower}, "id = ?", id).Error; err != nil {{
        c.JSON(http.StatusNotFound, gin.H{{"error": "{entity_name} not found"}})
        return
    }}
    if err := c.ShouldBindJSON(&{entity_lower}); err != nil {{
        c.JSON(http.StatusBadRequest, gin.H{{"error": err.Error()}})
        return
    }}
    database.DB.Save(&{entity_lower})
    c.JSON(http.StatusOK, {entity_lower})
}}

func Delete{entity_name}(c *gin.Context) {{
    id, _ := uuid.Parse(c.Param("id"))
    database.DB.Delete(&models.{entity_name}{{}}, "id = ?", id)
    c.Status(http.StatusNoContent)
}}


// routes.go
func SetupRoutes(r *gin.Engine) {{
    api := r.Group("/api")
    {{
        api.GET("/{plural_lower}", handlers.Get{entity_plural})
        api.GET("/{plural_lower}/:id", handlers.Get{entity_name})
        api.POST("/{plural_lower}", handlers.Create{entity_name})
        api.PUT("/{plural_lower}/:id", handlers.Update{entity_name})
        api.DELETE("/{plural_lower}/:id", handlers.Delete{entity_name})
    }}
}}
```'''


def generate_dotnet_crud(entity_name: str, entity_plural: str, attrs: list) -> str:
    """Generate .NET Core C# CRUD"""
    entity_lower = entity_name.lower()
    plural_lower = entity_plural.lower()

    return f'''```csharp
// Models/{entity_name}.cs
using System;
using System.ComponentModel.DataAnnotations;

namespace App.Models;

public class {entity_name}
{{
    public Guid Id {{ get; set; }}
{chr(10).join([f"    [Required]\n    public string {a[0][0].upper() + a[0][1:]} {{ get; set; }} = string.Empty;" for a in attrs[:5]])}
    public DateTime CreatedAt {{ get; set; }}
    public DateTime UpdatedAt {{ get; set; }}
}}


// Controllers/{entity_plural}Controller.cs
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using App.Data;
using App.Models;

namespace App.Controllers;

[ApiController]
[Route("api/{plural_lower}")]
public class {entity_plural}Controller : ControllerBase
{{
    private readonly AppDbContext _context;

    public {entity_plural}Controller(AppDbContext context)
    {{
        _context = context;
    }}

    [HttpGet]
    public async Task<ActionResult<IEnumerable<{entity_name}>>> GetAll()
    {{
        return await _context.{entity_plural}.ToListAsync();
    }}

    [HttpGet("{{id}}")]
    public async Task<ActionResult<{entity_name}>> GetById(Guid id)
    {{
        var {entity_lower} = await _context.{entity_plural}.FindAsync(id);
        if ({entity_lower} == null) return NotFound();
        return {entity_lower};
    }}

    [HttpPost]
    public async Task<ActionResult<{entity_name}>> Create({entity_name} {entity_lower})
    {{
        {entity_lower}.Id = Guid.NewGuid();
        {entity_lower}.CreatedAt = DateTime.UtcNow;
        {entity_lower}.UpdatedAt = DateTime.UtcNow;

        _context.{entity_plural}.Add({entity_lower});
        await _context.SaveChangesAsync();

        return CreatedAtAction(nameof(GetById), new {{ id = {entity_lower}.Id }}, {entity_lower});
    }}

    [HttpPut("{{id}}")]
    public async Task<IActionResult> Update(Guid id, {entity_name} {entity_lower})
    {{
        if (id != {entity_lower}.Id) return BadRequest();

        {entity_lower}.UpdatedAt = DateTime.UtcNow;
        _context.Entry({entity_lower}).State = EntityState.Modified;

        try
        {{
            await _context.SaveChangesAsync();
        }}
        catch (DbUpdateConcurrencyException)
        {{
            if (!await _context.{entity_plural}.AnyAsync(e => e.Id == id))
                return NotFound();
            throw;
        }}

        return NoContent();
    }}

    [HttpDelete("{{id}}")]
    public async Task<IActionResult> Delete(Guid id)
    {{
        var {entity_lower} = await _context.{entity_plural}.FindAsync(id);
        if ({entity_lower} == null) return NotFound();

        _context.{entity_plural}.Remove({entity_lower});
        await _context.SaveChangesAsync();

        return NoContent();
    }}
}}
```'''


def generate_flutter_screen(entity_name: str, attrs: list) -> str:
    """Generate Flutter Dart screen"""
    entity_lower = entity_name.lower()

    return f'''```dart
// lib/screens/{entity_lower}_form_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/{entity_lower}_provider.dart';
import '../models/{entity_lower}.dart';

class {entity_name}FormScreen extends StatefulWidget {{
  final {entity_name}? {entity_lower};

  const {entity_name}FormScreen({{Key? key, this.{entity_lower}}}) : super(key: key);

  @override
  State<{entity_name}FormScreen> createState() => _{entity_name}FormScreenState();
}}

class _{entity_name}FormScreenState extends State<{entity_name}FormScreen> {{
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

{chr(10).join([f"  late TextEditingController _{a[0]}Controller;" for a in attrs[:5]])}

  @override
  void initState() {{
    super.initState();
{chr(10).join([f"    _{a[0]}Controller = TextEditingController(text: widget.{entity_lower}?.{a[0]} ?? '');" for a in attrs[:5]])}
  }}

  @override
  void dispose() {{
{chr(10).join([f"    _{a[0]}Controller.dispose();" for a in attrs[:5]])}
    super.dispose();
  }}

  Future<void> _submit() async {{
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {{
      final provider = Provider.of<{entity_name}Provider>(context, listen: false);
      final data = {entity_name}(
{chr(10).join([f"        {a[0]}: _{a[0]}Controller.text," for a in attrs[:5]])}
      );

      if (widget.{entity_lower} != null) {{
        await provider.update(widget.{entity_lower}!.id, data);
      }} else {{
        await provider.create(data);
      }}

      Navigator.pop(context);
    }} catch (e) {{
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }} finally {{
      setState(() => _isLoading = false);
    }}
  }}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.{entity_lower} != null ? 'Edit {entity_name}' : 'Create {entity_name}'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
{chr(10).join([f'''            TextFormField(
              controller: _{a[0]}Controller,
              decoration: const InputDecoration(labelText: '{a[0].title()}'),
              validator: (v) => v?.isEmpty ?? true ? '{a[0].title()} is required' : null,
            ),
            const SizedBox(height: 16),''' for a in attrs[:5]])}
            ElevatedButton(
              onPressed: _isLoading ? null : _submit,
              child: _isLoading
                  ? const CircularProgressIndicator()
                  : Text(widget.{entity_lower} != null ? 'Update' : 'Create'),
            ),
          ],
        ),
      ),
    );
  }}
}}
```'''


def generate_react_native_screen(entity_name: str, attrs: list) -> str:
    """Generate React Native TypeScript screen"""
    entity_lower = entity_name.lower()

    return f'''```tsx
// screens/{entity_name}Form.tsx
import React, {{ useState }} from 'react';
import {{ View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator }} from 'react-native';
import {{ useForm, Controller }} from 'react-hook-form';
import {{ zodResolver }} from '@hookform/resolvers/zod';
import {{ z }} from 'zod';

const schema = z.object({{
{chr(10).join([f"  {a[0]}: z.string().min(1, '{a[0].title()} is required')," for a in attrs[:5]])}
}});

type FormData = z.infer<typeof schema>;

interface Props {{
  initialData?: Partial<FormData>;
  onSubmit: (data: FormData) => Promise<void>;
}}

export default function {entity_name}Form({{ initialData, onSubmit }}: Props) {{
  const [isLoading, setIsLoading] = useState(false);

  const {{ control, handleSubmit, formState: {{ errors }} }} = useForm<FormData>({{
    resolver: zodResolver(schema),
    defaultValues: initialData,
  }});

  const handleFormSubmit = async (data: FormData) => {{
    setIsLoading(true);
    try {{
      await onSubmit(data);
    }} finally {{
      setIsLoading(false);
    }}
  }};

  return (
    <View style={{styles.container}}>
{chr(10).join([f'''      <View style={{styles.field}}>
        <Text style={{styles.label}}>{a[0].title()}</Text>
        <Controller
          control={{control}}
          name="{a[0]}"
          render={{({{ field: {{ onChange, value }} }}) => (
            <TextInput
              style={{styles.input}}
              value={{value}}
              onChangeText={{onChange}}
              placeholder="Enter {a[0]}"
            />
          )}}
        />
        {{errors.{a[0]} && <Text style={{styles.error}}>{{errors.{a[0]}.message}}</Text>}}
      </View>''' for a in attrs[:5]])}

      <TouchableOpacity
        style={{[styles.button, isLoading && styles.buttonDisabled]}}
        onPress={{handleSubmit(handleFormSubmit)}}
        disabled={{isLoading}}
      >
        {{isLoading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={{styles.buttonText}}>Save {entity_name}</Text>
        )}}
      </TouchableOpacity>
    </View>
  );
}}

const styles = StyleSheet.create({{
  container: {{ padding: 16 }},
  field: {{ marginBottom: 16 }},
  label: {{ fontSize: 14, fontWeight: '600', marginBottom: 4 }},
  input: {{ borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, fontSize: 16 }},
  error: {{ color: 'red', fontSize: 12, marginTop: 4 }},
  button: {{ backgroundColor: '#3b82f6', padding: 16, borderRadius: 8, alignItems: 'center' }},
  buttonDisabled: {{ opacity: 0.5 }},
  buttonText: {{ color: '#fff', fontSize: 16, fontWeight: '600' }},
}});
```'''


# ============================================================================
# SAMPLE GENERATION
# ============================================================================

def generate_all_tech_samples() -> List[Dict]:
    """Generate samples for all tech stack combinations"""
    samples = []

    for entity_name, entity_plural, attrs in SAMPLE_ENTITIES:
        # Frontend Frameworks
        for fw_key, fw_config in FRONTEND_FRAMEWORKS.items():
            # Form component
            if fw_key == "react" or fw_key == "nextjs":
                code = generate_react_component(entity_name, attrs)
            elif fw_key == "vue" or fw_key == "nuxt":
                code = generate_vue_component(entity_name, attrs)
            elif fw_key == "angular":
                code = generate_angular_component(entity_name, attrs)
            elif fw_key == "svelte":
                code = generate_svelte_component(entity_name, attrs)
            else:
                continue

            samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert {fw_config['name']} developer using {fw_config['language']}."},
                    {"role": "user", "content": f"Create a {entity_name} form component using {fw_config['name']} with TypeScript and form validation"},
                    {"role": "assistant", "content": code}
                ]
            })

        # Backend Frameworks
        for fw_key, fw_config in BACKEND_FRAMEWORKS.items():
            if fw_key == "fastapi":
                code = generate_fastapi_crud(entity_name, entity_plural, attrs)
            elif fw_key == "django":
                code = generate_django_crud(entity_name, entity_plural, attrs)
            elif fw_key == "express":
                code = generate_express_crud(entity_name, entity_plural, attrs)
            elif fw_key == "nestjs":
                code = generate_nestjs_crud(entity_name, entity_plural, attrs)
            elif fw_key == "spring":
                code = generate_spring_crud(entity_name, entity_plural, attrs)
            elif fw_key == "go":
                code = generate_go_crud(entity_name, entity_plural, attrs)
            elif fw_key == "dotnet":
                code = generate_dotnet_crud(entity_name, entity_plural, attrs)
            else:
                continue

            orm = random.choice(fw_config["orm"])
            db = random.choice(fw_config["database"])

            samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert {fw_config['name']} developer using {fw_config['language']}."},
                    {"role": "user", "content": f"Create {entity_name} CRUD API endpoints using {fw_config['name']} with {orm} and {db}"},
                    {"role": "assistant", "content": code}
                ]
            })

        # Mobile Frameworks
        for fw_key, fw_config in MOBILE_FRAMEWORKS.items():
            if fw_key == "flutter":
                code = generate_flutter_screen(entity_name, attrs)
            elif fw_key in ["react_native", "expo"]:
                code = generate_react_native_screen(entity_name, attrs)
            else:
                continue

            samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert {fw_config['name']} developer using {fw_config['language']}."},
                    {"role": "user", "content": f"Create a {entity_name} form screen using {fw_config['name']}"},
                    {"role": "assistant", "content": code}
                ]
            })

    return samples


def generate_cross_tech_samples() -> List[Dict]:
    """Generate samples that mix different technology combinations"""
    samples = []

    prompts = [
        ("Build a full-stack {entity} management feature with {frontend} frontend and {backend} backend", "fullstack"),
        ("Create {entity} CRUD operations using {backend} with {database} database", "backend"),
        ("Implement {entity} form with validation using {frontend} and {styling}", "frontend"),
        ("Set up {entity} API with {backend}, {orm}, and {auth} authentication", "api"),
    ]

    for entity_name, entity_plural, attrs in SAMPLE_ENTITIES[:5]:  # Use fewer entities for cross-tech
        for prompt_template, category in prompts:
            # Pick random technologies
            frontend = random.choice(list(FRONTEND_FRAMEWORKS.values()))
            backend = random.choice(list(BACKEND_FRAMEWORKS.values()))

            prompt = prompt_template.format(
                entity=entity_name,
                frontend=frontend["name"],
                backend=backend["name"],
                database=random.choice(backend["database"]),
                orm=random.choice(backend["orm"]),
                auth=random.choice(backend["auth"]),
                styling=random.choice(frontend["styling"]),
            )

            # Generate appropriate code based on category
            if category == "frontend":
                code = generate_react_component(entity_name, attrs)
            elif category == "backend" or category == "api":
                code = generate_fastapi_crud(entity_name, entity_plural, attrs)
            else:
                # Full-stack: combine both
                frontend_code = generate_react_component(entity_name, attrs)
                backend_code = generate_fastapi_crud(entity_name, entity_plural, attrs)
                code = f"## Frontend\n{frontend_code}\n\n## Backend\n{backend_code}"

            samples.append({
                "messages": [
                    {"role": "system", "content": "You are an expert full-stack developer proficient in multiple technologies."},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": code}
                ]
            })

    return samples


def save_tech_stack_samples(output_dir: str = "./data/tech_stacks"):
    """Save all tech stack samples"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("Generating tech stack samples...")

    # Generate all samples
    tech_samples = generate_all_tech_samples()
    print(f"  Generated {len(tech_samples)} single-tech samples")

    cross_samples = generate_cross_tech_samples()
    print(f"  Generated {len(cross_samples)} cross-tech samples")

    all_samples = tech_samples + cross_samples

    # Save to file
    output_file = Path(output_dir) / "all_tech_stacks.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print("TECHNOLOGY COVERAGE SUMMARY")
    print(f"{'='*60}")
    print(f"\nFrontend Frameworks ({len(FRONTEND_FRAMEWORKS)}):")
    for fw in FRONTEND_FRAMEWORKS.values():
        print(f"  - {fw['name']} ({fw['language']})")

    print(f"\nBackend Frameworks ({len(BACKEND_FRAMEWORKS)}):")
    for fw in BACKEND_FRAMEWORKS.values():
        print(f"  - {fw['name']} ({fw['language']})")

    print(f"\nMobile Frameworks ({len(MOBILE_FRAMEWORKS)}):")
    for fw in MOBILE_FRAMEWORKS.values():
        print(f"  - {fw['name']} ({fw['language']})")

    print(f"\nTotal samples: {len(all_samples)}")
    print(f"Saved to: {output_file}")

    return all_samples


if __name__ == "__main__":
    save_tech_stack_samples()
