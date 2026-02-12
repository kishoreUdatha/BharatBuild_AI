"""
Additional Tech Stack Training Data Generator
Generates training samples for Vue.js, Django, and React Native
"""
import json
from pathlib import Path


# ============================================
# VUE.JS + NUXT.JS SAMPLES
# ============================================

VUE_SAMPLES = [
    {
        "messages": [
            {"role": "system", "content": "You are an expert Vue.js developer."},
            {"role": "user", "content": "Create a Vue 3 button component with loading state using Composition API and Tailwind CSS"},
            {"role": "assistant", "content": """```vue
<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const variantClasses = computed(() => ({
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
  outline: 'border-2 border-gray-300 text-gray-700 hover:bg-gray-50',
}[props.variant]))

const sizeClasses = computed(() => ({
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
}[props.size]))

const handleClick = (event: MouseEvent) => {
  if (!props.loading && !props.disabled) {
    emit('click', event)
  }
}
</script>

<template>
  <button
    :class="[
      'inline-flex items-center justify-center font-medium rounded-lg transition-colors',
      'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      variantClasses,
      sizeClasses,
    ]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <svg
      v-if="loading"
      class="w-4 h-4 mr-2 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
    <slot />
  </button>
</template>
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Vue.js developer."},
            {"role": "user", "content": "Create a Vue 3 login form with Vee-Validate and Yup validation"},
            {"role": "assistant", "content": """```vue
<script setup lang="ts">
import { useForm } from 'vee-validate'
import * as yup from 'yup'
import { ref } from 'vue'

const emit = defineEmits<{
  submit: [data: { email: string; password: string }]
}>()

const schema = yup.object({
  email: yup.string().required('Email is required').email('Invalid email'),
  password: yup.string().required('Password is required').min(8, 'Min 8 characters'),
})

const { handleSubmit, errors, defineField, isSubmitting } = useForm({
  validationSchema: schema,
})

const [email, emailAttrs] = defineField('email')
const [password, passwordAttrs] = defineField('password')
const showPassword = ref(false)

const onSubmit = handleSubmit((values) => {
  emit('submit', values)
})
</script>

<template>
  <form @submit="onSubmit" class="space-y-4 max-w-md mx-auto p-6 bg-white rounded-xl shadow-lg">
    <h2 class="text-2xl font-bold text-center text-gray-900 mb-6">Welcome Back</h2>

    <div>
      <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
      <input
        id="email"
        v-model="email"
        v-bind="emailAttrs"
        type="email"
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="you@example.com"
      />
      <p v-if="errors.email" class="mt-1 text-sm text-red-600">{{ errors.email }}</p>
    </div>

    <div>
      <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
      <div class="relative">
        <input
          id="password"
          v-model="password"
          v-bind="passwordAttrs"
          :type="showPassword ? 'text' : 'password'"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="••••••••"
        />
        <button
          type="button"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
          @click="showPassword = !showPassword"
        >
          {{ showPassword ? 'Hide' : 'Show' }}
        </button>
      </div>
      <p v-if="errors.password" class="mt-1 text-sm text-red-600">{{ errors.password }}</p>
    </div>

    <button
      type="submit"
      :disabled="isSubmitting"
      class="w-full py-2 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
    >
      {{ isSubmitting ? 'Signing in...' : 'Sign In' }}
    </button>
  </form>
</template>
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Vue.js developer."},
            {"role": "user", "content": "Create a Vue 3 modal component with transitions and teleport"},
            {"role": "assistant", "content": """```vue
<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'

interface Props {
  modelValue: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const close = () => emit('update:modelValue', false)

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
}

const handleEscape = (e: KeyboardEvent) => {
  if (e.key === 'Escape') close()
}

watch(() => props.modelValue, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/50" @click="close" />

        <!-- Modal -->
        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="modelValue"
            :class="['relative bg-white rounded-xl shadow-xl w-full', sizeClasses[size]]"
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b">
              <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
              <button
                @click="close"
                class="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div class="p-4">
              <slot />
            </div>

            <!-- Footer -->
            <div v-if="$slots.footer" class="p-4 border-t bg-gray-50 rounded-b-xl">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Vue.js developer."},
            {"role": "user", "content": "Create a Nuxt 3 API route for user authentication with JWT"},
            {"role": "assistant", "content": """```typescript
// server/api/auth/login.post.ts
import jwt from 'jsonwebtoken'
import bcrypt from 'bcrypt'
import { z } from 'zod'

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)

  // Validate input
  const result = loginSchema.safeParse(body)
  if (!result.success) {
    throw createError({
      statusCode: 400,
      message: 'Invalid input',
      data: result.error.errors,
    })
  }

  const { email, password } = result.data

  // Find user (replace with your database query)
  const user = await prisma.user.findUnique({ where: { email } })

  if (!user) {
    throw createError({
      statusCode: 401,
      message: 'Invalid credentials',
    })
  }

  // Verify password
  const validPassword = await bcrypt.compare(password, user.hashedPassword)
  if (!validPassword) {
    throw createError({
      statusCode: 401,
      message: 'Invalid credentials',
    })
  }

  // Generate tokens
  const accessToken = jwt.sign(
    { userId: user.id, email: user.email },
    config.jwtSecret,
    { expiresIn: '15m' }
  )

  const refreshToken = jwt.sign(
    { userId: user.id },
    config.jwtRefreshSecret,
    { expiresIn: '7d' }
  )

  // Set refresh token as httpOnly cookie
  setCookie(event, 'refresh_token', refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7, // 7 days
  })

  return {
    user: {
      id: user.id,
      email: user.email,
      name: user.name,
    },
    accessToken,
  }
})
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Vue.js developer."},
            {"role": "user", "content": "Create a Vue 3 composable for API fetching with loading and error states"},
            {"role": "assistant", "content": """```typescript
// composables/useApi.ts
import { ref, computed } from 'vue'

interface UseApiOptions<T> {
  immediate?: boolean
  initialData?: T
  onSuccess?: (data: T) => void
  onError?: (error: Error) => void
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  options: UseApiOptions<T> = {}
) {
  const { immediate = false, initialData, onSuccess, onError } = options

  const data = ref<T | undefined>(initialData) as Ref<T | undefined>
  const error = ref<Error | null>(null)
  const isLoading = ref(false)

  const isError = computed(() => error.value !== null)
  const isSuccess = computed(() => data.value !== undefined && !error.value)

  async function execute() {
    isLoading.value = true
    error.value = null

    try {
      const result = await fetcher()
      data.value = result
      onSuccess?.(result)
      return result
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e))
      error.value = err
      onError?.(err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function reset() {
    data.value = initialData
    error.value = null
    isLoading.value = false
  }

  if (immediate) {
    execute()
  }

  return {
    data,
    error,
    isLoading,
    isError,
    isSuccess,
    execute,
    reset,
  }
}

// Usage example:
// const { data: users, isLoading, execute } = useApi(
//   () => $fetch('/api/users'),
//   { immediate: true }
// )
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Vue.js developer."},
            {"role": "user", "content": "Create a Vue 3 data table component with sorting and pagination"},
            {"role": "assistant", "content": """```vue
<script setup lang="ts" generic="T extends Record<string, any>">
import { computed, ref } from 'vue'

interface Column<T> {
  key: keyof T
  label: string
  sortable?: boolean
  render?: (value: any, row: T) => string
}

interface Props {
  data: T[]
  columns: Column<T>[]
  pageSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  pageSize: 10,
})

const sortKey = ref<keyof T | null>(null)
const sortOrder = ref<'asc' | 'desc'>('asc')
const currentPage = ref(1)

const sortedData = computed(() => {
  if (!sortKey.value) return props.data

  return [...props.data].sort((a, b) => {
    const aVal = a[sortKey.value!]
    const bVal = b[sortKey.value!]

    if (aVal < bVal) return sortOrder.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * props.pageSize
  return sortedData.value.slice(start, start + props.pageSize)
})

const totalPages = computed(() => Math.ceil(props.data.length / props.pageSize))

function toggleSort(key: keyof T) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="min-w-full divide-y divide-gray-200">
      <thead class="bg-gray-50">
        <tr>
          <th
            v-for="col in columns"
            :key="String(col.key)"
            class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            :class="{ 'cursor-pointer hover:bg-gray-100': col.sortable }"
            @click="col.sortable && toggleSort(col.key)"
          >
            <div class="flex items-center gap-2">
              {{ col.label }}
              <span v-if="col.sortable && sortKey === col.key">
                {{ sortOrder === 'asc' ? '↑' : '↓' }}
              </span>
            </div>
          </th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
        <tr v-for="(row, idx) in paginatedData" :key="idx" class="hover:bg-gray-50">
          <td v-for="col in columns" :key="String(col.key)" class="px-6 py-4 whitespace-nowrap">
            {{ col.render ? col.render(row[col.key], row) : row[col.key] }}
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Pagination -->
    <div class="flex items-center justify-between px-4 py-3 border-t">
      <span class="text-sm text-gray-700">
        Page {{ currentPage }} of {{ totalPages }}
      </span>
      <div class="flex gap-2">
        <button
          :disabled="currentPage === 1"
          class="px-3 py-1 border rounded disabled:opacity-50"
          @click="currentPage--"
        >
          Previous
        </button>
        <button
          :disabled="currentPage === totalPages"
          class="px-3 py-1 border rounded disabled:opacity-50"
          @click="currentPage++"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>
```"""}
        ]
    },
]

# ============================================
# DJANGO + DRF SAMPLES
# ============================================

DJANGO_SAMPLES = [
    {
        "messages": [
            {"role": "system", "content": "You are an expert Django developer."},
            {"role": "user", "content": "Create a Django User model with custom manager and authentication"},
            {"role": "assistant", "content": """```python
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return self.name
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Django developer."},
            {"role": "user", "content": "Create Django REST Framework serializers for User with nested profile"},
            {"role": "assistant", "content": """```python
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'website', 'avatar_url']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'is_verified', 'created_at', 'profile']
        read_only_fields = ['id', 'is_verified', 'created_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Incorrect password')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Django developer."},
            {"role": "user", "content": "Create Django REST Framework viewset for products with filtering and pagination"},
            {"role": "assistant", "content": """```python
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg

from .models import Product, Review
from .serializers import ProductSerializer, ProductCreateSerializer, ReviewSerializer
from .filters import ProductFilter
from .pagination import StandardPagination


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related('category', 'brand')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Annotate with average rating
        return queryset.annotate(avg_rating=Avg('reviews__rating'))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        product = self.get_object()
        reviews = product.reviews.select_related('user').order_by('-created_at')
        page = self.paginate_queryset(reviews)
        serializer = ReviewSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_review(self, request, pk=None):
        product = self.get_object()

        # Check if user already reviewed
        if product.reviews.filter(user=request.user).exists():
            return Response(
                {'error': 'You have already reviewed this product'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured = self.get_queryset().filter(is_featured=True)[:10]
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Django developer."},
            {"role": "user", "content": "Create Django JWT authentication views with refresh tokens"},
            {"role": "assistant", "content": """```python
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model

from .serializers import (
    UserCreateSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)

            return Response({
                'access': str(token.access_token),
                'refresh': str(token),
            })
        except Exception:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Django developer."},
            {"role": "user", "content": "Create Django model for e-commerce Order with items and payment"},
            {"role": "assistant", "content": """```python
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Shipping
    shipping_address = models.JSONField(default=dict)
    billing_address = models.JSONField(default=dict)

    # Payment
    payment_method = models.CharField(max_length=50, blank=True)
    payment_id = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        self.calculate_totals()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        from django.utils import timezone
        return f"ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    def calculate_totals(self):
        self.subtotal = sum(item.total for item in self.items.all())
        self.total = self.subtotal + self.tax + self.shipping_cost - self.discount


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)
```"""}
        ]
    },
]

# ============================================
# REACT NATIVE + EXPO SAMPLES
# ============================================

REACT_NATIVE_SAMPLES = [
    {
        "messages": [
            {"role": "system", "content": "You are an expert React Native developer."},
            {"role": "user", "content": "Create a React Native button component with variants and loading state"},
            {"role": "assistant", "content": """```tsx
import React from 'react';
import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
  TextStyle,
} from 'react-native';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
}

export default function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  style,
}: ButtonProps) {
  const isDisabled = disabled || loading;

  const buttonStyles: ViewStyle[] = [
    styles.base,
    styles[variant],
    styles[`size_${size}`],
    isDisabled && styles.disabled,
    style,
  ];

  const textStyles: TextStyle[] = [
    styles.text,
    styles[`text_${variant}`],
    styles[`text_${size}`],
  ];

  return (
    <TouchableOpacity
      style={buttonStyles}
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.7}
    >
      {loading ? (
        <ActivityIndicator
          color={variant === 'outline' ? '#3B82F6' : '#FFFFFF'}
          size="small"
        />
      ) : (
        <Text style={textStyles}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  primary: {
    backgroundColor: '#3B82F6',
  },
  secondary: {
    backgroundColor: '#6B7280',
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: '#3B82F6',
  },
  size_sm: {
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  size_md: {
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  size_lg: {
    paddingVertical: 16,
    paddingHorizontal: 32,
  },
  disabled: {
    opacity: 0.5,
  },
  text: {
    fontWeight: '600',
  },
  text_primary: {
    color: '#FFFFFF',
  },
  text_secondary: {
    color: '#FFFFFF',
  },
  text_outline: {
    color: '#3B82F6',
  },
  text_sm: {
    fontSize: 14,
  },
  text_md: {
    fontSize: 16,
  },
  text_lg: {
    fontSize: 18,
  },
});
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert React Native developer."},
            {"role": "user", "content": "Create a React Native login screen with form validation"},
            {"role": "assistant", "content": """```tsx
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type FormData = z.infer<typeof schema>;

interface LoginScreenProps {
  onLogin: (data: FormData) => Promise<void>;
  onForgotPassword: () => void;
  onSignUp: () => void;
}

export default function LoginScreen({
  onLogin,
  onForgotPassword,
  onSignUp,
}: LoginScreenProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setIsLoading(true);
    try {
      await onLogin(data);
    } catch (error) {
      Alert.alert('Error', 'Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <Text style={styles.title}>Welcome Back</Text>
        <Text style={styles.subtitle}>Sign in to continue</Text>

        <View style={styles.form}>
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Email</Text>
            <Controller
              control={control}
              name="email"
              render={({ field: { onChange, onBlur, value } }) => (
                <TextInput
                  style={[styles.input, errors.email && styles.inputError]}
                  placeholder="you@example.com"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  onBlur={onBlur}
                  onChangeText={onChange}
                  value={value}
                />
              )}
            />
            {errors.email && (
              <Text style={styles.errorText}>{errors.email.message}</Text>
            )}
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>Password</Text>
            <View style={styles.passwordContainer}>
              <Controller
                control={control}
                name="password"
                render={({ field: { onChange, onBlur, value } }) => (
                  <TextInput
                    style={[styles.input, styles.passwordInput, errors.password && styles.inputError]}
                    placeholder="••••••••"
                    secureTextEntry={!showPassword}
                    onBlur={onBlur}
                    onChangeText={onChange}
                    value={value}
                  />
                )}
              />
              <TouchableOpacity
                style={styles.eyeButton}
                onPress={() => setShowPassword(!showPassword)}
              >
                <Text>{showPassword ? 'Hide' : 'Show'}</Text>
              </TouchableOpacity>
            </View>
            {errors.password && (
              <Text style={styles.errorText}>{errors.password.message}</Text>
            )}
          </View>

          <TouchableOpacity onPress={onForgotPassword}>
            <Text style={styles.forgotPassword}>Forgot Password?</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, isLoading && styles.buttonDisabled]}
            onPress={handleSubmit(onSubmit)}
            disabled={isLoading}
          >
            <Text style={styles.buttonText}>
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>Don't have an account? </Text>
          <TouchableOpacity onPress={onSignUp}>
            <Text style={styles.signUpText}>Sign Up</Text>
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  content: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: 'bold', color: '#1F2937', marginBottom: 8 },
  subtitle: { fontSize: 16, color: '#6B7280', marginBottom: 32 },
  form: { gap: 16 },
  inputContainer: { gap: 4 },
  label: { fontSize: 14, fontWeight: '500', color: '#374151' },
  input: {
    borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 8,
    padding: 12, fontSize: 16,
  },
  inputError: { borderColor: '#EF4444' },
  errorText: { color: '#EF4444', fontSize: 12 },
  passwordContainer: { position: 'relative' },
  passwordInput: { paddingRight: 60 },
  eyeButton: { position: 'absolute', right: 12, top: 12 },
  forgotPassword: { color: '#3B82F6', textAlign: 'right' },
  button: {
    backgroundColor: '#3B82F6', padding: 16, borderRadius: 8,
    alignItems: 'center', marginTop: 8,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: 24 },
  footerText: { color: '#6B7280' },
  signUpText: { color: '#3B82F6', fontWeight: '600' },
});
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert React Native developer."},
            {"role": "user", "content": "Create a React Native bottom tab navigator with Expo Router"},
            {"role": "assistant", "content": """```tsx
// app/(tabs)/_layout.tsx
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Platform } from 'react-native';

type IconName = keyof typeof Ionicons.glyphMap;

interface TabConfig {
  name: string;
  title: string;
  icon: IconName;
  iconFocused: IconName;
}

const tabs: TabConfig[] = [
  { name: 'index', title: 'Home', icon: 'home-outline', iconFocused: 'home' },
  { name: 'search', title: 'Search', icon: 'search-outline', iconFocused: 'search' },
  { name: 'cart', title: 'Cart', icon: 'cart-outline', iconFocused: 'cart' },
  { name: 'profile', title: 'Profile', icon: 'person-outline', iconFocused: 'person' },
];

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#3B82F6',
        tabBarInactiveTintColor: '#6B7280',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopWidth: 1,
          borderTopColor: '#E5E7EB',
          paddingBottom: Platform.OS === 'ios' ? 20 : 8,
          paddingTop: 8,
          height: Platform.OS === 'ios' ? 88 : 64,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
      }}
    >
      {tabs.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: tab.title,
            tabBarIcon: ({ focused, color, size }) => (
              <Ionicons
                name={focused ? tab.iconFocused : tab.icon}
                size={size}
                color={color}
              />
            ),
          }}
        />
      ))}
    </Tabs>
  );
}

// app/(tabs)/index.tsx
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function HomeScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Home</Text>
        {/* Your home content */}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  content: { padding: 16 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#1F2937' },
});
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert React Native developer."},
            {"role": "user", "content": "Create a React Native custom hook for API calls with caching"},
            {"role": "assistant", "content": """```tsx
import { useState, useEffect, useCallback, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface UseApiOptions<T> {
  cacheKey?: string;
  cacheDuration?: number; // in milliseconds
  initialData?: T;
  enabled?: boolean;
}

interface UseApiResult<T> {
  data: T | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  mutate: (newData: T) => void;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  options: UseApiOptions<T> = {}
): UseApiResult<T> {
  const {
    cacheKey,
    cacheDuration = 5 * 60 * 1000, // 5 minutes default
    initialData,
    enabled = true,
  } = options;

  const [data, setData] = useState<T | undefined>(initialData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const mountedRef = useRef(true);

  const getCachedData = useCallback(async (): Promise<T | null> => {
    if (!cacheKey) return null;

    try {
      const cached = await AsyncStorage.getItem(cacheKey);
      if (cached) {
        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < cacheDuration) {
          return data;
        }
        // Cache expired, remove it
        await AsyncStorage.removeItem(cacheKey);
      }
    } catch {
      // Ignore cache errors
    }
    return null;
  }, [cacheKey, cacheDuration]);

  const setCachedData = useCallback(async (data: T) => {
    if (!cacheKey) return;

    try {
      await AsyncStorage.setItem(
        cacheKey,
        JSON.stringify({ data, timestamp: Date.now() })
      );
    } catch {
      // Ignore cache errors
    }
  }, [cacheKey]);

  const fetchData = useCallback(async () => {
    if (!enabled) return;

    setIsLoading(true);
    setError(null);

    try {
      // Try cache first
      const cachedData = await getCachedData();
      if (cachedData && mountedRef.current) {
        setData(cachedData);
        setIsLoading(false);
        return;
      }

      // Fetch fresh data
      const result = await fetcher();

      if (mountedRef.current) {
        setData(result);
        await setCachedData(result);
      }
    } catch (e) {
      if (mountedRef.current) {
        setError(e instanceof Error ? e : new Error(String(e)));
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [enabled, fetcher, getCachedData, setCachedData]);

  const refetch = useCallback(async () => {
    // Clear cache and refetch
    if (cacheKey) {
      await AsyncStorage.removeItem(cacheKey);
    }
    await fetchData();
  }, [cacheKey, fetchData]);

  const mutate = useCallback((newData: T) => {
    setData(newData);
    setCachedData(newData);
  }, [setCachedData]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  return { data, isLoading, error, refetch, mutate };
}

// Usage:
// const { data: products, isLoading, refetch } = useApi(
//   () => api.get('/products'),
//   { cacheKey: 'products', cacheDuration: 10 * 60 * 1000 }
// );
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert React Native developer."},
            {"role": "user", "content": "Create a React Native product card component for e-commerce app"},
            {"role": "assistant", "content": """```tsx
import React from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');
const CARD_WIDTH = (width - 48) / 2;

interface Product {
  id: string;
  name: string;
  price: number;
  originalPrice?: number;
  image: string;
  rating: number;
  reviewCount: number;
  isNew?: boolean;
  isFavorite?: boolean;
}

interface ProductCardProps {
  product: Product;
  onPress: () => void;
  onAddToCart: () => void;
  onToggleFavorite: () => void;
}

export default function ProductCard({
  product,
  onPress,
  onAddToCart,
  onToggleFavorite,
}: ProductCardProps) {
  const discount = product.originalPrice
    ? Math.round((1 - product.price / product.originalPrice) * 100)
    : 0;

  return (
    <TouchableOpacity style={styles.container} onPress={onPress} activeOpacity={0.9}>
      {/* Image */}
      <View style={styles.imageContainer}>
        <Image source={{ uri: product.image }} style={styles.image} resizeMode="cover" />

        {/* Badges */}
        <View style={styles.badges}>
          {product.isNew && (
            <View style={styles.newBadge}>
              <Text style={styles.newBadgeText}>NEW</Text>
            </View>
          )}
          {discount > 0 && (
            <View style={styles.discountBadge}>
              <Text style={styles.discountBadgeText}>-{discount}%</Text>
            </View>
          )}
        </View>

        {/* Favorite Button */}
        <TouchableOpacity style={styles.favoriteButton} onPress={onToggleFavorite}>
          <Ionicons
            name={product.isFavorite ? 'heart' : 'heart-outline'}
            size={20}
            color={product.isFavorite ? '#EF4444' : '#6B7280'}
          />
        </TouchableOpacity>
      </View>

      {/* Content */}
      <View style={styles.content}>
        <Text style={styles.name} numberOfLines={2}>{product.name}</Text>

        {/* Rating */}
        <View style={styles.ratingContainer}>
          <Ionicons name="star" size={14} color="#FBBF24" />
          <Text style={styles.rating}>{product.rating.toFixed(1)}</Text>
          <Text style={styles.reviewCount}>({product.reviewCount})</Text>
        </View>

        {/* Price */}
        <View style={styles.priceContainer}>
          <Text style={styles.price}>${product.price.toFixed(2)}</Text>
          {product.originalPrice && (
            <Text style={styles.originalPrice}>${product.originalPrice.toFixed(2)}</Text>
          )}
        </View>

        {/* Add to Cart */}
        <TouchableOpacity style={styles.addButton} onPress={onAddToCart}>
          <Ionicons name="cart-outline" size={18} color="#FFFFFF" />
          <Text style={styles.addButtonText}>Add</Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    width: CARD_WIDTH,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  imageContainer: { position: 'relative', height: CARD_WIDTH },
  image: { width: '100%', height: '100%' },
  badges: { position: 'absolute', top: 8, left: 8, gap: 4 },
  newBadge: { backgroundColor: '#3B82F6', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4 },
  newBadgeText: { color: '#FFFFFF', fontSize: 10, fontWeight: 'bold' },
  discountBadge: { backgroundColor: '#EF4444', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4 },
  discountBadgeText: { color: '#FFFFFF', fontSize: 10, fontWeight: 'bold' },
  favoriteButton: {
    position: 'absolute', top: 8, right: 8,
    backgroundColor: '#FFFFFF', borderRadius: 20, padding: 6,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1, shadowRadius: 2, elevation: 2,
  },
  content: { padding: 12, gap: 6 },
  name: { fontSize: 14, fontWeight: '500', color: '#1F2937', lineHeight: 20 },
  ratingContainer: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  rating: { fontSize: 12, fontWeight: '600', color: '#1F2937' },
  reviewCount: { fontSize: 12, color: '#6B7280' },
  priceContainer: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  price: { fontSize: 16, fontWeight: 'bold', color: '#1F2937' },
  originalPrice: { fontSize: 14, color: '#9CA3AF', textDecorationLine: 'line-through' },
  addButton: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    backgroundColor: '#3B82F6', paddingVertical: 8, borderRadius: 8, gap: 4, marginTop: 4,
  },
  addButtonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '600' },
});
```"""}
        ]
    },
]


def generate_additional_samples():
    """Generate all additional tech stack samples"""
    all_samples = []

    # Add Vue samples
    all_samples.extend(VUE_SAMPLES)

    # Add Django samples
    all_samples.extend(DJANGO_SAMPLES)

    # Add React Native samples
    all_samples.extend(REACT_NATIVE_SAMPLES)

    # Augment with variations
    augmented = []
    for sample in all_samples:
        augmented.append(sample)
        # Add "Please" variation
        var = {"messages": sample["messages"].copy()}
        user_content = sample["messages"][1]["content"]
        var["messages"] = [
            sample["messages"][0],
            {"role": "user", "content": "Please " + user_content[0].lower() + user_content[1:]},
            sample["messages"][2]
        ]
        augmented.append(var)

    return augmented


def save_additional_samples(output_dir: str = "./data/additional"):
    """Save additional tech stack samples to file"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    samples = generate_additional_samples()

    output_file = Path(output_dir) / "additional_stacks.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"Generated {len(samples)} additional samples")
    print(f"  - Vue.js/Nuxt: {len(VUE_SAMPLES) * 2}")
    print(f"  - Django/DRF: {len(DJANGO_SAMPLES) * 2}")
    print(f"  - React Native: {len(REACT_NATIVE_SAMPLES) * 2}")
    print(f"Saved to: {output_file}")

    return samples


if __name__ == "__main__":
    save_additional_samples()
