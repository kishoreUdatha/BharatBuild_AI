'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Building2,
  GraduationCap,
  MapPin,
  User,
  Mail,
  Phone,
  Globe,
  Lock,
  ArrowRight,
  Check,
  Loader2,
  Shield,
  Award,
  Users,
  FileText
} from 'lucide-react'

interface RegistrationForm {
  // College Details
  name: string
  short_name: string
  aishe_code: string
  college_type: string
  university_affiliation: string
  year_established: string

  // Address
  address: string
  city: string
  state: string
  pincode: string

  // Contact
  phone: string
  email: string
  website: string

  // Principal
  principal_name: string
  principal_email: string
  principal_phone: string

  // Account
  admin_password: string
  confirm_password: string

  // Subscription
  subscription_plan: string
}

const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Puducherry', 'Chandigarh'
]

const COLLEGE_TYPES = [
  { value: 'autonomous', label: 'Autonomous' },
  { value: 'affiliated', label: 'Affiliated' },
  { value: 'deemed', label: 'Deemed University' },
  { value: 'central', label: 'Central University' },
  { value: 'state', label: 'State University' },
  { value: 'private', label: 'Private' },
]

const SUBSCRIPTION_PLANS = [
  {
    id: 'free_trial',
    name: 'Free Trial',
    price: 'Free',
    duration: '30 days',
    features: ['1 Criterion access', 'Basic reports', 'Email support']
  },
  {
    id: 'basic',
    name: 'Basic',
    price: '49,999',
    duration: 'per year',
    features: ['NAAC only', 'All 7 Criteria', 'SSR Generation', 'Email support']
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '99,999',
    duration: 'per year',
    features: ['NAAC + NBA', 'All Criteria', 'SSR + SAR', 'Priority support', 'DVV assistance'],
    popular: true
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: '1,99,999',
    duration: 'per year',
    features: ['Everything in Pro', 'Dedicated support', 'Custom training', 'On-site assistance', 'API access']
  }
]

export default function CollegeRegistrationPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState<RegistrationForm>({
    name: '',
    short_name: '',
    aishe_code: '',
    college_type: 'affiliated',
    university_affiliation: '',
    year_established: '',
    address: '',
    city: '',
    state: '',
    pincode: '',
    phone: '',
    email: '',
    website: '',
    principal_name: '',
    principal_email: '',
    principal_phone: '',
    admin_password: '',
    confirm_password: '',
    subscription_plan: 'free_trial'
  })

  const updateForm = (field: keyof RegistrationForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  const validateStep = (stepNum: number): boolean => {
    switch (stepNum) {
      case 1:
        if (!form.name || !form.city || !form.state) {
          setError('Please fill in all required fields')
          return false
        }
        break
      case 2:
        if (!form.principal_name || !form.principal_email) {
          setError('Principal details are required')
          return false
        }
        if (!form.principal_email.includes('@')) {
          setError('Please enter a valid email')
          return false
        }
        break
      case 3:
        if (!form.admin_password || form.admin_password.length < 8) {
          setError('Password must be at least 8 characters')
          return false
        }
        if (form.admin_password !== form.confirm_password) {
          setError('Passwords do not match')
          return false
        }
        break
    }
    return true
  }

  const nextStep = () => {
    if (validateStep(step)) {
      setStep(prev => Math.min(prev + 1, 4))
    }
  }

  const prevStep = () => {
    setStep(prev => Math.max(prev - 1, 1))
  }

  const handleSubmit = async () => {
    if (!validateStep(3)) return

    setIsLoading(true)
    setError('')

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
      const response = await fetch(`${API_URL}/onboarding/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          year_established: form.year_established ? parseInt(form.year_established) : null
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed')
      }

      // Store token and redirect
      if (data.access_token) {
        localStorage.setItem('access_token', data.access_token)
      }

      router.push(`/onboarding/setup?college_id=${data.id}`)
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-amber-500 rounded-xl flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">
              BharatBuild
            </span>
          </Link>
          <Link href="/login" className="text-slate-400 hover:text-white text-sm">
            Already registered? Login
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-12">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className="flex items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors ${
                step >= s
                  ? 'bg-orange-500 text-white'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {step > s ? <Check className="w-5 h-5" /> : s}
              </div>
              {s < 4 && (
                <div className={`w-20 h-1 mx-2 rounded ${
                  step > s ? 'bg-orange-500' : 'bg-slate-800'
                }`} />
              )}
            </div>
          ))}
        </div>

        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">
            {step === 1 && 'College Details'}
            {step === 2 && 'Principal Information'}
            {step === 3 && 'Create Account'}
            {step === 4 && 'Choose Plan'}
          </h1>
          <p className="text-slate-400">
            {step === 1 && 'Tell us about your institution'}
            {step === 2 && 'Who will manage the accreditation process?'}
            {step === 3 && 'Set up your admin login credentials'}
            {step === 4 && 'Select a subscription plan'}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6 text-center">
            {error}
          </div>
        )}

        {/* Step 1: College Details */}
        {step === 1 && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  College Name <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => updateForm('name', e.target.value)}
                    placeholder="e.g., ABC Engineering College"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Short Name
                </label>
                <input
                  type="text"
                  value={form.short_name}
                  onChange={(e) => updateForm('short_name', e.target.value)}
                  placeholder="e.g., ABCEC"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  AISHE Code
                </label>
                <input
                  type="text"
                  value={form.aishe_code}
                  onChange={(e) => updateForm('aishe_code', e.target.value)}
                  placeholder="e.g., C-12345"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  College Type
                </label>
                <select
                  value={form.college_type}
                  onChange={(e) => updateForm('college_type', e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                >
                  {COLLEGE_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  University Affiliation
                </label>
                <input
                  type="text"
                  value={form.university_affiliation}
                  onChange={(e) => updateForm('university_affiliation', e.target.value)}
                  placeholder="e.g., JNTU Hyderabad"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Year Established
                </label>
                <input
                  type="number"
                  value={form.year_established}
                  onChange={(e) => updateForm('year_established', e.target.value)}
                  placeholder="e.g., 1990"
                  min="1800"
                  max="2030"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  City <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    value={form.city}
                    onChange={(e) => updateForm('city', e.target.value)}
                    placeholder="e.g., Hyderabad"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  State <span className="text-red-400">*</span>
                </label>
                <select
                  value={form.state}
                  onChange={(e) => updateForm('state', e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                >
                  <option value="">Select State</option>
                  {INDIAN_STATES.map(state => (
                    <option key={state} value={state}>{state}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Pincode
                </label>
                <input
                  type="text"
                  value={form.pincode}
                  onChange={(e) => updateForm('pincode', e.target.value)}
                  placeholder="e.g., 500001"
                  maxLength={6}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Website
                </label>
                <div className="relative">
                  <Globe className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="url"
                    value={form.website}
                    onChange={(e) => updateForm('website', e.target.value)}
                    placeholder="https://www.college.edu"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  College Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => updateForm('email', e.target.value)}
                    placeholder="info@college.edu"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  College Phone
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="tel"
                    value={form.phone}
                    onChange={(e) => updateForm('phone', e.target.value)}
                    placeholder="+91 40 12345678"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Full Address
                </label>
                <textarea
                  value={form.address}
                  onChange={(e) => updateForm('address', e.target.value)}
                  placeholder="Enter complete address"
                  rows={2}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none resize-none"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Principal Information */}
        {step === 2 && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Principal / Director Name <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    value={form.principal_name}
                    onChange={(e) => updateForm('principal_name', e.target.value)}
                    placeholder="e.g., Dr. Rajesh Kumar"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Principal Email <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="email"
                    value={form.principal_email}
                    onChange={(e) => updateForm('principal_email', e.target.value)}
                    placeholder="principal@college.edu"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">This will be the admin login email</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Principal Phone
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="tel"
                    value={form.principal_phone}
                    onChange={(e) => updateForm('principal_phone', e.target.value)}
                    placeholder="+91 9876543210"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="mt-8 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-400 mb-1">Admin Account</h4>
                  <p className="text-sm text-slate-400">
                    The Principal will be the primary admin with full access to manage the accreditation process,
                    invite team members, and approve submissions.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Create Account */}
        {step === 3 && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8">
            <div className="max-w-md mx-auto space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Create Password <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="password"
                    value={form.admin_password}
                    onChange={(e) => updateForm('admin_password', e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Confirm Password <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="password"
                    value={form.confirm_password}
                    onChange={(e) => updateForm('confirm_password', e.target.value)}
                    placeholder="Re-enter password"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none"
                  />
                </div>
              </div>

              <div className="p-4 bg-slate-800 rounded-lg">
                <p className="text-sm text-slate-400 mb-2">Password requirements:</p>
                <ul className="text-sm space-y-1">
                  <li className={`flex items-center gap-2 ${form.admin_password.length >= 8 ? 'text-green-400' : 'text-slate-500'}`}>
                    <Check className="w-4 h-4" /> At least 8 characters
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Choose Plan */}
        {step === 4 && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {SUBSCRIPTION_PLANS.map((plan) => (
                <div
                  key={plan.id}
                  onClick={() => updateForm('subscription_plan', plan.id)}
                  className={`relative bg-slate-900/50 border rounded-2xl p-6 cursor-pointer transition-all ${
                    form.subscription_plan === plan.id
                      ? 'border-orange-500 ring-2 ring-orange-500/20'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-orange-500 text-white text-xs px-3 py-1 rounded-full font-medium">
                      Popular
                    </div>
                  )}

                  <h3 className="text-lg font-semibold mb-2">{plan.name}</h3>
                  <div className="mb-4">
                    <span className="text-2xl font-bold text-orange-400">
                      {plan.price === 'Free' ? 'Free' : `₹${plan.price}`}
                    </span>
                    <span className="text-slate-500 text-sm ml-1">/{plan.duration}</span>
                  </div>

                  <ul className="space-y-2 text-sm">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-slate-400">
                        <Check className="w-4 h-4 text-green-500" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-8">
          <button
            onClick={prevStep}
            disabled={step === 1}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              step === 1
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-slate-800 text-white hover:bg-slate-700'
            }`}
          >
            Back
          </button>

          {step < 4 ? (
            <button
              onClick={nextStep}
              className="flex items-center gap-2 px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-colors"
            >
              Continue <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={isLoading}
              className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Registering...
                </>
              ) : (
                <>
                  Complete Registration <Check className="w-4 h-4" />
                </>
              )}
            </button>
          )}
        </div>

        {/* Features */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-6">
            <div className="w-12 h-12 bg-orange-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Award className="w-6 h-6 text-orange-400" />
            </div>
            <h3 className="font-semibold mb-2">NAAC 2025 Framework</h3>
            <p className="text-sm text-slate-400">
              Full support for Binary Accreditation and MBGL assessment
            </p>
          </div>
          <div className="text-center p-6">
            <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Users className="w-6 h-6 text-blue-400" />
            </div>
            <h3 className="font-semibold mb-2">Team Collaboration</h3>
            <p className="text-sm text-slate-400">
              Role-based access for Principal, IQAC, HODs, and staff
            </p>
          </div>
          <div className="text-center p-6">
            <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
              <FileText className="w-6 h-6 text-green-400" />
            </div>
            <h3 className="font-semibold mb-2">Auto SSR Generation</h3>
            <p className="text-sm text-slate-400">
              AI-powered Self Study Report generation with DVV support
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
