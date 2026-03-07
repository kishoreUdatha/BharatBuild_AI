"""
Generate Multi-File Project Examples for ALL 20 Frameworks

Frontend (6): React, Vue, Angular, Svelte, Next.js, Nuxt
Backend (9): FastAPI, Django, Flask, Express, NestJS, Spring Boot, .NET, Go, Rails, Laravel
Mobile (5): Flutter, React Native, Swift, Kotlin, Expo

Each framework gets complete project templates with:
- Full folder structure
- All necessary files
- Configuration files
- Docker setup
"""

import json
import random
from pathlib import Path
from typing import List, Dict


# ============================================================================
# PROJECT DOMAINS
# ============================================================================

DOMAINS = [
    ("ecommerce", "E-Commerce Platform", ["Product", "Category", "Cart", "Order", "User"]),
    ("blog", "Blog Platform", ["Post", "Category", "Comment", "Author", "Tag"]),
    ("task", "Task Management", ["Project", "Task", "User", "Team", "Comment"]),
    ("crm", "CRM System", ["Contact", "Company", "Deal", "Activity", "User"]),
    ("booking", "Booking System", ["Service", "Booking", "Customer", "Provider", "Payment"]),
    ("inventory", "Inventory System", ["Product", "Warehouse", "Stock", "Supplier", "Order"]),
    ("social", "Social Network", ["User", "Post", "Comment", "Like", "Follow"]),
    ("lms", "Learning Platform", ["Course", "Lesson", "Quiz", "Student", "Instructor"]),
]


# ============================================================================
# FRAMEWORK TEMPLATES
# ============================================================================

def generate_vue_project(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate Vue.js + Pinia project"""
    primary = entities[0]
    return f'''I'll create a complete {domain_name} with Vue 3, TypeScript, Pinia, and Tailwind CSS.

## Project Structure

```
{domain}-vue/
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   ├── auth.ts
│   │   └── {primary.lower()}.ts
│   ├── views/
│   │   ├── HomeView.vue
│   │   ├── LoginView.vue
│   │   ├── DashboardView.vue
│   │   └── {primary}View.vue
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppNavbar.vue
│   │   │   ├── AppSidebar.vue
│   │   │   └── AppFooter.vue
│   │   ├── ui/
│   │   │   ├── BaseButton.vue
│   │   │   ├── BaseInput.vue
│   │   │   ├── BaseModal.vue
│   │   │   └── BaseTable.vue
│   │   └── {primary.lower()}/
│   │       ├── {primary}List.vue
│   │       ├── {primary}Form.vue
│   │       └── {primary}Card.vue
│   ├── composables/
│   │   ├── useAuth.ts
│   │   └── use{primary}.ts
│   ├── services/
│   │   └── api.ts
│   └── types/
│       └── index.ts
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Key Files

### src/stores/{primary.lower()}.ts
```typescript
import {{ defineStore }} from 'pinia'
import {{ ref, computed }} from 'vue'
import api from '@/services/api'

interface {primary} {{
  id: string
  name: string
  description: string
  status: 'active' | 'inactive'
  createdAt: string
}}

export const use{primary}Store = defineStore('{primary.lower()}', () => {{
  const items = ref<{primary}[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeItems = computed(() =>
    items.value.filter(item => item.status === 'active')
  )

  async function fetchAll() {{
    loading.value = true
    try {{
      const response = await api.get('/{primary.lower()}s')
      items.value = response.data
    }} catch (e) {{
      error.value = 'Failed to fetch {primary.lower()}s'
    }} finally {{
      loading.value = false
    }}
  }}

  async function create(data: Partial<{primary}>) {{
    const response = await api.post('/{primary.lower()}s', data)
    items.value.push(response.data)
    return response.data
  }}

  async function update(id: string, data: Partial<{primary}>) {{
    const response = await api.put(`/{primary.lower()}s/${{id}}`, data)
    const index = items.value.findIndex(item => item.id === id)
    if (index !== -1) items.value[index] = response.data
    return response.data
  }}

  async function remove(id: string) {{
    await api.delete(`/{primary.lower()}s/${{id}}`)
    items.value = items.value.filter(item => item.id !== id)
  }}

  return {{ items, loading, error, activeItems, fetchAll, create, update, remove }}
}})
```

### src/components/{primary.lower()}/{primary}List.vue
```vue
<script setup lang="ts">
import {{ ref, onMounted }} from 'vue'
import {{ use{primary}Store }} from '@/stores/{primary.lower()}'
import {primary}Card from './{primary}Card.vue'
import {primary}Form from './{primary}Form.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const store = use{primary}Store()
const showCreateModal = ref(false)

onMounted(() => {{
  store.fetchAll()
}})

async function handleCreate(data: any) {{
  await store.create(data)
  showCreateModal.value = false
}}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">{primary}s</h1>
      <BaseButton @click="showCreateModal = true">
        Add {primary}
      </BaseButton>
    </div>

    <div v-if="store.loading" class="flex justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <{primary}Card
        v-for="item in store.items"
        :key="item.id"
        :{primary.lower()}="item"
        @delete="store.remove(item.id)"
      />
    </div>

    <BaseModal v-model="showCreateModal" title="Create {primary}">
      <{primary}Form @submit="handleCreate" @cancel="showCreateModal = false" />
    </BaseModal>
  </div>
</template>
```

### src/services/api.ts
```typescript
import axios from 'axios'

const api = axios.create({{
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {{
    'Content-Type': 'application/json',
  }},
}})

api.interceptors.request.use((config) => {{
  const token = localStorage.getItem('token')
  if (token) {{
    config.headers.Authorization = `Bearer ${{token}}`
  }}
  return config
}})

api.interceptors.response.use(
  (response) => response,
  (error) => {{
    if (error.response?.status === 401) {{
      localStorage.removeItem('token')
      window.location.href = '/login'
    }}
    return Promise.reject(error)
  }}
)

export default api
```

### package.json
```json
{{
  "name": "{domain}-vue",
  "version": "1.0.0",
  "scripts": {{
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0"
  }},
  "devDependencies": {{
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }}
}}
```

This Vue 3 project includes Composition API, Pinia for state management, TypeScript, and Tailwind CSS.
'''


def generate_angular_project(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate Angular project"""
    primary = entities[0]
    return f'''I'll create a complete {domain_name} with Angular 17, TypeScript, NgRx, and Angular Material.

## Project Structure

```
{domain}-angular/
├── src/
│   ├── app/
│   │   ├── app.component.ts
│   │   ├── app.config.ts
│   │   ├── app.routes.ts
│   │   ├── core/
│   │   │   ├── services/
│   │   │   │   ├── api.service.ts
│   │   │   │   └── auth.service.ts
│   │   │   ├── guards/
│   │   │   │   └── auth.guard.ts
│   │   │   └── interceptors/
│   │   │       └── auth.interceptor.ts
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   │   ├── login/
│   │   │   │   │   └── login.component.ts
│   │   │   │   └── register/
│   │   │   │       └── register.component.ts
│   │   │   ├── dashboard/
│   │   │   │   └── dashboard.component.ts
│   │   │   └── {primary.lower()}/
│   │   │       ├── {primary.lower()}-list/
│   │   │       │   └── {primary.lower()}-list.component.ts
│   │   │       ├── {primary.lower()}-form/
│   │   │       │   └── {primary.lower()}-form.component.ts
│   │   │       └── {primary.lower()}.service.ts
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   │   ├── navbar/
│   │   │   │   ├── sidebar/
│   │   │   │   └── data-table/
│   │   │   └── models/
│   │   │       └── {primary.lower()}.model.ts
│   │   └── store/
│   │       ├── {primary.lower()}/
│   │       │   ├── {primary.lower()}.actions.ts
│   │       │   ├── {primary.lower()}.reducer.ts
│   │       │   ├── {primary.lower()}.effects.ts
│   │       │   └── {primary.lower()}.selectors.ts
│   │       └── index.ts
│   ├── main.ts
│   └── styles.scss
├── angular.json
├── package.json
└── tsconfig.json
```

## Key Files

### src/app/features/{primary.lower()}/{primary.lower()}.service.ts
```typescript
import {{ Injectable, inject }} from '@angular/core';
import {{ HttpClient }} from '@angular/common/http';
import {{ Observable }} from 'rxjs';
import {{ {primary} }} from '../../shared/models/{primary.lower()}.model';
import {{ environment }} from '../../../environments/environment';

@Injectable({{
  providedIn: 'root'
}})
export class {primary}Service {{
  private http = inject(HttpClient);
  private apiUrl = `${{environment.apiUrl}}/{primary.lower()}s`;

  getAll(): Observable<{primary}[]> {{
    return this.http.get<{primary}[]>(this.apiUrl);
  }}

  getById(id: string): Observable<{primary}> {{
    return this.http.get<{primary}>(`${{this.apiUrl}}/${{id}}`);
  }}

  create(data: Partial<{primary}>): Observable<{primary}> {{
    return this.http.post<{primary}>(this.apiUrl, data);
  }}

  update(id: string, data: Partial<{primary}>): Observable<{primary}> {{
    return this.http.put<{primary}>(`${{this.apiUrl}}/${{id}}`, data);
  }}

  delete(id: string): Observable<void> {{
    return this.http.delete<void>(`${{this.apiUrl}}/${{id}}`);
  }}
}}
```

### src/app/store/{primary.lower()}/{primary.lower()}.effects.ts
```typescript
import {{ Injectable, inject }} from '@angular/core';
import {{ Actions, createEffect, ofType }} from '@ngrx/effects';
import {{ {primary}Service }} from '../../features/{primary.lower()}/{primary.lower()}.service';
import * as {primary}Actions from './{primary.lower()}.actions';
import {{ catchError, map, mergeMap, of }} from 'rxjs';

@Injectable()
export class {primary}Effects {{
  private actions$ = inject(Actions);
  private {primary.lower()}Service = inject({primary}Service);

  load{primary}s$ = createEffect(() =>
    this.actions$.pipe(
      ofType({primary}Actions.load{primary}s),
      mergeMap(() =>
        this.{primary.lower()}Service.getAll().pipe(
          map({primary.lower()}s => {primary}Actions.load{primary}sSuccess({{ {primary.lower()}s }})),
          catchError(error => of({primary}Actions.load{primary}sFailure({{ error: error.message }})))
        )
      )
    )
  );

  create{primary}$ = createEffect(() =>
    this.actions$.pipe(
      ofType({primary}Actions.create{primary}),
      mergeMap(({{ {primary.lower()} }}) =>
        this.{primary.lower()}Service.create({primary.lower()}).pipe(
          map({primary.lower()} => {primary}Actions.create{primary}Success({{ {primary.lower()} }})),
          catchError(error => of({primary}Actions.create{primary}Failure({{ error: error.message }})))
        )
      )
    )
  );
}}
```

### src/app/features/{primary.lower()}/{primary.lower()}-list/{primary.lower()}-list.component.ts
```typescript
import {{ Component, inject, OnInit }} from '@angular/core';
import {{ CommonModule }} from '@angular/common';
import {{ Store }} from '@ngrx/store';
import {{ MatTableModule }} from '@angular/material/table';
import {{ MatButtonModule }} from '@angular/material/button';
import {{ MatIconModule }} from '@angular/material/icon';
import {{ MatDialog, MatDialogModule }} from '@angular/material/dialog';
import {{ select{primary}s, selectLoading }} from '../../../store/{primary.lower()}/{primary.lower()}.selectors';
import * as {primary}Actions from '../../../store/{primary.lower()}/{primary.lower()}.actions';
import {{ {primary}FormComponent }} from '../{primary.lower()}-form/{primary.lower()}-form.component';

@Component({{
  selector: 'app-{primary.lower()}-list',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule, MatDialogModule],
  template: `
    <div class="container mx-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">{primary}s</h1>
        <button mat-raised-button color="primary" (click)="openCreateDialog()">
          <mat-icon>add</mat-icon> Add {primary}
        </button>
      </div>

      <mat-table [dataSource]="{primary.lower()}s()" class="w-full">
        <ng-container matColumnDef="name">
          <mat-header-cell *matHeaderCellDef>Name</mat-header-cell>
          <mat-cell *matCellDef="let item">{{{{ item.name }}}}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="status">
          <mat-header-cell *matHeaderCellDef>Status</mat-header-cell>
          <mat-cell *matCellDef="let item">{{{{ item.status }}}}</mat-cell>
        </ng-container>

        <ng-container matColumnDef="actions">
          <mat-header-cell *matHeaderCellDef>Actions</mat-header-cell>
          <mat-cell *matCellDef="let item">
            <button mat-icon-button (click)="edit(item)">
              <mat-icon>edit</mat-icon>
            </button>
            <button mat-icon-button color="warn" (click)="delete(item.id)">
              <mat-icon>delete</mat-icon>
            </button>
          </mat-cell>
        </ng-container>

        <mat-header-row *matHeaderRowDef="displayedColumns"></mat-header-row>
        <mat-row *matRowDef="let row; columns: displayedColumns"></mat-row>
      </mat-table>
    </div>
  `
}})
export class {primary}ListComponent implements OnInit {{
  private store = inject(Store);
  private dialog = inject(MatDialog);

  {primary.lower()}s = this.store.selectSignal(select{primary}s);
  loading = this.store.selectSignal(selectLoading);
  displayedColumns = ['name', 'status', 'actions'];

  ngOnInit() {{
    this.store.dispatch({primary}Actions.load{primary}s());
  }}

  openCreateDialog() {{
    this.dialog.open({primary}FormComponent);
  }}

  edit(item: any) {{
    this.dialog.open({primary}FormComponent, {{ data: item }});
  }}

  delete(id: string) {{
    this.store.dispatch({primary}Actions.delete{primary}({{ id }}));
  }}
}}
```

This Angular 17 project uses standalone components, signals, NgRx for state management, and Angular Material.
'''


def generate_flutter_project(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate Flutter mobile app"""
    primary = entities[0]
    return f'''I'll create a complete {domain_name} mobile app with Flutter, Riverpod, and clean architecture.

## Project Structure

```
{domain}_app/
├── lib/
│   ├── main.dart
│   ├── app/
│   │   ├── app.dart
│   │   ├── routes.dart
│   │   └── theme.dart
│   ├── core/
│   │   ├── constants/
│   │   │   └── api_constants.dart
│   │   ├── errors/
│   │   │   └── failures.dart
│   │   ├── network/
│   │   │   └── api_client.dart
│   │   └── utils/
│   │       └── validators.dart
│   ├── features/
│   │   ├── auth/
│   │   │   ├── data/
│   │   │   │   ├── datasources/
│   │   │   │   ├── models/
│   │   │   │   └── repositories/
│   │   │   ├── domain/
│   │   │   │   ├── entities/
│   │   │   │   ├── repositories/
│   │   │   │   └── usecases/
│   │   │   └── presentation/
│   │   │       ├── providers/
│   │   │       ├── screens/
│   │   │       └── widgets/
│   │   └── {primary.lower()}/
│   │       ├── data/
│   │       │   ├── datasources/
│   │       │   │   └── {primary.lower()}_remote_datasource.dart
│   │       │   ├── models/
│   │       │   │   └── {primary.lower()}_model.dart
│   │       │   └── repositories/
│   │       │       └── {primary.lower()}_repository_impl.dart
│   │       ├── domain/
│   │       │   ├── entities/
│   │       │   │   └── {primary.lower()}.dart
│   │       │   ├── repositories/
│   │       │   │   └── {primary.lower()}_repository.dart
│   │       │   └── usecases/
│   │       │       ├── get_{primary.lower()}s.dart
│   │       │       └── create_{primary.lower()}.dart
│   │       └── presentation/
│   │           ├── providers/
│   │           │   └── {primary.lower()}_provider.dart
│   │           ├── screens/
│   │           │   ├── {primary.lower()}_list_screen.dart
│   │           │   └── {primary.lower()}_detail_screen.dart
│   │           └── widgets/
│   │               └── {primary.lower()}_card.dart
│   └── shared/
│       └── widgets/
│           ├── app_button.dart
│           └── app_text_field.dart
├── pubspec.yaml
└── analysis_options.yaml
```

## Key Files

### lib/features/{primary.lower()}/domain/entities/{primary.lower()}.dart
```dart
import 'package:equatable/equatable.dart';

class {primary} extends Equatable {{
  final String id;
  final String name;
  final String description;
  final String status;
  final DateTime createdAt;

  const {primary}({{
    required this.id,
    required this.name,
    required this.description,
    required this.status,
    required this.createdAt,
  }});

  @override
  List<Object?> get props => [id, name, description, status, createdAt];
}}
```

### lib/features/{primary.lower()}/data/models/{primary.lower()}_model.dart
```dart
import '../../domain/entities/{primary.lower()}.dart';

class {primary}Model extends {primary} {{
  const {primary}Model({{
    required super.id,
    required super.name,
    required super.description,
    required super.status,
    required super.createdAt,
  }});

  factory {primary}Model.fromJson(Map<String, dynamic> json) {{
    return {primary}Model(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String? ?? '',
      status: json['status'] as String? ?? 'active',
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }}

  Map<String, dynamic> toJson() {{
    return {{
      'id': id,
      'name': name,
      'description': description,
      'status': status,
      'created_at': createdAt.toIso8601String(),
    }};
  }}
}}
```

### lib/features/{primary.lower()}/presentation/providers/{primary.lower()}_provider.dart
```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/entities/{primary.lower()}.dart';
import '../../domain/usecases/get_{primary.lower()}s.dart';
import '../../domain/usecases/create_{primary.lower()}.dart';

final {primary.lower()}sProvider = StateNotifierProvider<{primary}Notifier, AsyncValue<List<{primary}>>>((ref) {{
  return {primary}Notifier(ref);
}});

class {primary}Notifier extends StateNotifier<AsyncValue<List<{primary}>>> {{
  final Ref _ref;

  {primary}Notifier(this._ref) : super(const AsyncValue.loading()) {{
    load{primary}s();
  }}

  Future<void> load{primary}s() async {{
    state = const AsyncValue.loading();
    try {{
      final get{primary}s = _ref.read(get{primary}sUseCaseProvider);
      final {primary.lower()}s = await get{primary}s();
      state = AsyncValue.data({primary.lower()}s);
    }} catch (e, st) {{
      state = AsyncValue.error(e, st);
    }}
  }}

  Future<void> create{primary}(String name, String description) async {{
    try {{
      final create{primary} = _ref.read(create{primary}UseCaseProvider);
      final new{primary} = await create{primary}(name, description);
      state = AsyncValue.data([...state.value ?? [], new{primary}]);
    }} catch (e) {{
      rethrow;
    }}
  }}
}}
```

### lib/features/{primary.lower()}/presentation/screens/{primary.lower()}_list_screen.dart
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/{primary.lower()}_provider.dart';
import '../widgets/{primary.lower()}_card.dart';

class {primary}ListScreen extends ConsumerWidget {{
  const {primary}ListScreen({{super.key}});

  @override
  Widget build(BuildContext context, WidgetRef ref) {{
    final {primary.lower()}sAsync = ref.watch({primary.lower()}sProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('{primary}s'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read({primary.lower()}sProvider.notifier).load{primary}s(),
          ),
        ],
      ),
      body: {primary.lower()}sAsync.when(
        data: ({primary.lower()}s) => {primary.lower()}s.isEmpty
            ? const Center(child: Text('No {primary.lower()}s found'))
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: {primary.lower()}s.length,
                itemBuilder: (context, index) {{
                  return {primary}Card({primary.lower()}: {primary.lower()}s[index]);
                }},
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Error: $error'),
              ElevatedButton(
                onPressed: () => ref.read({primary.lower()}sProvider.notifier).load{primary}s(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context, ref),
        child: const Icon(Icons.add),
      ),
    );
  }}

  void _showCreateDialog(BuildContext context, WidgetRef ref) {{
    showDialog(
      context: context,
      builder: (context) => const Create{primary}Dialog(),
    );
  }}
}}
```

### pubspec.yaml
```yaml
name: {domain}_app
description: {domain_name} Mobile App
version: 1.0.0

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.4.0
  dio: ^5.4.0
  equatable: ^2.0.5
  go_router: ^13.0.0
  flutter_secure_storage: ^9.0.0
  intl: ^0.18.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
  mocktail: ^1.0.0

flutter:
  uses-material-design: true
```

This Flutter app uses clean architecture with Riverpod for state management.
'''


def generate_spring_boot_project(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate Spring Boot project"""
    primary = entities[0]
    return f'''I'll create a complete {domain_name} with Spring Boot 3, JPA, and PostgreSQL.

## Project Structure

```
{domain}-spring/
├── src/
│   ├── main/
│   │   ├── java/com/example/{domain}/
│   │   │   ├── Application.java
│   │   │   ├── config/
│   │   │   │   ├── SecurityConfig.java
│   │   │   │   ├── JwtConfig.java
│   │   │   │   └── CorsConfig.java
│   │   │   ├── controller/
│   │   │   │   ├── AuthController.java
│   │   │   │   └── {primary}Controller.java
│   │   │   ├── service/
│   │   │   │   ├── AuthService.java
│   │   │   │   └── {primary}Service.java
│   │   │   ├── repository/
│   │   │   │   ├── UserRepository.java
│   │   │   │   └── {primary}Repository.java
│   │   │   ├── model/
│   │   │   │   ├── User.java
│   │   │   │   └── {primary}.java
│   │   │   ├── dto/
│   │   │   │   ├── {primary}Request.java
│   │   │   │   └── {primary}Response.java
│   │   │   └── exception/
│   │   │       ├── GlobalExceptionHandler.java
│   │   │       └── ResourceNotFoundException.java
│   │   └── resources/
│   │       └── application.yml
│   └── test/
│       └── java/com/example/{domain}/
│           └── {primary}ServiceTest.java
├── pom.xml
├── Dockerfile
└── docker-compose.yml
```

## Key Files

### src/main/java/com/example/{domain}/model/{primary}.java
```java
package com.example.{domain}.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "{primary.lower()}s")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class {primary} {{

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Status status = Status.ACTIVE;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by")
    private User createdBy;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    public enum Status {{
        ACTIVE, INACTIVE, ARCHIVED
    }}
}}
```

### src/main/java/com/example/{domain}/controller/{primary}Controller.java
```java
package com.example.{domain}.controller;

import com.example.{domain}.dto.*;
import com.example.{domain}.service.{primary}Service;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import java.util.UUID;

@RestController
@RequestMapping("/api/{primary.lower()}s")
@RequiredArgsConstructor
public class {primary}Controller {{

    private final {primary}Service {primary.lower()}Service;

    @GetMapping
    public ResponseEntity<Page<{primary}Response>> getAll(
            @RequestParam(required = false) String search,
            Pageable pageable) {{
        return ResponseEntity.ok({primary.lower()}Service.findAll(search, pageable));
    }}

    @GetMapping("/{{id}}")
    public ResponseEntity<{primary}Response> getById(@PathVariable UUID id) {{
        return ResponseEntity.ok({primary.lower()}Service.findById(id));
    }}

    @PostMapping
    public ResponseEntity<{primary}Response> create(
            @Valid @RequestBody {primary}Request request,
            @AuthenticationPrincipal UserDetails userDetails) {{
        return ResponseEntity
                .status(HttpStatus.CREATED)
                .body({primary.lower()}Service.create(request, userDetails.getUsername()));
    }}

    @PutMapping("/{{id}}")
    public ResponseEntity<{primary}Response> update(
            @PathVariable UUID id,
            @Valid @RequestBody {primary}Request request) {{
        return ResponseEntity.ok({primary.lower()}Service.update(id, request));
    }}

    @DeleteMapping("/{{id}}")
    public ResponseEntity<Void> delete(@PathVariable UUID id) {{
        {primary.lower()}Service.delete(id);
        return ResponseEntity.noContent().build();
    }}
}}
```

### src/main/java/com/example/{domain}/service/{primary}Service.java
```java
package com.example.{domain}.service;

import com.example.{domain}.dto.*;
import com.example.{domain}.exception.ResourceNotFoundException;
import com.example.{domain}.model.{primary};
import com.example.{domain}.model.User;
import com.example.{domain}.repository.{primary}Repository;
import com.example.{domain}.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional
public class {primary}Service {{

    private final {primary}Repository {primary.lower()}Repository;
    private final UserRepository userRepository;

    @Transactional(readOnly = true)
    public Page<{primary}Response> findAll(String search, Pageable pageable) {{
        Page<{primary}> page;
        if (search != null && !search.isEmpty()) {{
            page = {primary.lower()}Repository.findByNameContainingIgnoreCase(search, pageable);
        }} else {{
            page = {primary.lower()}Repository.findAll(pageable);
        }}
        return page.map(this::toResponse);
    }}

    @Transactional(readOnly = true)
    public {primary}Response findById(UUID id) {{
        return {primary.lower()}Repository.findById(id)
                .map(this::toResponse)
                .orElseThrow(() -> new ResourceNotFoundException("{primary} not found"));
    }}

    public {primary}Response create({primary}Request request, String username) {{
        User user = userRepository.findByEmail(username)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        {primary} {primary.lower()} = {primary}.builder()
                .name(request.getName())
                .description(request.getDescription())
                .status({primary}.Status.ACTIVE)
                .createdBy(user)
                .build();

        return toResponse({primary.lower()}Repository.save({primary.lower()}));
    }}

    public {primary}Response update(UUID id, {primary}Request request) {{
        {primary} {primary.lower()} = {primary.lower()}Repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("{primary} not found"));

        {primary.lower()}.setName(request.getName());
        {primary.lower()}.setDescription(request.getDescription());
        if (request.getStatus() != null) {{
            {primary.lower()}.setStatus(request.getStatus());
        }}

        return toResponse({primary.lower()}Repository.save({primary.lower()}));
    }}

    public void delete(UUID id) {{
        if (!{primary.lower()}Repository.existsById(id)) {{
            throw new ResourceNotFoundException("{primary} not found");
        }}
        {primary.lower()}Repository.deleteById(id);
    }}

    private {primary}Response toResponse({primary} {primary.lower()}) {{
        return {primary}Response.builder()
                .id({primary.lower()}.getId())
                .name({primary.lower()}.getName())
                .description({primary.lower()}.getDescription())
                .status({primary.lower()}.getStatus())
                .createdAt({primary.lower()}.getCreatedAt())
                .build();
    }}
}}
```

### pom.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>

    <groupId>com.example</groupId>
    <artifactId>{domain}</artifactId>
    <version>1.0.0</version>

    <properties>
        <java.version>21</java.version>
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
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-api</artifactId>
            <version>0.12.3</version>
        </dependency>
    </dependencies>
</project>
```

This Spring Boot 3 project includes JPA, Spring Security with JWT, PostgreSQL, and proper layered architecture.
'''


def generate_go_project(domain: str, domain_name: str, entities: List[str]) -> str:
    """Generate Go Gin project"""
    primary = entities[0]
    return f'''I'll create a complete {domain_name} with Go, Gin, GORM, and PostgreSQL.

## Project Structure

```
{domain}-go/
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── config/
│   │   └── config.go
│   ├── database/
│   │   └── database.go
│   ├── handlers/
│   │   ├── auth.go
│   │   └── {primary.lower()}.go
│   ├── middleware/
│   │   ├── auth.go
│   │   └── cors.go
│   ├── models/
│   │   ├── user.go
│   │   └── {primary.lower()}.go
│   ├── repository/
│   │   └── {primary.lower()}_repository.go
│   ├── services/
│   │   └── {primary.lower()}_service.go
│   └── router/
│       └── router.go
├── pkg/
│   └── utils/
│       ├── jwt.go
│       └── response.go
├── go.mod
├── go.sum
├── Dockerfile
└── docker-compose.yml
```

## Key Files

### internal/models/{primary.lower()}.go
```go
package models

import (
	"time"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type {primary} struct {{
	ID          uuid.UUID      `gorm:"type:uuid;primary_key" json:"id"`
	Name        string         `gorm:"not null" json:"name"`
	Description string         `gorm:"type:text" json:"description"`
	Status      string         `gorm:"default:active" json:"status"`
	CreatedBy   uuid.UUID      `gorm:"type:uuid" json:"created_by"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`

	User        *User          `gorm:"foreignKey:CreatedBy" json:"user,omitempty"`
}}

func (p *{primary}) BeforeCreate(tx *gorm.DB) error {{
	p.ID = uuid.New()
	return nil
}}

type Create{primary}Request struct {{
	Name        string `json:"name" binding:"required,min=1,max=255"`
	Description string `json:"description"`
}}

type Update{primary}Request struct {{
	Name        string `json:"name"`
	Description string `json:"description"`
	Status      string `json:"status"`
}}

type {primary}Response struct {{
	ID          uuid.UUID `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Status      string    `json:"status"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}}
```

### internal/handlers/{primary.lower()}.go
```go
package handlers

import (
	"net/http"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"{domain}-go/internal/models"
	"{domain}-go/internal/services"
)

type {primary}Handler struct {{
	service *services.{primary}Service
}}

func New{primary}Handler(service *services.{primary}Service) *{primary}Handler {{
	return &{primary}Handler{{service: service}}
}}

func (h *{primary}Handler) GetAll(c *gin.Context) {{
	page := c.DefaultQuery("page", "1")
	limit := c.DefaultQuery("limit", "20")
	search := c.Query("search")

	{primary.lower()}s, total, err := h.service.FindAll(page, limit, search)
	if err != nil {{
		c.JSON(http.StatusInternalServerError, gin.H{{"error": err.Error()}})
		return
	}}

	c.JSON(http.StatusOK, gin.H{{
		"data":  {primary.lower()}s,
		"total": total,
	}})
}}

func (h *{primary}Handler) GetByID(c *gin.Context) {{
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {{
		c.JSON(http.StatusBadRequest, gin.H{{"error": "invalid id"}})
		return
	}}

	{primary.lower()}, err := h.service.FindByID(id)
	if err != nil {{
		c.JSON(http.StatusNotFound, gin.H{{"error": "{primary} not found"}})
		return
	}}

	c.JSON(http.StatusOK, {primary.lower()})
}}

func (h *{primary}Handler) Create(c *gin.Context) {{
	var req models.Create{primary}Request
	if err := c.ShouldBindJSON(&req); err != nil {{
		c.JSON(http.StatusBadRequest, gin.H{{"error": err.Error()}})
		return
	}}

	userID := c.GetString("user_id")
	uid, _ := uuid.Parse(userID)

	{primary.lower()}, err := h.service.Create(&req, uid)
	if err != nil {{
		c.JSON(http.StatusInternalServerError, gin.H{{"error": err.Error()}})
		return
	}}

	c.JSON(http.StatusCreated, {primary.lower()})
}}

func (h *{primary}Handler) Update(c *gin.Context) {{
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {{
		c.JSON(http.StatusBadRequest, gin.H{{"error": "invalid id"}})
		return
	}}

	var req models.Update{primary}Request
	if err := c.ShouldBindJSON(&req); err != nil {{
		c.JSON(http.StatusBadRequest, gin.H{{"error": err.Error()}})
		return
	}}

	{primary.lower()}, err := h.service.Update(id, &req)
	if err != nil {{
		c.JSON(http.StatusInternalServerError, gin.H{{"error": err.Error()}})
		return
	}}

	c.JSON(http.StatusOK, {primary.lower()})
}}

func (h *{primary}Handler) Delete(c *gin.Context) {{
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {{
		c.JSON(http.StatusBadRequest, gin.H{{"error": "invalid id"}})
		return
	}}

	if err := h.service.Delete(id); err != nil {{
		c.JSON(http.StatusInternalServerError, gin.H{{"error": err.Error()}})
		return
	}}

	c.Status(http.StatusNoContent)
}}
```

### internal/router/router.go
```go
package router

import (
	"github.com/gin-gonic/gin"
	"{domain}-go/internal/handlers"
	"{domain}-go/internal/middleware"
)

func Setup(
	authHandler *handlers.AuthHandler,
	{primary.lower()}Handler *handlers.{primary}Handler,
) *gin.Engine {{
	r := gin.Default()

	r.Use(middleware.CORS())

	api := r.Group("/api")
	{{
		// Auth routes
		auth := api.Group("/auth")
		{{
			auth.POST("/register", authHandler.Register)
			auth.POST("/login", authHandler.Login)
		}}

		// Protected routes
		protected := api.Group("")
		protected.Use(middleware.Auth())
		{{
			{primary.lower()}s := protected.Group("/{primary.lower()}s")
			{{
				{primary.lower()}s.GET("", {primary.lower()}Handler.GetAll)
				{primary.lower()}s.GET("/:id", {primary.lower()}Handler.GetByID)
				{primary.lower()}s.POST("", {primary.lower()}Handler.Create)
				{primary.lower()}s.PUT("/:id", {primary.lower()}Handler.Update)
				{primary.lower()}s.DELETE("/:id", {primary.lower()}Handler.Delete)
			}}
		}}
	}}

	return r
}}
```

### go.mod
```go
module {domain}-go

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/golang-jwt/jwt/v5 v5.2.0
	github.com/google/uuid v1.5.0
	github.com/joho/godotenv v1.5.1
	golang.org/x/crypto v0.17.0
	gorm.io/driver/postgres v1.5.4
	gorm.io/gorm v1.25.5
)
```

This Go project uses Gin framework, GORM for database, JWT authentication, and clean architecture.
'''


def create_training_example(system_prompt: str, user_prompt: str, response: str) -> Dict:
    """Create training example"""
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_all_framework_examples(output_dir: Path):
    """Generate examples for all frameworks"""

    output_dir.mkdir(exist_ok=True)

    system_prompts = {
        "vue": "You are an expert Vue.js developer. Generate complete Vue 3 projects with TypeScript, Pinia, and Tailwind CSS.",
        "angular": "You are an expert Angular developer. Generate complete Angular 17+ projects with TypeScript, NgRx, and Angular Material.",
        "flutter": "You are an expert Flutter developer. Generate complete Flutter apps with Riverpod, clean architecture, and Material Design.",
        "spring": "You are an expert Java developer. Generate complete Spring Boot 3 projects with JPA, Spring Security, and PostgreSQL.",
        "go": "You are an expert Go developer. Generate complete Go projects with Gin, GORM, and clean architecture.",
    }

    generators = {
        "vue": generate_vue_project,
        "angular": generate_angular_project,
        "flutter": generate_flutter_project,
        "spring": generate_spring_boot_project,
        "go": generate_go_project,
    }

    prompt_templates = {
        "vue": [
            "Create a complete {domain} application with Vue 3, Pinia, and TypeScript",
            "Build a full-stack {domain} using Vue.js and Tailwind CSS",
        ],
        "angular": [
            "Create a complete {domain} application with Angular and NgRx",
            "Build an enterprise {domain} system using Angular and Angular Material",
        ],
        "flutter": [
            "Create a complete {domain} mobile app with Flutter and Riverpod",
            "Build a cross-platform {domain} application using Flutter",
        ],
        "spring": [
            "Create a complete {domain} API with Spring Boot and JPA",
            "Build an enterprise {domain} system using Spring Boot and PostgreSQL",
        ],
        "go": [
            "Create a complete {domain} API with Go and Gin",
            "Build a high-performance {domain} backend using Go and GORM",
        ],
    }

    all_examples = []

    for framework, generator in generators.items():
        print(f"Generating {framework} examples...")
        system_prompt = system_prompts[framework]

        for domain, domain_name, entities in DOMAINS:
            for prompt_template in prompt_templates[framework]:
                user_prompt = prompt_template.format(domain=domain_name)
                response = generator(domain, domain_name, entities)

                example = create_training_example(system_prompt, user_prompt, response)
                all_examples.append(example)

    # Shuffle
    random.shuffle(all_examples)

    # Split train/eval
    split_idx = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_idx]
    eval_examples = all_examples[split_idx:]

    # Save
    train_file = output_dir / "train.jsonl"
    eval_file = output_dir / "eval.jsonl"

    with open(train_file, 'w', encoding='utf-8') as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    with open(eval_file, 'w', encoding='utf-8') as f:
        for ex in eval_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nGenerated {len(all_examples)} framework examples")
    print(f"  Train: {len(train_examples)}")
    print(f"  Eval: {len(eval_examples)}")
    print(f"  Location: {output_dir}")

    return len(all_examples)


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "all_frameworks"
    generate_all_framework_examples(output_dir)
