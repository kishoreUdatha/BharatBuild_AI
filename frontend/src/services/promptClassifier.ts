/**
 * Prompt Classifier Layer
 *
 * This is a critical layer that classifies user prompts before routing them
 * to the appropriate handler. Similar to what Bolt.new, Replit Agent, and Cursor use.
 *
 * The classifier uses both:
 * 1. Local pattern matching for instant responses (greetings, etc.)
 * 2. Backend AI-powered classification for complex prompts
 *
 * Intent Types:
 * - CHAT: Simple conversation, greetings, questions about the AI
 * - GENERATE: Create new project/code from scratch
 * - MODIFY: Edit/update existing code or project
 * - EXPLAIN: Explain code, concepts, or errors
 * - DEBUG: Fix bugs, troubleshoot issues
 * - DOCUMENT: Generate documentation, comments, README
 * - REFACTOR: Improve code structure without changing functionality
 */

import { apiConfig } from '@/config'

const API_BASE_URL = apiConfig.baseUrl

export type PromptIntent =
  | 'CHAT'
  | 'GENERATE'
  | 'MODIFY'
  | 'EXPLAIN'
  | 'DEBUG'
  | 'FIX'  // Auto-fix: user reports a problem, system collects all context automatically
  | 'DOCUMENT'
  | 'REFACTOR'

export interface ClassificationResult {
  intent: PromptIntent
  confidence: number // 0-1
  reasoning?: string
  entities: {
    projectType?: string      // e.g., "react app", "api", "website"
    technology?: string[]     // e.g., ["react", "typescript", "tailwind"]
    action?: string           // e.g., "create", "fix", "add"
    target?: string           // e.g., specific file, component, feature
  }
  requiresGeneration: boolean
  suggestedWorkflow?: 'bolt_standard' | 'bolt_instant' | 'chat_only'
  chatResponse?: string | null  // For CHAT intent, the response from AI
}

// Patterns for each intent type
const INTENT_PATTERNS: Record<PromptIntent, RegExp[]> = {
  CHAT: [
    /^(hi|hello|hey|hola|namaste|howdy|greetings|yo|sup)[\s!.,?]*$/i,
    /^(good\s+(morning|afternoon|evening|night))[\s!.,?]*$/i,
    /^(how\s+are\s+you|what's\s+up|whats\s+up|wassup)[\s!.,?]*$/i,
    /^(thanks|thank\s+you|thx|ty|cheers)[\s!.,?]*$/i,
    /^(bye|goodbye|see\s+you|cya|later|farewell)[\s!.,?]*$/i,
    /^(yes|no|ok|okay|sure|yep|nope|yeah|nah|yup)[\s!.,?]*$/i,
    /^(help|what\s+can\s+you\s+do|what\s+do\s+you\s+do|who\s+are\s+you)[\s!.,?]*$/i,
    /^(nice|cool|awesome|great|perfect|amazing)[\s!.,?]*$/i,
    /^(hmm|hm|um|uh|ah|oh)[\s!.,?]*$/i,
    /^[\s]*$/,  // Empty or whitespace only
  ],

  GENERATE: [
    /\b(create|build|make|develop|generate|write|implement|design|construct|setup|scaffold|bootstrap|initialize|init|start)\s+(a|an|the|new|my)?\s*\w+/i,
    /\b(i\s+(want|need|would\s+like)\s+(a|an|to\s+(create|build|make|have)))/i,
    /\b(can\s+you\s+(create|build|make|generate|write|develop))/i,
    /\b(help\s+me\s+(create|build|make|develop|write|generate))/i,
    /\b(new\s+(project|app|application|website|site|api|backend|frontend|component|page))/i,
    /\b(from\s+scratch|brand\s+new|fresh\s+start)/i,
    /\b(full[- ]?stack|fullstack)\s+(app|application|project)/i,
  ],

  MODIFY: [
    /\b(add|update|change|modify|edit|alter|adjust|tweak|enhance|extend|expand|include|insert)\s+(a|an|the|this|that|new)?\s*\w+/i,
    /\b(can\s+you\s+(add|update|change|modify|include))/i,
    /\b(i\s+want\s+to\s+(add|update|change|modify))/i,
    /\b(put|place|insert)\s+(a|an|the|this)?\s*\w+\s+(in|into|to|on)/i,
    /\b(make\s+(it|this|the)\s+(more|less|better|different))/i,
    /\b(replace|swap|switch)\s+(the|this|that)?\s*\w+/i,
    /\b(remove|delete|take\s+out)\s+(the|this|that|a|an)?\s*\w+/i,
  ],

  EXPLAIN: [
    /\b(explain|describe|tell\s+me|what\s+is|what\s+are|what's|how\s+does|how\s+do|how\s+is|why\s+does|why\s+is|why\s+do)\b/i,
    /\b(can\s+you\s+explain|could\s+you\s+explain)/i,
    /\b(what\s+does\s+(this|that|it)\s+(mean|do))/i,
    /\b(i\s+don't\s+understand|i\s+don't\s+get)/i,
    /\b(walk\s+me\s+through|break\s+(it|this)\s+down)/i,
    /\b(what's\s+the\s+(difference|purpose|point|meaning))/i,
    /^(what|why|how|when|where|who)\s+/i,
  ],

  DEBUG: [
    /\b(fix|debug|solve|resolve|troubleshoot|repair|correct|patch)\s+(this|the|my|a|an)?\s*(error|bug|issue|problem|crash|failure)/i,
    /\b(not\s+working|doesn't\s+work|won't\s+work|broken|failing|crashed|error)/i,
    /\b(why\s+(is|isn't|does|doesn't)\s+(this|it|my))/i,
    /\b(getting\s+(an?\s+)?(error|exception|bug|issue))/i,
    /\b(something\s+(is\s+)?(wrong|broken|off))/i,
    /\b(help\s+me\s+(fix|debug|solve|troubleshoot))/i,
    /\b(can't\s+(figure\s+out|understand|see)\s+(why|what|how))/i,
  ],

  DOCUMENT: [
    /\b(document|documentation|docs|readme|comment|jsdoc|docstring|api\s+docs)/i,
    /\b(write\s+(the\s+)?(docs|documentation|readme|comments))/i,
    /\b(add\s+(the\s+)?(docs|documentation|comments|jsdoc))/i,
    /\b(generate\s+(the\s+)?(docs|documentation|readme|srs|report))/i,
    /\b(srs|software\s+requirements|technical\s+doc|specification)/i,
  ],

  REFACTOR: [
    /\b(refactor|restructure|reorganize|clean\s+up|improve|optimize|simplify)/i,
    /\b(make\s+(it|this|the\s+code)\s+(cleaner|better|simpler|more\s+readable|more\s+efficient))/i,
    /\b(reduce\s+(duplication|complexity|redundancy))/i,
    /\b(extract\s+(to|into)\s+(a\s+)?(function|component|class|module))/i,
    /\b(split\s+(this|the)\s+(into|to))/i,
  ],

  // FIX: Auto-fix patterns - user reports a problem in simple terms
  // System automatically collects all context (errors, logs, code) and fixes
  FIX: [
    // Simple problem reports (Bolt.new style - user doesn't need technical knowledge)
    /\b(page|screen|app|site|website)\s+(is\s+)?(blank|empty|white|black|not\s+showing)/i,
    /\b(nothing\s+(is\s+)?(showing|appearing|loading|working|displayed))/i,
    /\b(it('s|s)?\s+(not\s+working|broken|crashed|stuck|frozen|dead))/i,
    /\b(something\s+(is\s+)?(wrong|broken|off|weird|strange))/i,
    /\b(doesn't|does\s+not|won't|will\s+not|can't|cannot)\s+(work|load|show|display|render|run|start)/i,
    /\b(preview\s+(is\s+)?(blank|empty|not\s+working|broken|white|black|dead))/i,
    /\b(i\s+(see|get|have)\s+(a\s+)?(blank|white|empty|black)\s+(page|screen))/i,

    // Error mentions without technical details
    /\b(there('s|s)?\s+(an?\s+)?error)/i,
    /\b(i('m|\s+am)\s+getting\s+(an?\s+)?error)/i,
    /\b(it\s+(says|shows)\s+error)/i,
    /\b(error\s+(message|appeared|popped\s+up))/i,

    // Fix requests
    /\b(fix\s+(this|it|the\s+error|the\s+bug|the\s+issue|the\s+problem|my\s+app|my\s+code))/i,
    /\b(please\s+fix)/i,
    /\b(can\s+you\s+fix)/i,
    /\b(help\s+me\s+fix)/i,

    // Build/compile problems
    /\b(build\s+(failed|error|broken|not\s+working))/i,
    /\b(compile\s+(error|failed|problem))/i,
    /\b(npm|yarn|pnpm)\s+(error|failed|problem)/i,

    // Runtime problems
    /\b(crashed|crashing|keeps\s+crashing)/i,
    /\b(stuck\s+(on|at)\s+(loading|startup|splash))/i,
    /\b(infinite\s+(loop|loading|spinner))/i,
    /\b(won't\s+start|doesn't\s+start|not\s+starting)/i,

    // Visual problems
    /\b(looks\s+(wrong|weird|broken|off|bad|messed\s+up))/i,
    /\b(layout\s+(is\s+)?(broken|wrong|off|messed))/i,
    /\b(styles?\s+(not\s+working|broken|missing|wrong))/i,
    /\b(button|link|form)\s+(doesn't|does\s+not)\s+work/i,
  ],
}

// Keywords that strongly indicate specific intents
const INTENT_KEYWORDS: Record<PromptIntent, string[]> = {
  CHAT: [],  // Chat is detected by patterns only
  GENERATE: [
    'create', 'build', 'make', 'develop', 'generate', 'write', 'implement',
    'new project', 'new app', 'from scratch', 'scaffold', 'bootstrap',
    'fullstack', 'full-stack', 'full stack'
  ],
  MODIFY: [
    'add', 'update', 'change', 'modify', 'edit', 'extend', 'include',
    'remove', 'delete', 'replace', 'insert', 'put'
  ],
  EXPLAIN: [
    'explain', 'describe', 'what is', 'what are', 'how does', 'how do',
    'why does', 'why is', 'tell me about', 'understand'
  ],
  DEBUG: [
    'fix', 'debug', 'error', 'bug', 'issue', 'problem', 'broken',
    'not working', 'crash', 'failing', 'troubleshoot'
  ],
  DOCUMENT: [
    'document', 'documentation', 'readme', 'docs', 'srs', 'specification',
    'comments', 'jsdoc', 'docstring', 'api docs'
  ],
  REFACTOR: [
    'refactor', 'clean up', 'restructure', 'reorganize', 'optimize',
    'simplify', 'improve code', 'make cleaner'
  ],

  // FIX: Keywords for auto-fix intent (user reports problems in simple terms)
  FIX: [
    'not working', 'broken', 'blank page', 'white screen', 'empty',
    'error', 'crashed', 'crashing', 'stuck', 'frozen',
    'fix this', 'fix it', 'please fix', 'help fix',
    'build failed', 'compile error', 'npm error',
    'doesn\'t work', 'won\'t load', 'not showing', 'nothing showing',
    'looks wrong', 'looks weird', 'messed up', 'layout broken'
  ],
}

// Technology detection patterns
const TECHNOLOGY_PATTERNS: Record<string, RegExp> = {
  'react': /\b(react|reactjs|react\.js)\b/i,
  'next.js': /\b(next|nextjs|next\.js)\b/i,
  'vue': /\b(vue|vuejs|vue\.js)\b/i,
  'angular': /\b(angular|angularjs)\b/i,
  'svelte': /\b(svelte|sveltekit)\b/i,
  'typescript': /\b(typescript|ts)\b/i,
  'javascript': /\b(javascript|js|vanilla\s*js)\b/i,
  'python': /\b(python|py)\b/i,
  'fastapi': /\b(fastapi|fast\s*api)\b/i,
  'django': /\b(django)\b/i,
  'flask': /\b(flask)\b/i,
  'express': /\b(express|expressjs)\b/i,
  'node': /\b(node|nodejs|node\.js)\b/i,
  'tailwind': /\b(tailwind|tailwindcss)\b/i,
  'bootstrap': /\b(bootstrap)\b/i,
  'mongodb': /\b(mongo|mongodb)\b/i,
  'postgresql': /\b(postgres|postgresql|pg)\b/i,
  'mysql': /\b(mysql)\b/i,
  'graphql': /\b(graphql|gql)\b/i,
  'rest': /\b(rest|restful|rest\s*api)\b/i,
}

// Project type patterns
const PROJECT_TYPE_PATTERNS: Record<string, RegExp> = {
  'web app': /\b(web\s*(app|application)|webapp)\b/i,
  'mobile app': /\b(mobile\s*(app|application)|android|ios)\b/i,
  'api': /\b(api|backend|server|microservice)\b/i,
  'website': /\b(website|site|landing\s*page|portfolio)\b/i,
  'dashboard': /\b(dashboard|admin\s*panel|control\s*panel)\b/i,
  'e-commerce': /\b(e-?commerce|shop|store|marketplace)\b/i,
  'blog': /\b(blog|cms|content\s*management)\b/i,
  'chat': /\b(chat|messaging|real-?time)\b/i,
  'todo': /\b(todo|task|project\s*management)\b/i,
  'auth': /\b(auth|authentication|login|signup)\b/i,
}

/**
 * Quick local classification for obvious cases (greetings, etc.)
 * Returns null if the prompt needs AI classification
 */
function quickLocalClassify(prompt: string): ClassificationResult | null {
  const normalizedPrompt = prompt.trim().toLowerCase().replace(/[!.,?]+$/, '')

  // Obvious CHAT patterns - handle locally for instant response
  const chatPatterns = [
    /^(hi|hello|hey|hola|namaste|howdy|greetings|yo|sup)$/i,
    /^(good\s+(morning|afternoon|evening|night))$/i,
    /^(how\s+are\s+you|what's\s+up|whats\s+up|wassup)$/i,
    /^(thanks|thank\s+you|thx|ty|cheers)$/i,
    /^(bye|goodbye|see\s+you|cya|later|farewell)$/i,
    /^(yes|no|ok|okay|sure|yep|nope|yeah|nah|yup)$/i,
    /^(nice|cool|awesome|great|perfect|amazing)$/i,
  ]

  for (const pattern of chatPatterns) {
    if (pattern.test(normalizedPrompt)) {
      return {
        intent: 'CHAT',
        confidence: 1.0,
        entities: {},
        requiresGeneration: false,
        suggestedWorkflow: 'chat_only',
        chatResponse: getChatResponse(prompt)
      }
    }
  }

  return null  // Needs AI classification
}

/**
 * Call the backend AI-powered classifier
 */
async function classifyWithAPI(
  prompt: string,
  context?: {
    hasExistingProject?: boolean
    currentFiles?: string[]
    conversationHistory?: Array<{ role: string; content: string }>
  }
): Promise<ClassificationResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/classify/classify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt,
        has_existing_project: context?.hasExistingProject || false,
        current_files: context?.currentFiles || [],
        conversation_history: context?.conversationHistory || []
      })
    })

    if (!response.ok) {
      throw new Error(`Classification API error: ${response.status}`)
    }

    const data = await response.json()

    return {
      intent: data.intent as PromptIntent,
      confidence: data.confidence,
      reasoning: data.reasoning,
      entities: data.entities || {},
      requiresGeneration: data.requires_generation,
      suggestedWorkflow: data.suggested_workflow as 'bolt_standard' | 'bolt_instant' | 'chat_only',
      chatResponse: data.chat_response
    }
  } catch (error) {
    console.error('[PromptClassifier] API call failed, using fallback:', error)
    // Fall back to local classification
    return classifyPromptLocal(prompt, context)
  }
}

/**
 * Main classifier function - uses AI for complex prompts
 */
export async function classifyPromptAsync(
  prompt: string,
  context?: {
    hasExistingProject?: boolean
    currentFiles?: string[]
    conversationHistory?: Array<{ role: string; content: string }>
  }
): Promise<ClassificationResult> {
  // 1. Quick check for empty prompts
  if (!prompt || !prompt.trim()) {
    return {
      intent: 'CHAT',
      confidence: 1.0,
      entities: {},
      requiresGeneration: false,
      suggestedWorkflow: 'chat_only',
      chatResponse: "Hello! I'm BharatBuild AI. What would you like to build today?"
    }
  }

  // 2. Try quick local classification first (for obvious cases)
  const quickResult = quickLocalClassify(prompt)
  if (quickResult) {
    console.log('[PromptClassifier] Quick local classification:', quickResult.intent)
    return quickResult
  }

  // 3. Use AI-powered classification for complex prompts
  console.log('[PromptClassifier] Using AI classification for:', prompt.substring(0, 50))
  return classifyWithAPI(prompt, context)
}

/**
 * Synchronous classifier function (fallback, uses local patterns only)
 * Use classifyPromptAsync for AI-powered classification
 */
export function classifyPrompt(prompt: string, context?: {
  hasExistingProject?: boolean
  currentFiles?: string[]
  conversationHistory?: string[]
}): ClassificationResult {
  return classifyPromptLocal(prompt, context)
}

/**
 * Local pattern-based classifier (fallback when API unavailable)
 */
function classifyPromptLocal(prompt: string, context?: {
  hasExistingProject?: boolean
  currentFiles?: string[]
  conversationHistory?: string[] | Array<{ role: string; content: string }>
}): ClassificationResult {
  const normalizedPrompt = prompt.trim().toLowerCase()

  // Quick check for empty or very short prompts
  if (!normalizedPrompt || normalizedPrompt.length < 2) {
    return {
      intent: 'CHAT',
      confidence: 1.0,
      entities: {},
      requiresGeneration: false,
      suggestedWorkflow: 'chat_only'
    }
  }

  // Score each intent
  const scores: Record<PromptIntent, number> = {
    CHAT: 0,
    GENERATE: 0,
    MODIFY: 0,
    EXPLAIN: 0,
    DEBUG: 0,
    FIX: 0,
    DOCUMENT: 0,
    REFACTOR: 0,
  }

  // Check patterns
  for (const [intent, patterns] of Object.entries(INTENT_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(normalizedPrompt)) {
        scores[intent as PromptIntent] += 2
      }
    }
  }

  // Check keywords
  for (const [intent, keywords] of Object.entries(INTENT_KEYWORDS)) {
    for (const keyword of keywords) {
      if (normalizedPrompt.includes(keyword.toLowerCase())) {
        scores[intent as PromptIntent] += 1
      }
    }
  }

  // Context-based adjustments
  if (context?.hasExistingProject) {
    // If there's already a project, MODIFY becomes more likely than GENERATE
    scores.MODIFY += 1
    scores.GENERATE -= 1
  }

  // Find the winning intent
  let maxScore = 0
  let winningIntent: PromptIntent = 'CHAT'

  for (const [intent, score] of Object.entries(scores)) {
    if (score > maxScore) {
      maxScore = score
      winningIntent = intent as PromptIntent
    }
  }

  // If no patterns matched, default to CHAT for short messages or GENERATE for longer ones
  if (maxScore === 0) {
    if (normalizedPrompt.split(/\s+/).length <= 3) {
      winningIntent = 'CHAT'
    } else {
      // Longer messages might be project descriptions
      winningIntent = 'GENERATE'
      maxScore = 0.5
    }
  }

  // Calculate confidence (normalize to 0-1)
  const confidence = Math.min(maxScore / 5, 1)

  // Extract entities
  const entities = extractEntities(prompt)

  // Determine if generation is required
  const requiresGeneration = ['GENERATE', 'MODIFY', 'DOCUMENT', 'REFACTOR', 'FIX'].includes(winningIntent)

  // Suggest workflow
  let suggestedWorkflow: 'bolt_standard' | 'bolt_instant' | 'chat_only' = 'chat_only'
  if (winningIntent === 'GENERATE') {
    suggestedWorkflow = 'bolt_standard'
  } else if (['MODIFY', 'REFACTOR'].includes(winningIntent)) {
    suggestedWorkflow = 'bolt_instant'
  } else if (winningIntent === 'DOCUMENT') {
    suggestedWorkflow = 'bolt_standard'
  } else if (winningIntent === 'FIX') {
    // FIX intent uses bolt_instant workflow with auto-collected context
    suggestedWorkflow = 'bolt_instant'
  }

  return {
    intent: winningIntent,
    confidence,
    entities,
    requiresGeneration,
    suggestedWorkflow
  }
}

/**
 * Extract entities from the prompt
 */
function extractEntities(prompt: string): ClassificationResult['entities'] {
  const entities: ClassificationResult['entities'] = {}
  const normalizedPrompt = prompt.toLowerCase()

  // Detect technologies
  const technologies: string[] = []
  for (const [tech, pattern] of Object.entries(TECHNOLOGY_PATTERNS)) {
    if (pattern.test(normalizedPrompt)) {
      technologies.push(tech)
    }
  }
  if (technologies.length > 0) {
    entities.technology = technologies
  }

  // Detect project type
  for (const [projectType, pattern] of Object.entries(PROJECT_TYPE_PATTERNS)) {
    if (pattern.test(normalizedPrompt)) {
      entities.projectType = projectType
      break
    }
  }

  // Extract action verb
  const actionMatch = normalizedPrompt.match(
    /\b(create|build|make|develop|generate|write|implement|add|update|change|modify|fix|debug|explain|refactor)\b/i
  )
  if (actionMatch) {
    entities.action = actionMatch[1].toLowerCase()
  }

  return entities
}

/**
 * Generate appropriate response for CHAT intent
 */
export function getChatResponse(prompt: string): string {
  const normalizedPrompt = prompt.toLowerCase().trim().replace(/[!.,?]+$/, '')

  const responses: Record<string, string> = {
    'hi': `Hello! Welcome to **BharatBuild AI** - Your AI-Powered Development Partner!

I can help you build complete, production-ready applications in minutes. Here's what I can do:

**Quick Start Ideas:**
- "Create a React dashboard with charts and authentication"
- "Build an e-commerce website with Next.js"
- "Generate a REST API with FastAPI and PostgreSQL"

What would you like to build today?`,

    'hello': `Hello! I'm **BharatBuild AI**, your intelligent code generation assistant.

**My Capabilities:**
- Full-stack web applications (React, Next.js, Vue, Angular)
- Backend APIs (FastAPI, Express, Django, Flask)
- Mobile-ready responsive designs
- Database integrations (PostgreSQL, MongoDB, MySQL)
- Authentication systems (JWT, OAuth)
- Documentation (SRS, README, API docs)

Just describe your project idea, and I'll generate the complete code for you!`,

    'hey': `Hey there! Ready to turn your ideas into code?

I'm BharatBuild AI - I generate **complete, working applications** from your descriptions. No boilerplate, no setup hassle - just describe what you need!

**Popular requests:**
- Task management apps
- E-commerce platforms
- Admin dashboards
- Chat applications
- Portfolio websites

What's on your mind?`,

    'hola': `¡Hola! Welcome to **BharatBuild AI**!

I'm your AI development assistant, ready to generate complete applications in any tech stack you prefer.

¿Qué te gustaría construir hoy? (What would you like to build today?)`,

    'namaste': `Namaste! 🙏 Welcome to **BharatBuild AI**!

I'm here to help you build amazing software projects. Whether you're a student working on college projects or a professional building production apps, I've got you covered!

**Special Features for Indian Developers:**
- Academic project documentation (SRS, UML, Reports)
- IEEE paper-based project generation
- Full-stack MERN/MEAN applications
- Python/FastAPI backends

Tell me about your project!`,

    'good morning': `Good morning! ☀️

Welcome to **BharatBuild AI**! It's a great day to build something amazing.

**Quick Actions:**
- Describe a new project to generate
- Upload an IEEE paper for academic projects
- Ask me to explain any coding concept

What would you like to accomplish today?`,

    'good afternoon': `Good afternoon!

I'm **BharatBuild AI**, ready to help you with your development needs.

Whether you need a quick prototype or a full production app, just describe it and I'll generate the code!

What are you working on?`,

    'good evening': `Good evening! 🌙

Welcome to **BharatBuild AI**! Let's make your evening productive.

I can generate complete applications while you relax - just tell me what you need!

What would you like to build?`,

    'how are you': `I'm running at full capacity and ready to generate amazing code for you!

Thanks for asking! As an AI, I'm always excited to help developers like you build their projects faster.

**Fun fact:** I can generate a complete full-stack application in just a few minutes!

What can I build for you today?`,

    "what's up": `Not much - just ready to generate some awesome code!

I've been helping developers build:
- E-commerce platforms
- Social media apps
- Admin dashboards
- API backends
- And much more!

Your turn - what would you like me to create?`,

    'help': `# BharatBuild AI - Help Guide

## What I Can Do

### **Project Generation**
- "Create a React dashboard with authentication"
- "Build an e-commerce site with Next.js and Stripe"
- "Generate a social media app like Twitter"

### **API Development**
- "Build a REST API with FastAPI and PostgreSQL"
- "Create a GraphQL backend with Node.js"
- "Generate CRUD endpoints for user management"

### **Academic Projects**
- "Generate an IEEE paper implementation"
- "Create SRS documentation for my project"
- "Build a machine learning web app"

### **Code Modifications**
- "Add dark mode to my app"
- "Implement user authentication"
- "Add payment integration"

### **Documentation**
- "Generate README for my project"
- "Create API documentation"
- "Write SRS and SDS documents"

## Tips for Best Results
1. **Be specific** - Include tech stack preferences
2. **Mention features** - List key functionalities needed
3. **Specify style** - Modern, minimal, colorful, etc.

## Example Prompts
\`\`\`
"Create a task management app with React, TypeScript,
Tailwind CSS, with features: user auth, drag-drop tasks,
deadline reminders, and dark mode"
\`\`\`

What would you like to build?`,

    'what can you do': `# BharatBuild AI Capabilities

## **Full-Stack Development**
| Frontend | Backend | Database |
|----------|---------|----------|
| React | FastAPI | PostgreSQL |
| Next.js | Express | MongoDB |
| Vue.js | Django | MySQL |
| Angular | Flask | SQLite |

## **Key Features**
- **Complete Code Generation** - Not snippets, but full working apps
- **Production Ready** - Proper error handling, validation, security
- **Modern Stack** - Latest frameworks and best practices
- **Documentation** - README, API docs, comments included

## **Special Capabilities**
- **IEEE Paper Analysis** - Upload research papers, get implementations
- **Academic Docs** - SRS, SDS, UML diagrams, project reports
- **Live Preview** - See your app running in real-time
- **Export** - Download as ZIP, ready to deploy

## **Try These Commands**
- "Create a [type] app with [tech stack]"
- "Build an API for [purpose]"
- "Generate documentation for [project]"
- "Explain [concept]"

What would you like me to build for you?`,

    'who are you': `# About BharatBuild AI

I'm **BharatBuild AI** - an advanced AI-powered code generation platform designed to help developers build applications faster.

## **My Mission**
To democratize software development by making it accessible to everyone - from students to professionals.

## **What Makes Me Different**
- **Complete Applications** - I don't just give snippets; I generate entire working projects
- **Production Quality** - Clean code, proper structure, best practices
- **Academic Focus** - Special support for college projects and documentation
- **Indian Developer Friendly** - Built with the needs of Indian developers in mind

## **Technology**
I'm powered by advanced AI models that understand code, architecture, and best practices across multiple programming languages and frameworks.

## **Created For**
- Students building college projects
- Startups creating MVPs
- Developers prototyping ideas
- Teams needing quick implementations

Ready to experience the future of development? Tell me what you'd like to build!`,

    'thanks': `You're welcome! I'm glad I could help!

**Before you go:**
- You can **Export** your project as a ZIP file
- Use **Preview** to see your app running
- Come back anytime to modify or build new projects

Need anything else? I'm here 24/7!`,

    'thank you': `You're very welcome! It was my pleasure to help!

**Quick Tips:**
- Browse your files in the editor panel
- Click Preview to see your app live
- Use Export to download your project

Feel free to describe another project whenever you're ready. Happy coding!`,

    'bye': `Goodbye! 👋

Thanks for using **BharatBuild AI**!

**Remember:**
- Your project files are saved in the editor
- You can export anytime using the Export button
- Come back whenever you need to build something new

See you soon! Happy coding! 🚀`,

    'goodbye': `See you later!

It was great helping you today. Your generated projects are ready to use.

**Quick Actions Before You Go:**
- Export your project as ZIP
- Preview your application
- Copy code to your clipboard

Come back anytime - I'll be here ready to build your next project!`,

    'yes': `Great! I'm ready to help!

**What would you like to do?**
1. **Create a new project** - Describe your app idea
2. **Modify existing code** - Tell me what to change
3. **Generate documentation** - Request SRS, README, etc.
4. **Explain concepts** - Ask me anything about coding

Just type your request!`,

    'no': `No problem at all!

Take your time. When you're ready, you can:
- Describe a project to build
- Ask questions about coding
- Request documentation
- Get help with debugging

I'll be right here whenever you need me!`,

    'ok': `Sounds good!

Whenever you're ready, just describe what you'd like to build. I can create:
- Web applications
- APIs and backends
- Mobile-responsive sites
- Documentation

What's your next project idea?`,

    'okay': `Perfect! I'm standing by and ready to help!

**Quick Start:**
Just type something like:
- "Create a blog with Next.js"
- "Build a REST API with Python"
- "Generate a portfolio website"

What would you like to build?`,

    'cool': `Thanks! Glad you think so!

I'm constantly improving to generate better code for you.

**Ready for the next challenge?** Describe your project and watch the magic happen!`,

    'nice': `Thank you!

I love helping developers bring their ideas to life.

**What's next?** Got another project in mind? A feature to add? Documentation to generate? Let me know!`,

    'awesome': `Thanks! Your enthusiasm is awesome too!

Let's keep the momentum going - what would you like to create next?

**Ideas:**
- Add new features to your project
- Build something completely new
- Generate documentation
- Try a different tech stack`,

    'start': `Let's get started! 🚀

**To create a new project, describe it like this:**

"Create a [project type] with [technologies] that has [features]"

**Examples:**
- "Create a task manager with React and Firebase that has user auth and real-time sync"
- "Build an e-commerce API with FastAPI, PostgreSQL, and Stripe payments"
- "Generate a portfolio website with Next.js, Tailwind, and dark mode"

What would you like to build?`,

    'features': `# BharatBuild AI Features

## **Code Generation**
- Full-stack applications
- API backends
- Frontend components
- Database schemas

## **Documentation**
- README files
- API documentation
- SRS documents
- UML diagrams
- Project reports

## **Academic Support**
- IEEE paper analysis
- College project templates
- Technical documentation
- Presentation materials

## **Developer Tools**
- Live preview
- File explorer
- Code editor
- Terminal output
- Export to ZIP

## **Tech Stacks Supported**
- React, Next.js, Vue, Angular
- FastAPI, Express, Django, Flask
- PostgreSQL, MongoDB, MySQL
- Tailwind, Bootstrap, Material UI
- TypeScript, JavaScript, Python

What feature would you like to try?`,
  }

  // Check for exact match
  if (responses[normalizedPrompt]) {
    return responses[normalizedPrompt]
  }

  // Check for partial matches
  for (const [key, response] of Object.entries(responses)) {
    if (normalizedPrompt.includes(key) || key.includes(normalizedPrompt)) {
      return response
    }
  }

  // Default response
  return `# Welcome to BharatBuild AI!

I'm your AI-powered development assistant, ready to generate complete, production-ready applications.

## **What I Can Build**
- Full-stack web applications
- REST & GraphQL APIs
- Admin dashboards
- E-commerce platforms
- Social media apps
- And much more!

## **How to Get Started**
Just describe your project! For example:
- "Create a task management app with React and Node.js"
- "Build a REST API with FastAPI and PostgreSQL"
- "Generate an e-commerce platform with Next.js"

## **Need Help?**
Type "help" for a complete guide of my capabilities.

What would you like to create today?`
}

/**
 * Get response for EXPLAIN intent
 */
export function getExplainResponse(prompt: string): string {
  return `# I'd Be Happy to Help Explain!

While I'm primarily designed for **code generation**, I can definitely help you understand concepts.

## **How I Can Help**

### **Option 1: Generate with Explanations**
I can create code with detailed comments explaining each part:
- "Create a React component with comments explaining the hooks"
- "Build an API with documentation for each endpoint"

### **Option 2: Documentation Generation**
I can generate comprehensive documentation:
- README files with setup instructions
- API documentation with examples
- Code architecture explanations

### **Option 3: Example Projects**
Learn by example - I'll generate a working project:
- "Create a simple example of React context"
- "Build a basic REST API to demonstrate CRUD operations"

## **What Would You Like?**
1. Generate code with explanations?
2. Create documentation?
3. Build an example project?

Just let me know what concept you want to understand, and I'll generate something helpful!`
}

/**
 * Get response for DEBUG intent without existing project
 */
export function getDebugResponse(prompt: string): string {
  return `# Debug Assistance

I'm ready to help you fix that issue! To provide the best solution, I need some information:

## **Please Provide:**

### **1. The Code**
\`\`\`
Paste the problematic code here or describe which file has the issue
\`\`\`

### **2. The Error Message**
What error are you seeing? Include:
- Error message text
- Stack trace (if available)
- Console output

### **3. Expected vs Actual Behavior**
- What should happen?
- What actually happens?

## **Quick Fix Options**

### **Option A: Paste Your Code**
Share the code and error, and I'll fix it for you.

### **Option B: Generate Fresh**
If the code is too broken, I can generate a fresh, working version:
- "Create a working user authentication system"
- "Build a functional CRUD API"

### **Option C: Common Fixes**
Tell me if you're facing common issues:
- CORS errors
- Authentication problems
- Database connection issues
- API not responding
- Component not rendering

## **What's the issue you're facing?**`
}

export default {
  classifyPrompt,
  getChatResponse,
  getExplainResponse,
  getDebugResponse,
}
