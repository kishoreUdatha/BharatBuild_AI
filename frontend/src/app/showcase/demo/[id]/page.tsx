'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  ArrowLeft, ShoppingCart, Search, Plus, Star, Package, User, Send, Check,
  MessageSquare, Heart, Menu, X, Home, Settings, Bell, ChevronRight,
  Play, Pause, SkipBack, SkipForward, Volume2, Repeat, Shuffle,
  Music, MapPin, Clock, Phone, Mail, Calendar, Users, Activity,
  DollarSign, TrendingUp, BarChart3, PieChart, FileText, Download,
  Stethoscope, BookOpen, GraduationCap, CheckCircle, Circle, Filter,
  Globe, Zap, Sparkles, Code, Layers, Eye, Edit, Trash2, Share2,
  CreditCard, Truck, Shield, Award, ThumbsUp, MessageCircle, Image,
  Video, Mic, Paperclip, Smile, MoreVertical, ChevronDown, LogOut,
  Wallet, Receipt, PiggyBank, Target, Coffee, Utensils, Pizza,
  ShoppingBag, Gift, Plane, Car, Building, Briefcase
} from 'lucide-react'

// =============== SAAS LANDING PAGE DEMO ===============
function SaaSLandingDemo() {
  const [mobileMenu, setMobileMenu] = useState(false)

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-violet-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl">SaaSify</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
            <a href="#testimonials" className="hover:text-white transition-colors">Testimonials</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </div>
          <div className="hidden md:flex items-center gap-4">
            <button className="text-sm text-gray-400 hover:text-white transition-colors">Sign In</button>
            <button className="px-5 py-2.5 bg-gradient-to-r from-violet-500 to-cyan-500 rounded-xl text-sm font-medium hover:opacity-90 transition-opacity">
              Start Free Trial
            </button>
          </div>
          <button onClick={() => setMobileMenu(!mobileMenu)} className="md:hidden p-2">
            {mobileMenu ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
        {mobileMenu && (
          <div className="md:hidden bg-slate-900 border-b border-white/10 p-4 space-y-4">
            <a href="#features" className="block text-gray-400 hover:text-white">Features</a>
            <a href="#pricing" className="block text-gray-400 hover:text-white">Pricing</a>
            <a href="#testimonials" className="block text-gray-400 hover:text-white">Testimonials</a>
            <button className="w-full py-3 bg-gradient-to-r from-violet-500 to-cyan-500 rounded-xl font-medium">Start Free Trial</button>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-violet-500/20 rounded-full blur-[120px]" />
          <div className="absolute top-40 right-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-[120px]" />
        </div>
        <div className="relative max-w-7xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-violet-500/10 border border-violet-500/20 rounded-full text-violet-400 text-sm mb-8">
            <Sparkles className="w-4 h-4" /> New: AI-Powered Analytics Dashboard
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            Build Better Products
            <br />
            <span className="bg-gradient-to-r from-violet-400 via-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Ship Faster
            </span>
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10">
            The all-in-one platform for modern teams to collaborate, track progress, and deliver exceptional products.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button className="px-8 py-4 bg-gradient-to-r from-violet-500 to-cyan-500 rounded-xl font-semibold text-lg hover:opacity-90 transition-opacity shadow-lg shadow-violet-500/25">
              Start Free Trial
            </button>
            <button className="px-8 py-4 border border-white/20 rounded-xl font-semibold text-lg hover:bg-white/5 transition-colors flex items-center justify-center gap-2">
              <Play className="w-5 h-5" /> Watch Demo
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-6">No credit card required • 14-day free trial</p>
        </div>
      </section>

      {/* Logos */}
      <section className="py-16 border-y border-white/10">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-gray-500 mb-8">Trusted by 10,000+ companies worldwide</p>
          <div className="flex flex-wrap justify-center items-center gap-12 opacity-50">
            {['Google', 'Microsoft', 'Amazon', 'Meta', 'Apple'].map((company) => (
              <div key={company} className="text-2xl font-bold text-gray-400">{company}</div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Everything you need to succeed</h2>
            <p className="text-gray-400 text-lg">Powerful features to help your team deliver faster</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: BarChart3, title: 'Real-time Analytics', desc: 'Track performance metrics and make data-driven decisions' },
              { icon: Users, title: 'Team Collaboration', desc: 'Work together seamlessly with real-time updates' },
              { icon: Shield, title: 'Enterprise Security', desc: 'Bank-grade encryption and compliance certifications' },
              { icon: Zap, title: 'Lightning Fast', desc: 'Optimized for speed with global CDN infrastructure' },
              { icon: Code, title: 'Developer API', desc: 'Integrate with your existing tools and workflows' },
              { icon: Bell, title: 'Smart Notifications', desc: 'Stay informed with intelligent alerts and updates' },
            ].map((feature, i) => (
              <div key={i} className="p-8 bg-slate-900/50 border border-white/10 rounded-2xl hover:border-violet-500/50 transition-colors group">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-r from-violet-500/20 to-cyan-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <feature.icon className="w-7 h-7 text-violet-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-gray-400">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 bg-slate-900/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Simple, transparent pricing</h2>
            <p className="text-gray-400 text-lg">Choose the plan that fits your needs</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { name: 'Starter', price: '$9', features: ['5 team members', '10GB storage', 'Basic analytics', 'Email support'] },
              { name: 'Pro', price: '$29', features: ['Unlimited members', '100GB storage', 'Advanced analytics', 'Priority support', 'API access'], popular: true },
              { name: 'Enterprise', price: '$99', features: ['Unlimited everything', 'Custom integrations', 'Dedicated support', 'SLA guarantee', 'On-premise option'] },
            ].map((plan, i) => (
              <div key={i} className={`p-8 rounded-2xl ${plan.popular ? 'bg-gradient-to-b from-violet-500/20 to-cyan-500/20 border-2 border-violet-500' : 'bg-slate-800/50 border border-white/10'}`}>
                {plan.popular && <div className="text-violet-400 text-sm font-medium mb-4">Most Popular</div>}
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-gray-400">/month</span>
                </div>
                <ul className="space-y-4 mb-8">
                  {plan.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-3 text-gray-300">
                      <CheckCircle className="w-5 h-5 text-green-400" /> {f}
                    </li>
                  ))}
                </ul>
                <button className={`w-full py-3 rounded-xl font-medium transition-opacity ${plan.popular ? 'bg-gradient-to-r from-violet-500 to-cyan-500 hover:opacity-90' : 'bg-white/10 hover:bg-white/20'}`}>
                  Get Started
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-16 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-violet-500 to-cyan-500 flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-xl">SaaSify</span>
            </div>
            <p className="text-gray-500">© 2024 SaaSify. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

// =============== E-COMMERCE DEMO ===============
function EcommerceDemo() {
  const [cart, setCart] = useState<any[]>([])
  const [showCart, setShowCart] = useState(false)
  const [category, setCategory] = useState('all')

  const products = [
    { id: 1, name: 'Wireless Earbuds Pro', price: 2999, rating: 4.8, image: '🎧', category: 'electronics' },
    { id: 2, name: 'Smart Watch Ultra', price: 4999, rating: 4.9, image: '⌚', category: 'electronics' },
    { id: 3, name: 'Power Bank 20000mAh', price: 1499, rating: 4.5, image: '🔋', category: 'electronics' },
    { id: 4, name: 'USB-C Hub 7-in-1', price: 1999, rating: 4.7, image: '🔌', category: 'electronics' },
    { id: 5, name: 'Running Shoes', price: 3499, rating: 4.6, image: '👟', category: 'fashion' },
    { id: 6, name: 'Laptop Backpack', price: 1299, rating: 4.4, image: '🎒', category: 'fashion' },
    { id: 7, name: 'Coffee Maker', price: 2499, rating: 4.3, image: '☕', category: 'home' },
    { id: 8, name: 'Air Purifier', price: 5999, rating: 4.7, image: '💨', category: 'home' },
  ]

  const addToCart = (product: any) => {
    const existing = cart.find(item => item.id === product.id)
    if (existing) {
      setCart(cart.map(item => item.id === product.id ? { ...item, qty: item.qty + 1 } : item))
    } else {
      setCart([...cart, { ...product, qty: 1 }])
    }
  }

  const removeFromCart = (id: number) => {
    setCart(cart.filter(item => item.id !== id))
  }

  const total = cart.reduce((sum, item) => sum + item.price * item.qty, 0)
  const filtered = category === 'all' ? products : products.filter(p => p.category === category)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">ShopNow</h1>
            <div className="hidden md:flex relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input placeholder="Search products..." className="pl-10 pr-4 py-2.5 w-80 bg-gray-100 rounded-xl outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2 hover:bg-gray-100 rounded-xl">
              <Heart className="w-6 h-6 text-gray-600" />
            </button>
            <button onClick={() => setShowCart(true)} className="relative p-2 hover:bg-gray-100 rounded-xl">
              <ShoppingCart className="w-6 h-6 text-gray-600" />
              {cart.length > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-emerald-500 text-white text-xs rounded-full flex items-center justify-center">
                  {cart.reduce((sum, item) => sum + item.qty, 0)}
                </span>
              )}
            </button>
            <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
              <User className="w-5 h-5 text-emerald-600" />
            </div>
          </div>
        </div>
      </header>

      {/* Categories */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-3 overflow-x-auto pb-2">
          {[
            { id: 'all', label: 'All', icon: '🛍️' },
            { id: 'electronics', label: 'Electronics', icon: '📱' },
            { id: 'fashion', label: 'Fashion', icon: '👔' },
            { id: 'home', label: 'Home', icon: '🏠' },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setCategory(cat.id)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl whitespace-nowrap transition-all ${
                category === cat.id
                  ? 'bg-emerald-500 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              <span>{cat.icon}</span> {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Products Grid */}
      <div className="max-w-7xl mx-auto px-4 pb-20">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {filtered.map((product) => (
            <div key={product.id} className="bg-white rounded-2xl p-4 shadow-sm hover:shadow-lg transition-shadow">
              <div className="h-32 bg-gradient-to-br from-gray-100 to-gray-50 rounded-xl mb-4 flex items-center justify-center text-5xl">
                {product.image}
              </div>
              <h3 className="font-semibold text-gray-800 mb-1">{product.name}</h3>
              <div className="flex items-center gap-1 mb-2">
                <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                <span className="text-sm text-gray-500">{product.rating}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xl font-bold text-emerald-600">₹{product.price.toLocaleString()}</span>
                <button
                  onClick={() => addToCart(product)}
                  className="w-10 h-10 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl flex items-center justify-center transition-colors"
                >
                  <Plus className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cart Sidebar */}
      {showCart && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowCart(false)} />
          <div className="absolute right-0 top-0 bottom-0 w-full max-w-md bg-white shadow-xl">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold">Shopping Cart ({cart.length})</h2>
              <button onClick={() => setShowCart(false)} className="p-2 hover:bg-gray-100 rounded-xl">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 flex-1 overflow-y-auto max-h-[calc(100vh-250px)]">
              {cart.length === 0 ? (
                <div className="text-center py-12">
                  <ShoppingCart className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">Your cart is empty</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {cart.map((item) => (
                    <div key={item.id} className="flex gap-4 p-4 bg-gray-50 rounded-xl">
                      <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center text-3xl">
                        {item.image}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-800">{item.name}</h4>
                        <p className="text-emerald-600 font-semibold">₹{item.price.toLocaleString()} × {item.qty}</p>
                      </div>
                      <button onClick={() => removeFromCart(item.id)} className="p-2 hover:bg-white rounded-xl">
                        <Trash2 className="w-5 h-5 text-gray-400" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {cart.length > 0 && (
              <div className="p-6 border-t bg-gray-50">
                <div className="flex justify-between mb-4">
                  <span className="text-gray-600">Subtotal</span>
                  <span className="text-xl font-bold">₹{total.toLocaleString()}</span>
                </div>
                <button className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-semibold transition-colors">
                  Proceed to Checkout
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// =============== KANBAN/PROJECT MANAGEMENT DEMO ===============
function KanbanDemo() {
  const [columns, setColumns] = useState([
    { id: 'todo', title: 'To Do', color: 'gray', tasks: [
      { id: 1, title: 'Design system updates', priority: 'high', assignee: 'A' },
      { id: 2, title: 'API documentation', priority: 'medium', assignee: 'B' },
    ]},
    { id: 'progress', title: 'In Progress', color: 'blue', tasks: [
      { id: 3, title: 'User authentication', priority: 'high', assignee: 'C' },
      { id: 4, title: 'Dashboard UI', priority: 'low', assignee: 'A' },
    ]},
    { id: 'review', title: 'In Review', color: 'amber', tasks: [
      { id: 5, title: 'Payment integration', priority: 'high', assignee: 'B' },
    ]},
    { id: 'done', title: 'Done', color: 'green', tasks: [
      { id: 6, title: 'Project setup', priority: 'low', assignee: 'C' },
      { id: 7, title: 'Database schema', priority: 'medium', assignee: 'A' },
    ]},
  ])
  const [newTask, setNewTask] = useState('')
  const [addingTo, setAddingTo] = useState<string | null>(null)

  const addTask = (columnId: string) => {
    if (!newTask.trim()) return
    setColumns(columns.map(col =>
      col.id === columnId
        ? { ...col, tasks: [...col.tasks, { id: Date.now(), title: newTask, priority: 'medium', assignee: 'A' }] }
        : col
    ))
    setNewTask('')
    setAddingTo(null)
  }

  const priorityColors: Record<string, string> = {
    high: 'bg-red-100 text-red-600',
    medium: 'bg-amber-100 text-amber-600',
    low: 'bg-green-100 text-green-600'
  }

  const columnColors: Record<string, { bg: string, border: string, dot: string }> = {
    gray: { bg: 'bg-gray-50', border: 'border-gray-200', dot: 'bg-gray-400' },
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-500' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500' },
    green: { bg: 'bg-green-50', border: 'border-green-200', dot: 'bg-green-500' },
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-full mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-xl text-gray-800">TaskBoard Pro</h1>
              <p className="text-sm text-gray-500">Sprint 24 • 12 tasks</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex -space-x-2">
              {['A', 'B', 'C'].map((letter, i) => (
                <div key={i} className={`w-9 h-9 rounded-full border-2 border-white flex items-center justify-center text-white text-sm font-medium ${
                  i === 0 ? 'bg-violet-500' : i === 1 ? 'bg-blue-500' : 'bg-emerald-500'
                }`}>
                  {letter}
                </div>
              ))}
              <div className="w-9 h-9 rounded-full border-2 border-white bg-gray-200 flex items-center justify-center text-gray-600 text-sm">
                +2
              </div>
            </div>
            <button className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-xl text-sm font-medium transition-colors flex items-center gap-2">
              <Plus className="w-4 h-4" /> Add Task
            </button>
          </div>
        </div>
      </header>

      {/* Board */}
      <div className="p-6 overflow-x-auto">
        <div className="flex gap-6 min-w-max">
          {columns.map((column) => {
            const colors = columnColors[column.color]
            return (
              <div key={column.id} className="w-80 flex-shrink-0">
                <div className={`${colors.bg} ${colors.border} border rounded-xl p-4 mb-4`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${colors.dot}`} />
                      <span className="font-semibold text-gray-700">{column.title}</span>
                    </div>
                    <span className="text-sm bg-white px-2.5 py-1 rounded-full text-gray-500 font-medium">
                      {column.tasks.length}
                    </span>
                  </div>
                </div>
                <div className="space-y-3">
                  {column.tasks.map((task) => (
                    <div key={task.id} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-pointer group">
                      <div className="flex items-start justify-between mb-3">
                        <h4 className="font-medium text-gray-800">{task.title}</h4>
                        <button className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-100 rounded transition-all">
                          <MoreVertical className="w-4 h-4 text-gray-400" />
                        </button>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className={`text-xs px-2 py-1 rounded-full font-medium ${priorityColors[task.priority]}`}>
                          {task.priority}
                        </span>
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-medium ${
                          task.assignee === 'A' ? 'bg-violet-500' : task.assignee === 'B' ? 'bg-blue-500' : 'bg-emerald-500'
                        }`}>
                          {task.assignee}
                        </div>
                      </div>
                    </div>
                  ))}
                  {addingTo === column.id ? (
                    <div className="bg-white p-4 rounded-xl shadow-sm border-2 border-indigo-300">
                      <input
                        value={newTask}
                        onChange={(e) => setNewTask(e.target.value)}
                        placeholder="Task title..."
                        className="w-full text-sm outline-none mb-3"
                        autoFocus
                        onKeyPress={(e) => e.key === 'Enter' && addTask(column.id)}
                      />
                      <div className="flex gap-2">
                        <button onClick={() => addTask(column.id)} className="flex-1 py-2 bg-indigo-500 text-white rounded-lg text-sm font-medium">
                          Add
                        </button>
                        <button onClick={() => setAddingTo(null)} className="flex-1 py-2 bg-gray-100 text-gray-600 rounded-lg text-sm font-medium">
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setAddingTo(column.id)}
                      className="w-full py-3 border-2 border-dashed border-gray-200 rounded-xl text-sm text-gray-400 hover:border-indigo-300 hover:text-indigo-500 transition-colors flex items-center justify-center gap-2"
                    >
                      <Plus className="w-4 h-4" /> Add Task
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// =============== CHAT APP DEMO ===============
function ChatDemo() {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([
    { id: 1, from: 'other', name: 'Sarah Wilson', text: 'Hey! How are you?', time: '10:30 AM', avatar: '👩' },
    { id: 2, from: 'me', text: "I'm good! Working on the new project", time: '10:31 AM' },
    { id: 3, from: 'other', name: 'Sarah Wilson', text: 'Nice! How is it going?', time: '10:32 AM', avatar: '👩' },
    { id: 4, from: 'me', text: 'Pretty well! Almost done with the frontend', time: '10:33 AM' },
    { id: 5, from: 'other', name: 'Sarah Wilson', text: "That's great! Let me know if you need any help with the backend", time: '10:34 AM', avatar: '👩' },
  ])
  const [activeChat, setActiveChat] = useState(0)

  const chats = [
    { name: 'Sarah Wilson', avatar: '👩', lastMsg: "That's great! Let me know...", time: '10:34 AM', unread: 0, online: true },
    { name: 'Team Project', avatar: '👥', lastMsg: 'John: Meeting at 3 PM', time: '10:15 AM', unread: 3, online: false },
    { name: 'Mike Johnson', avatar: '👨', lastMsg: 'See you tomorrow!', time: 'Yesterday', unread: 0, online: true },
    { name: 'Design Team', avatar: '🎨', lastMsg: 'New mockups uploaded', time: 'Yesterday', unread: 5, online: false },
  ]

  const sendMessage = () => {
    if (message.trim()) {
      setMessages([...messages, { id: Date.now(), from: 'me', text: message, time: 'Now' }])
      setMessage('')
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-bold text-gray-800">Messages</h1>
            <button className="p-2 hover:bg-gray-100 rounded-xl">
              <Edit className="w-5 h-5 text-gray-500" />
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input placeholder="Search messages..." className="w-full pl-10 pr-4 py-2.5 bg-gray-100 rounded-xl text-sm outline-none" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {chats.map((chat, i) => (
            <div
              key={i}
              onClick={() => setActiveChat(i)}
              className={`flex items-center gap-3 p-4 cursor-pointer transition-colors ${
                activeChat === i ? 'bg-emerald-50' : 'hover:bg-gray-50'
              }`}
            >
              <div className="relative">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-2xl">
                  {chat.avatar}
                </div>
                {chat.online && (
                  <div className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-green-500 border-2 border-white rounded-full" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-800">{chat.name}</span>
                  <span className="text-xs text-gray-400">{chat.time}</span>
                </div>
                <p className="text-sm text-gray-500 truncate">{chat.lastMsg}</p>
              </div>
              {chat.unread > 0 && (
                <div className="w-5 h-5 bg-emerald-500 text-white text-xs rounded-full flex items-center justify-center">
                  {chat.unread}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center text-xl">
                {chats[activeChat].avatar}
              </div>
              {chats[activeChat].online && (
                <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full" />
              )}
            </div>
            <div>
              <h2 className="font-semibold text-gray-800">{chats[activeChat].name}</h2>
              <p className="text-sm text-green-500">{chats[activeChat].online ? 'Online' : 'Offline'}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2.5 hover:bg-gray-100 rounded-xl">
              <Phone className="w-5 h-5 text-gray-500" />
            </button>
            <button className="p-2.5 hover:bg-gray-100 rounded-xl">
              <Video className="w-5 h-5 text-gray-500" />
            </button>
            <button className="p-2.5 hover:bg-gray-100 rounded-xl">
              <MoreVertical className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.from === 'me' ? 'justify-end' : 'justify-start'}`}>
              {msg.from === 'other' && (
                <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-lg mr-2 flex-shrink-0">
                  {msg.avatar}
                </div>
              )}
              <div className={`max-w-[70%] ${msg.from === 'me' ? 'order-1' : ''}`}>
                <div className={`p-4 rounded-2xl ${
                  msg.from === 'me'
                    ? 'bg-emerald-500 text-white rounded-br-md'
                    : 'bg-white shadow-sm rounded-bl-md'
                }`}>
                  <p className="text-sm">{msg.text}</p>
                </div>
                <p className={`text-xs mt-1 ${msg.from === 'me' ? 'text-right' : ''} text-gray-400`}>{msg.time}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-white p-4 border-t border-gray-200">
          <div className="flex items-center gap-3">
            <button className="p-2.5 hover:bg-gray-100 rounded-xl">
              <Paperclip className="w-5 h-5 text-gray-500" />
            </button>
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type a message..."
              className="flex-1 px-4 py-3 bg-gray-100 rounded-xl outline-none text-sm"
            />
            <button className="p-2.5 hover:bg-gray-100 rounded-xl">
              <Smile className="w-5 h-5 text-gray-500" />
            </button>
            <button
              onClick={sendMessage}
              className="w-11 h-11 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl flex items-center justify-center transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============== DASHBOARD DEMO ===============
function DashboardDemo() {
  const stats = [
    { label: 'Total Revenue', value: '₹24,50,000', change: '+12.5%', icon: DollarSign, color: 'from-emerald-500 to-green-600' },
    { label: 'Total Users', value: '12,345', change: '+8.2%', icon: Users, color: 'from-blue-500 to-cyan-600' },
    { label: 'Total Orders', value: '4,567', change: '+15.3%', icon: ShoppingBag, color: 'from-purple-500 to-pink-600' },
    { label: 'Growth Rate', value: '+23.5%', change: '+4.1%', icon: TrendingUp, color: 'from-orange-500 to-amber-600' },
  ]

  const recentOrders = [
    { id: '#ORD-001', customer: 'John Doe', product: 'Wireless Earbuds', amount: '₹2,999', status: 'Delivered' },
    { id: '#ORD-002', customer: 'Jane Smith', product: 'Smart Watch', amount: '₹4,999', status: 'Processing' },
    { id: '#ORD-003', customer: 'Bob Wilson', product: 'Power Bank', amount: '₹1,499', status: 'Shipped' },
    { id: '#ORD-004', customer: 'Alice Brown', product: 'USB Hub', amount: '₹1,999', status: 'Pending' },
  ]

  const statusColors: Record<string, string> = {
    Delivered: 'bg-green-100 text-green-700',
    Processing: 'bg-blue-100 text-blue-700',
    Shipped: 'bg-purple-100 text-purple-700',
    Pending: 'bg-amber-100 text-amber-700',
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 bottom-0 w-64 bg-slate-900 text-white p-6">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 flex items-center justify-center">
            <BarChart3 className="w-5 h-5" />
          </div>
          <span className="font-bold text-lg">Analytics Pro</span>
        </div>
        <nav className="space-y-2">
          {[
            { icon: Home, label: 'Dashboard', active: true },
            { icon: BarChart3, label: 'Analytics' },
            { icon: Users, label: 'Customers' },
            { icon: ShoppingBag, label: 'Orders' },
            { icon: Package, label: 'Products' },
            { icon: Settings, label: 'Settings' },
          ].map((item, i) => (
            <button
              key={i}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                item.active ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
            <p className="text-gray-500">Welcome back, Admin</p>
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2.5 hover:bg-white rounded-xl relative">
              <Bell className="w-6 h-6 text-gray-600" />
              <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full" />
            </button>
            <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-xl">
              <div className="w-9 h-9 bg-blue-100 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">Admin User</p>
                <p className="text-xs text-gray-500">admin@example.com</p>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-6 mb-8">
          {stats.map((stat, i) => (
            <div key={i} className="bg-white p-6 rounded-2xl shadow-sm">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-r ${stat.color} flex items-center justify-center mb-4`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-800 mb-1">{stat.value}</p>
              <p className="text-sm text-green-600 font-medium">{stat.change} from last month</p>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-3 gap-6 mb-8">
          <div className="col-span-2 bg-white p-6 rounded-2xl shadow-sm">
            <h3 className="font-semibold text-gray-800 mb-6">Revenue Overview</h3>
            <div className="flex items-end gap-4 h-48">
              {[40, 65, 45, 80, 55, 90, 70, 85, 60, 75, 50, 95].map((h, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-2">
                  <div
                    className="w-full bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t-lg transition-all hover:opacity-80"
                    style={{ height: `${h}%` }}
                  />
                  <span className="text-xs text-gray-400">{['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'][i]}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm">
            <h3 className="font-semibold text-gray-800 mb-6">Traffic Sources</h3>
            <div className="space-y-4">
              {[
                { source: 'Direct', value: 45, color: 'bg-blue-500' },
                { source: 'Organic', value: 30, color: 'bg-emerald-500' },
                { source: 'Social', value: 15, color: 'bg-purple-500' },
                { source: 'Referral', value: 10, color: 'bg-amber-500' },
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">{item.source}</span>
                    <span className="font-medium text-gray-800">{item.value}%</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.value}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Orders */}
        <div className="bg-white rounded-2xl shadow-sm">
          <div className="p-6 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Recent Orders</h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left p-4 text-sm font-medium text-gray-500">Order ID</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Customer</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Product</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Amount</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody>
              {recentOrders.map((order, i) => (
                <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="p-4 text-sm font-medium text-gray-800">{order.id}</td>
                  <td className="p-4 text-sm text-gray-600">{order.customer}</td>
                  <td className="p-4 text-sm text-gray-600">{order.product}</td>
                  <td className="p-4 text-sm font-medium text-gray-800">{order.amount}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[order.status]}`}>
                      {order.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}

// =============== TODO APP DEMO ===============
function TodoDemo() {
  const [todos, setTodos] = useState([
    { id: 1, text: 'Complete project report', done: true, priority: 'high', category: 'work' },
    { id: 2, text: 'Review pull requests', done: false, priority: 'high', category: 'work' },
    { id: 3, text: 'Team meeting at 3 PM', done: false, priority: 'medium', category: 'work' },
    { id: 4, text: 'Buy groceries', done: false, priority: 'low', category: 'personal' },
    { id: 5, text: 'Go to the gym', done: true, priority: 'medium', category: 'personal' },
  ])
  const [newTodo, setNewTodo] = useState('')
  const [filter, setFilter] = useState('all')

  const addTodo = () => {
    if (newTodo.trim()) {
      setTodos([...todos, { id: Date.now(), text: newTodo, done: false, priority: 'medium', category: 'personal' }])
      setNewTodo('')
    }
  }

  const toggleTodo = (id: number) => {
    setTodos(todos.map(t => t.id === id ? { ...t, done: !t.done } : t))
  }

  const deleteTodo = (id: number) => {
    setTodos(todos.filter(t => t.id !== id))
  }

  const filtered = filter === 'all' ? todos : filter === 'active' ? todos.filter(t => !t.done) : todos.filter(t => t.done)

  const priorityColors: Record<string, string> = {
    high: 'border-red-400',
    medium: 'border-amber-400',
    low: 'border-green-400'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700">
      <div className="max-w-2xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center text-white mb-10">
          <h1 className="text-4xl font-bold mb-2">My Tasks</h1>
          <p className="text-violet-200">
            {todos.filter(t => !t.done).length} tasks remaining • {todos.filter(t => t.done).length} completed
          </p>
        </div>

        {/* Add Task */}
        <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 mb-6">
          <div className="flex gap-3">
            <input
              value={newTodo}
              onChange={(e) => setNewTodo(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addTodo()}
              placeholder="Add a new task..."
              className="flex-1 px-5 py-4 bg-white/10 border border-white/20 rounded-xl text-white placeholder:text-white/50 outline-none focus:border-white/40"
            />
            <button
              onClick={addTodo}
              className="px-6 py-4 bg-white text-violet-600 rounded-xl font-semibold hover:bg-violet-50 transition-colors"
            >
              <Plus className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-6">
          {['all', 'active', 'completed'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-5 py-2.5 rounded-xl font-medium capitalize transition-all ${
                filter === f
                  ? 'bg-white text-violet-600'
                  : 'bg-white/10 text-white hover:bg-white/20'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Tasks */}
        <div className="space-y-3">
          {filtered.map((todo) => (
            <div
              key={todo.id}
              className={`flex items-center gap-4 p-5 bg-white rounded-xl shadow-sm border-l-4 ${priorityColors[todo.priority]} transition-all ${
                todo.done ? 'opacity-60' : ''
              }`}
            >
              <button
                onClick={() => toggleTodo(todo.id)}
                className={`w-7 h-7 rounded-full border-2 flex items-center justify-center transition-colors ${
                  todo.done
                    ? 'bg-violet-500 border-violet-500'
                    : 'border-gray-300 hover:border-violet-400'
                }`}
              >
                {todo.done && <Check className="w-4 h-4 text-white" />}
              </button>
              <div className="flex-1">
                <span className={`font-medium ${todo.done ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                  {todo.text}
                </span>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    todo.category === 'work' ? 'bg-blue-100 text-blue-600' : 'bg-green-100 text-green-600'
                  }`}>
                    {todo.category}
                  </span>
                </div>
              </div>
              <button
                onClick={() => deleteTodo(todo.id)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Trash2 className="w-5 h-5 text-gray-400" />
              </button>
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12 text-white/60">
            <CheckCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p>No tasks found</p>
          </div>
        )}
      </div>
    </div>
  )
}

// =============== EXPENSE TRACKER DEMO ===============
function ExpenseDemo() {
  const [transactions] = useState([
    { id: 1, name: 'Salary', amount: 50000, type: 'income', category: 'salary', date: 'Today' },
    { id: 2, name: 'Groceries', amount: -2500, type: 'expense', category: 'food', date: 'Today' },
    { id: 3, name: 'Netflix', amount: -649, type: 'expense', category: 'entertainment', date: 'Yesterday' },
    { id: 4, name: 'Electricity Bill', amount: -1200, type: 'expense', category: 'utilities', date: 'Yesterday' },
    { id: 5, name: 'Freelance', amount: 15000, type: 'income', category: 'freelance', date: '2 days ago' },
  ])

  const totalIncome = transactions.filter(t => t.type === 'income').reduce((sum, t) => sum + t.amount, 0)
  const totalExpense = Math.abs(transactions.filter(t => t.type === 'expense').reduce((sum, t) => sum + t.amount, 0))
  const balance = totalIncome - totalExpense

  const categoryIcons: Record<string, any> = {
    salary: Wallet,
    food: ShoppingCart,
    entertainment: Video,
    utilities: Building,
    freelance: Briefcase,
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-500 via-green-500 to-teal-600">
      {/* Header */}
      <div className="px-6 py-10 text-white text-center">
        <p className="text-emerald-100 mb-2">Total Balance</p>
        <h1 className="text-5xl font-bold mb-6">₹{balance.toLocaleString()}</h1>
        <div className="flex justify-center gap-12">
          <div className="text-center">
            <div className="flex items-center gap-2 justify-center mb-1">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-4 h-4" />
              </div>
              <span className="text-sm text-emerald-100">Income</span>
            </div>
            <p className="text-2xl font-semibold">₹{totalIncome.toLocaleString()}</p>
          </div>
          <div className="text-center">
            <div className="flex items-center gap-2 justify-center mb-1">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <Receipt className="w-4 h-4" />
              </div>
              <span className="text-sm text-emerald-100">Expense</span>
            </div>
            <p className="text-2xl font-semibold">₹{totalExpense.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-t-[2.5rem] min-h-[60vh] px-6 py-8">
        {/* Quick Actions */}
        <div className="flex gap-4 mb-8">
          <button className="flex-1 py-4 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl font-semibold flex items-center justify-center gap-2 transition-colors">
            <Plus className="w-5 h-5" /> Add Income
          </button>
          <button className="flex-1 py-4 bg-red-500 hover:bg-red-600 text-white rounded-2xl font-semibold flex items-center justify-center gap-2 transition-colors">
            <Plus className="w-5 h-5" /> Add Expense
          </button>
        </div>

        {/* Spending Categories */}
        <div className="mb-8">
          <h3 className="font-semibold text-gray-800 mb-4">Spending by Category</h3>
          <div className="grid grid-cols-4 gap-3">
            {[
              { name: 'Food', amount: 2500, icon: '🍔', color: 'bg-orange-100' },
              { name: 'Bills', amount: 1200, icon: '📄', color: 'bg-blue-100' },
              { name: 'Entertainment', amount: 649, icon: '🎬', color: 'bg-purple-100' },
              { name: 'Shopping', amount: 0, icon: '🛍️', color: 'bg-pink-100' },
            ].map((cat, i) => (
              <div key={i} className={`${cat.color} p-4 rounded-2xl text-center`}>
                <div className="text-2xl mb-2">{cat.icon}</div>
                <p className="text-sm text-gray-600">{cat.name}</p>
                <p className="font-semibold text-gray-800">₹{cat.amount.toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Transactions */}
        <div>
          <h3 className="font-semibold text-gray-800 mb-4">Recent Transactions</h3>
          <div className="space-y-3">
            {transactions.map((t) => {
              const Icon = categoryIcons[t.category] || Wallet
              return (
                <div key={t.id} className="flex items-center gap-4 p-4 bg-gray-50 rounded-2xl">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    t.type === 'income' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                  }`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-800">{t.name}</p>
                    <p className="text-sm text-gray-400">{t.date}</p>
                  </div>
                  <p className={`font-bold text-lg ${t.amount > 0 ? 'text-green-600' : 'text-red-500'}`}>
                    {t.amount > 0 ? '+' : ''}₹{Math.abs(t.amount).toLocaleString()}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

// =============== RESTAURANT DEMO ===============
function RestaurantDemo() {
  const [tab, setTab] = useState('menu')
  const [cart, setCart] = useState<any[]>([])

  const menuItems = [
    { id: 1, name: 'Margherita Pizza', price: 399, desc: 'Fresh tomatoes, mozzarella, basil', image: '🍕' },
    { id: 2, name: 'Pasta Carbonara', price: 449, desc: 'Creamy bacon pasta with parmesan', image: '🍝' },
    { id: 3, name: 'Caesar Salad', price: 299, desc: 'Crisp romaine, croutons, parmesan', image: '🥗' },
    { id: 4, name: 'Tiramisu', price: 249, desc: 'Classic Italian coffee dessert', image: '🍰' },
    { id: 5, name: 'Bruschetta', price: 199, desc: 'Toasted bread with tomatoes & herbs', image: '🥖' },
    { id: 6, name: 'Gelato', price: 149, desc: 'Italian ice cream - 3 scoops', image: '🍨' },
  ]

  const addToCart = (item: any) => {
    const existing = cart.find(c => c.id === item.id)
    if (existing) {
      setCart(cart.map(c => c.id === item.id ? { ...c, qty: c.qty + 1 } : c))
    } else {
      setCart([...cart, { ...item, qty: 1 }])
    }
  }

  return (
    <div className="min-h-screen bg-amber-50">
      {/* Hero */}
      <div className="relative h-64 bg-gradient-to-br from-orange-500 via-red-500 to-pink-500">
        <div className="absolute inset-0 bg-black/30" />
        <div className="relative h-full flex flex-col items-center justify-center text-white text-center px-4">
          <h1 className="text-4xl font-serif font-bold mb-2">La Bella Italia</h1>
          <p className="text-orange-100 mb-4">Authentic Italian Cuisine Since 1985</p>
          <div className="flex items-center gap-6 text-sm">
            <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> Downtown</span>
            <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> 11AM - 10PM</span>
            <span className="flex items-center gap-1"><Star className="w-4 h-4 fill-current" /> 4.8</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="sticky top-0 z-40 bg-white border-b border-orange-200">
        <div className="flex">
          {['menu', 'reserve', 'reviews', 'about'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-4 text-sm font-medium capitalize transition-colors ${
                tab === t
                  ? 'text-orange-600 border-b-2 border-orange-500'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {tab === 'menu' && (
          <div>
            <h2 className="text-2xl font-serif font-bold text-gray-800 mb-6">Our Menu</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {menuItems.map((item) => (
                <div key={item.id} className="flex items-center gap-4 p-4 bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow">
                  <div className="w-20 h-20 bg-gradient-to-br from-orange-100 to-red-100 rounded-xl flex items-center justify-center text-4xl">
                    {item.image}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-800">{item.name}</h3>
                    <p className="text-sm text-gray-500 mb-2">{item.desc}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-orange-600">₹{item.price}</span>
                      <button
                        onClick={() => addToCart(item)}
                        className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm rounded-xl font-medium transition-colors"
                      >
                        Add to Cart
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'reserve' && (
          <div className="max-w-md mx-auto">
            <h2 className="text-2xl font-serif font-bold text-gray-800 mb-6 text-center">Make a Reservation</h2>
            <div className="bg-white p-6 rounded-2xl shadow-sm space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:border-orange-500" placeholder="Your name" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                  <input type="date" className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:border-orange-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Time</label>
                  <input type="time" className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:border-orange-500" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Number of Guests</label>
                <select className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:border-orange-500">
                  {[1, 2, 3, 4, 5, 6, 7, 8].map(n => <option key={n}>{n} {n === 1 ? 'Guest' : 'Guests'}</option>)}
                </select>
              </div>
              <button className="w-full py-4 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-semibold transition-colors">
                Reserve Table
              </button>
            </div>
          </div>
        )}

        {tab === 'reviews' && (
          <div>
            <h2 className="text-2xl font-serif font-bold text-gray-800 mb-6">Customer Reviews</h2>
            <div className="space-y-4">
              {[
                { name: 'John D.', rating: 5, text: 'Amazing food! The pasta was perfectly cooked.', date: '2 days ago' },
                { name: 'Sarah M.', rating: 5, text: 'Best Italian restaurant in town. Love the ambiance!', date: '1 week ago' },
                { name: 'Mike R.', rating: 4, text: 'Great pizza, slightly slow service but worth the wait.', date: '2 weeks ago' },
              ].map((review, i) => (
                <div key={i} className="bg-white p-5 rounded-2xl shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 font-semibold">
                        {review.name[0]}
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{review.name}</p>
                        <p className="text-xs text-gray-400">{review.date}</p>
                      </div>
                    </div>
                    <div className="flex">
                      {Array.from({ length: review.rating }).map((_, j) => (
                        <Star key={j} className="w-4 h-4 text-amber-400 fill-amber-400" />
                      ))}
                    </div>
                  </div>
                  <p className="text-gray-600">{review.text}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cart Floating Button */}
      {cart.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-orange-500 text-white px-6 py-4 rounded-2xl shadow-lg flex items-center gap-4">
          <ShoppingCart className="w-6 h-6" />
          <span className="font-semibold">{cart.reduce((sum, c) => sum + c.qty, 0)} items</span>
          <span className="text-orange-200">|</span>
          <span className="font-bold">₹{cart.reduce((sum, c) => sum + c.price * c.qty, 0)}</span>
          <button className="ml-4 px-4 py-2 bg-white text-orange-600 rounded-xl font-semibold">
            View Cart
          </button>
        </div>
      )}
    </div>
  )
}

// =============== MUSIC PLAYER DEMO ===============
function MusicDemo() {
  const [playing, setPlaying] = useState(false)
  const [currentTrack, setCurrentTrack] = useState(0)
  const [shuffle, setShuffle] = useState(false)
  const [repeat, setRepeat] = useState(false)

  const tracks = [
    { title: 'Shape of You', artist: 'Ed Sheeran', duration: '3:53', color: 'from-orange-500 to-red-500' },
    { title: 'Blinding Lights', artist: 'The Weeknd', duration: '3:20', color: 'from-red-500 to-pink-500' },
    { title: 'Dance Monkey', artist: 'Tones and I', duration: '3:29', color: 'from-purple-500 to-pink-500' },
    { title: 'Someone You Loved', artist: 'Lewis Capaldi', duration: '3:02', color: 'from-blue-500 to-purple-500' },
    { title: 'Bad Guy', artist: 'Billie Eilish', duration: '3:14', color: 'from-green-500 to-teal-500' },
  ]

  const current = tracks[currentTrack]

  return (
    <div className={`min-h-screen bg-gradient-to-b ${current.color} via-slate-900 to-black text-white`}>
      {/* Header */}
      <div className="flex items-center justify-between p-6">
        <button className="p-2 hover:bg-white/10 rounded-xl">
          <ChevronDown className="w-6 h-6" />
        </button>
        <div className="text-center">
          <p className="text-xs text-white/60 uppercase tracking-wider">Now Playing</p>
          <p className="font-medium">Top Hits 2024</p>
        </div>
        <button className="p-2 hover:bg-white/10 rounded-xl">
          <MoreVertical className="w-6 h-6" />
        </button>
      </div>

      {/* Album Art */}
      <div className="px-12 py-8">
        <div className={`aspect-square bg-gradient-to-br ${current.color} rounded-3xl shadow-2xl flex items-center justify-center`}>
          <Music className="w-32 h-32 text-white/30" />
        </div>
      </div>

      {/* Track Info */}
      <div className="px-8 text-center mb-8">
        <h1 className="text-2xl font-bold mb-1">{current.title}</h1>
        <p className="text-white/60">{current.artist}</p>
      </div>

      {/* Progress Bar */}
      <div className="px-8 mb-8">
        <div className="h-1 bg-white/20 rounded-full overflow-hidden">
          <div className="h-full w-1/3 bg-white rounded-full" />
        </div>
        <div className="flex justify-between text-xs text-white/60 mt-2">
          <span>1:18</span>
          <span>{current.duration}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="px-8">
        <div className="flex items-center justify-center gap-8 mb-8">
          <button onClick={() => setShuffle(!shuffle)} className={`p-3 rounded-full ${shuffle ? 'text-green-400' : 'text-white/60 hover:text-white'}`}>
            <Shuffle className="w-6 h-6" />
          </button>
          <button onClick={() => setCurrentTrack(Math.max(0, currentTrack - 1))} className="p-3 text-white/60 hover:text-white">
            <SkipBack className="w-8 h-8" />
          </button>
          <button
            onClick={() => setPlaying(!playing)}
            className="w-20 h-20 bg-white rounded-full flex items-center justify-center hover:scale-105 transition-transform shadow-xl"
          >
            {playing ? (
              <Pause className="w-8 h-8 text-black" />
            ) : (
              <Play className="w-8 h-8 text-black ml-1" />
            )}
          </button>
          <button onClick={() => setCurrentTrack(Math.min(tracks.length - 1, currentTrack + 1))} className="p-3 text-white/60 hover:text-white">
            <SkipForward className="w-8 h-8" />
          </button>
          <button onClick={() => setRepeat(!repeat)} className={`p-3 rounded-full ${repeat ? 'text-green-400' : 'text-white/60 hover:text-white'}`}>
            <Repeat className="w-6 h-6" />
          </button>
        </div>

        {/* Volume */}
        <div className="flex items-center gap-4 justify-center">
          <Volume2 className="w-5 h-5 text-white/60" />
          <div className="w-32 h-1 bg-white/20 rounded-full overflow-hidden">
            <div className="h-full w-2/3 bg-white rounded-full" />
          </div>
        </div>
      </div>

      {/* Queue */}
      <div className="mt-12 px-6 pb-8">
        <h3 className="text-sm font-semibold text-white/60 mb-4">Up Next</h3>
        <div className="space-y-2">
          {tracks.map((track, i) => (
            <button
              key={i}
              onClick={() => setCurrentTrack(i)}
              className={`w-full flex items-center gap-4 p-3 rounded-xl transition-colors ${
                i === currentTrack ? 'bg-white/20' : 'hover:bg-white/10'
              }`}
            >
              <div className={`w-12 h-12 bg-gradient-to-br ${track.color} rounded-xl flex items-center justify-center`}>
                <Music className="w-5 h-5 text-white/50" />
              </div>
              <div className="flex-1 text-left">
                <p className={`font-medium ${i === currentTrack ? 'text-white' : 'text-white/80'}`}>{track.title}</p>
                <p className="text-sm text-white/40">{track.artist}</p>
              </div>
              <span className="text-sm text-white/40">{track.duration}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// =============== HOSPITAL MANAGEMENT DEMO ===============
function HospitalDemo() {
  const [tab, setTab] = useState('dashboard')

  const stats = [
    { label: 'Total Patients', value: '1,234', icon: Users, color: 'from-blue-500 to-cyan-500' },
    { label: 'Doctors', value: '48', icon: Stethoscope, color: 'from-red-500 to-rose-500' },
    { label: "Today's Appointments", value: '67', icon: Calendar, color: 'from-amber-500 to-orange-500' },
    { label: 'Available Beds', value: '86/120', icon: Activity, color: 'from-emerald-500 to-green-500' },
  ]

  const appointments = [
    { id: 1, patient: 'John Doe', doctor: 'Dr. Smith', time: '09:00 AM', type: 'Checkup', status: 'Confirmed' },
    { id: 2, patient: 'Jane Wilson', doctor: 'Dr. Johnson', time: '10:30 AM', type: 'Follow-up', status: 'Waiting' },
    { id: 3, patient: 'Bob Brown', doctor: 'Dr. Williams', time: '11:00 AM', type: 'Consultation', status: 'In Progress' },
    { id: 4, patient: 'Alice Green', doctor: 'Dr. Davis', time: '02:00 PM', type: 'Lab Test', status: 'Scheduled' },
  ]

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-red-500 to-rose-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <Stethoscope className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold">City Hospital</h1>
                <p className="text-sm text-red-100">Patient Management System</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button className="p-2.5 hover:bg-white/10 rounded-xl relative">
                <Bell className="w-6 h-6" />
                <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-amber-400 rounded-full" />
              </button>
              <div className="flex items-center gap-3 bg-white/10 px-4 py-2 rounded-xl">
                <div className="w-9 h-9 bg-white/20 rounded-full flex items-center justify-center">
                  <User className="w-5 h-5" />
                </div>
                <span className="font-medium">Dr. Admin</span>
              </div>
            </div>
          </div>
        </div>
        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            {['dashboard', 'patients', 'appointments', 'doctors', 'billing'].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-6 py-3 rounded-t-xl capitalize font-medium transition-colors ${
                  tab === t ? 'bg-slate-100 text-gray-800' : 'text-white/70 hover:text-white hover:bg-white/10'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-6 mb-8">
          {stats.map((stat, i) => (
            <div key={i} className="bg-white p-6 rounded-2xl shadow-sm">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center mb-4`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-800">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Today's Appointments */}
        <div className="bg-white rounded-2xl shadow-sm">
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">Today's Appointments</h2>
            <button className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl text-sm font-medium transition-colors flex items-center gap-2">
              <Plus className="w-4 h-4" /> New Appointment
            </button>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left p-4 text-sm font-medium text-gray-500">Patient</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Doctor</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Time</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Type</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Status</th>
                <th className="text-left p-4 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((apt) => (
                <tr key={apt.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                        <User className="w-5 h-5 text-gray-500" />
                      </div>
                      <span className="font-medium text-gray-800">{apt.patient}</span>
                    </div>
                  </td>
                  <td className="p-4 text-gray-600">{apt.doctor}</td>
                  <td className="p-4 text-gray-600">{apt.time}</td>
                  <td className="p-4 text-gray-600">{apt.type}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      apt.status === 'Confirmed' ? 'bg-green-100 text-green-700' :
                      apt.status === 'Waiting' ? 'bg-amber-100 text-amber-700' :
                      apt.status === 'In Progress' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {apt.status}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <button className="p-2 hover:bg-gray-100 rounded-lg">
                        <Eye className="w-4 h-4 text-gray-500" />
                      </button>
                      <button className="p-2 hover:bg-gray-100 rounded-lg">
                        <Edit className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}

// =============== LIBRARY SYSTEM DEMO ===============
function LibraryDemo() {
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState('books')

  const books = [
    { id: 1, title: 'Clean Code', author: 'Robert C. Martin', isbn: '978-0132350884', status: 'Available', copies: 3 },
    { id: 2, title: 'The Pragmatic Programmer', author: 'David Thomas', isbn: '978-0135957059', status: 'Issued', copies: 0 },
    { id: 3, title: 'Design Patterns', author: 'Gang of Four', isbn: '978-0201633610', status: 'Available', copies: 2 },
    { id: 4, title: 'Introduction to Algorithms', author: 'Thomas Cormen', isbn: '978-0262033848', status: 'Available', copies: 5 },
    { id: 5, title: 'Structure and Interpretation', author: 'Harold Abelson', isbn: '978-0262510875', status: 'Reserved', copies: 1 },
  ]

  return (
    <div className="min-h-screen bg-amber-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-amber-500 to-orange-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <BookOpen className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Central Library</h1>
                <p className="text-sm text-amber-100">Management System</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/60" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search books, authors..."
                  className="pl-10 pr-4 py-2.5 w-80 bg-white/20 border border-white/30 rounded-xl text-white placeholder:text-white/60 outline-none"
                />
              </div>
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <User className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Total Books', value: '12,456' },
              { label: 'Active Members', value: '1,234' },
              { label: 'Books Issued', value: '456' },
              { label: 'Overdue', value: '23' },
            ].map((stat, i) => (
              <div key={i} className="bg-white/10 backdrop-blur p-4 rounded-xl">
                <p className="text-sm text-amber-100">{stat.label}</p>
                <p className="text-2xl font-bold">{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b border-amber-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            {['books', 'members', 'issued', 'returns'].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-6 py-4 capitalize font-medium transition-colors ${
                  tab === t
                    ? 'text-amber-600 border-b-2 border-amber-500'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-800">Book Catalog</h2>
          <button className="px-4 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-medium transition-colors flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add Book
          </button>
        </div>

        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-amber-50 border-b border-amber-100">
                <th className="text-left p-4 text-sm font-medium text-gray-600">Title</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Author</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">ISBN</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Status</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Copies</th>
                <th className="text-left p-4 text-sm font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {books.map((book) => (
                <tr key={book.id} className="border-b border-gray-50 hover:bg-amber-50/50">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-16 bg-gradient-to-br from-amber-400 to-orange-500 rounded-lg flex items-center justify-center">
                        <BookOpen className="w-5 h-5 text-white" />
                      </div>
                      <span className="font-medium text-gray-800">{book.title}</span>
                    </div>
                  </td>
                  <td className="p-4 text-gray-600">{book.author}</td>
                  <td className="p-4 text-gray-500 font-mono text-sm">{book.isbn}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      book.status === 'Available' ? 'bg-green-100 text-green-700' :
                      book.status === 'Issued' ? 'bg-red-100 text-red-700' :
                      'bg-amber-100 text-amber-700'
                    }`}>
                      {book.status}
                    </span>
                  </td>
                  <td className="p-4 text-gray-600">{book.copies}</td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <button className="px-3 py-1.5 bg-amber-100 hover:bg-amber-200 text-amber-700 rounded-lg text-sm font-medium transition-colors">
                        Issue
                      </button>
                      <button className="p-1.5 hover:bg-gray-100 rounded-lg">
                        <Edit className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}

// =============== EXAM PORTAL DEMO ===============
function ExamDemo() {
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [timeLeft, setTimeLeft] = useState(1800) // 30 minutes

  const questions = [
    { id: 1, question: 'What is the time complexity of binary search?', options: ['O(n)', 'O(log n)', 'O(n²)', 'O(1)'], correct: 1 },
    { id: 2, question: 'Which data structure uses FIFO principle?', options: ['Stack', 'Queue', 'Tree', 'Graph'], correct: 1 },
    { id: 3, question: 'What does SQL stand for?', options: ['Structured Query Language', 'Simple Query Language', 'Standard Query Logic', 'System Query Language'], correct: 0 },
    { id: 4, question: 'Which sorting algorithm has the best average case?', options: ['Bubble Sort', 'Quick Sort', 'Selection Sort', 'Insertion Sort'], correct: 1 },
    { id: 5, question: 'What is the purpose of DNS?', options: ['Data encryption', 'Domain name resolution', 'File transfer', 'Email routing'], correct: 1 },
  ]

  useEffect(() => {
    const timer = setInterval(() => setTimeLeft(t => Math.max(0, t - 1)), 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const current = questions[currentQuestion]

  return (
    <div className="min-h-screen bg-indigo-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold">Online Examination</h1>
              <p className="text-sm text-indigo-200">Computer Science - Final Exam</p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center bg-white/10 px-4 py-2 rounded-xl">
              <p className="text-xs text-indigo-200">Time Remaining</p>
              <p className={`text-xl font-bold font-mono ${timeLeft < 300 ? 'text-red-300' : ''}`}>
                {formatTime(timeLeft)}
              </p>
            </div>
            <button className="px-4 py-2 bg-white text-indigo-600 rounded-xl font-medium hover:bg-indigo-50 transition-colors">
              Submit Exam
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 flex gap-8">
        {/* Question Panel */}
        <div className="flex-1">
          <div className="bg-white p-8 rounded-2xl shadow-sm mb-6">
            <div className="flex items-center justify-between mb-6">
              <span className="px-4 py-2 bg-indigo-100 text-indigo-700 rounded-xl font-medium">
                Question {currentQuestion + 1} of {questions.length}
              </span>
              <span className="text-sm text-gray-500">Marks: 2</span>
            </div>
            <h2 className="text-xl font-medium text-gray-800 mb-8">{current.question}</h2>
            <div className="space-y-3">
              {current.options.map((option, i) => (
                <button
                  key={i}
                  onClick={() => setAnswers({ ...answers, [currentQuestion]: i })}
                  className={`w-full p-5 rounded-xl text-left flex items-center gap-4 transition-all ${
                    answers[currentQuestion] === i
                      ? 'bg-indigo-100 border-2 border-indigo-500'
                      : 'bg-gray-50 border-2 border-transparent hover:border-gray-200'
                  }`}
                >
                  <span className={`w-10 h-10 rounded-full flex items-center justify-center font-medium ${
                    answers[currentQuestion] === i
                      ? 'bg-indigo-500 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {String.fromCharCode(65 + i)}
                  </span>
                  <span className={answers[currentQuestion] === i ? 'text-indigo-700 font-medium' : 'text-gray-700'}>
                    {option}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex gap-4">
            <button
              onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
              disabled={currentQuestion === 0}
              className="flex-1 py-4 bg-gray-200 text-gray-700 rounded-xl font-medium disabled:opacity-50 hover:bg-gray-300 transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentQuestion(Math.min(questions.length - 1, currentQuestion + 1))}
              disabled={currentQuestion === questions.length - 1}
              className="flex-1 py-4 bg-indigo-600 text-white rounded-xl font-medium disabled:opacity-50 hover:bg-indigo-700 transition-colors"
            >
              Next
            </button>
          </div>
        </div>

        {/* Question Navigator */}
        <div className="w-72">
          <div className="bg-white p-6 rounded-2xl shadow-sm sticky top-24">
            <h3 className="font-semibold text-gray-800 mb-4">Question Navigator</h3>
            <div className="grid grid-cols-5 gap-2 mb-6">
              {questions.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentQuestion(i)}
                  className={`w-10 h-10 rounded-xl font-medium transition-colors ${
                    i === currentQuestion
                      ? 'bg-indigo-600 text-white'
                      : answers[i] !== undefined
                      ? 'bg-green-100 text-green-700 border border-green-300'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 bg-green-100 border border-green-300 rounded" />
                <span className="text-gray-600">Answered ({Object.keys(answers).length})</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 bg-gray-100 rounded" />
                <span className="text-gray-600">Not Answered ({questions.length - Object.keys(answers).length})</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 bg-indigo-600 rounded" />
                <span className="text-gray-600">Current</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============== DEMO ROUTER ===============
const DEMOS: Record<string, React.FC> = {
  'lp-1': SaaSLandingDemo,
  'aa-1': EcommerceDemo,
  'aa-2': KanbanDemo,
  'aa-3': ChatDemo,
  'bt-1': DashboardDemo,
  'pt-1': TodoDemo,
  'pt-2': ExpenseDemo,
  'lp-2': RestaurantDemo,
  'ma-2': MusicDemo,
  'cp-1': HospitalDemo,
  'cp-2': LibraryDemo,
  'cp-3': ExamDemo,
}

export default function DemoPage() {
  const params = useParams()
  const id = params.id as string

  const Demo = DEMOS[id]

  if (!Demo) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-4">Demo Not Found</h1>
          <p className="text-gray-400 mb-8">The demo you're looking for doesn't exist.</p>
          <Link href="/showcase" className="px-6 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition-colors">
            Back to Showcase
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Back Button */}
      <Link
        href="/showcase"
        className="fixed top-4 left-4 z-50 flex items-center gap-2 px-4 py-2 bg-black/50 backdrop-blur-xl text-white rounded-xl hover:bg-black/70 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Showcase
      </Link>

      {/* Demo Content */}
      <Demo />
    </div>
  )
}
