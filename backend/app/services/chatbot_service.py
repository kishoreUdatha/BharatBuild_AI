"""
AI Chatbot Service for BharatBuild AI
======================================
Handles user queries using Google Gemini (FREE) with context about the platform.
Supports FAQs, technical support, and sales queries.
Falls back to rule-based responses when Gemini is unavailable.
"""

from typing import Optional, List, Dict
from datetime import datetime
from app.core.config import settings
from app.core.logging_config import logger

# Try to import Gemini, but don't fail if unavailable
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("[Chatbot] google-genai not installed, using fallback responses")


class ChatbotService:
    """AI-powered chatbot using Google Gemini (Free) with fallback responses"""

    def __init__(self):
        self.client = None
        self.model = settings.GEMINI_MODEL
        self.use_fallback = False

        # Try to initialize Gemini client
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info(f"[Chatbot] Initialized with Gemini model: {self.model}")
            except Exception as e:
                logger.warning(f"[Chatbot] Failed to init Gemini client: {e}, using fallback")
                self.use_fallback = True
        else:
            self.use_fallback = True
            logger.info("[Chatbot] Using fallback responses (no Gemini API key)")

        # Fallback responses for common queries
        self.fallback_responses = {
            "pricing": "BharatBuild AI offers:\n- **Free Plan**: Preview 3 files, see project structure\n- **Premium Plan**: Rs 4,499 one-time payment for 1 complete project with full code, documentation, PPT, and Viva Q&A.\n\nVisit our pricing page for more details!",
            "features": "BharatBuild AI features include:\n- **AI Project Generation**: Describe your idea, get complete working code\n- **Multiple Technologies**: React, Next.js, Flutter, Django, FastAPI, and more\n- **Complete Documentation**: SRS, SDS, Project Report (60-80 pages), PPT, Viva Q&A\n- **Bug Fixing**: AI automatically detects and fixes errors\n- **Download Options**: ZIP download or GitHub export",
            "how": "Here's how BharatBuild AI works:\n1. **Describe**: Tell AI what you want to build\n2. **Generate**: AI creates complete project with code & docs\n3. **Preview**: Test and run code in browser\n4. **Download**: Get ZIP or push to GitHub",
            "support": "For support, please contact us at support@bharatbuild.ai. Our team typically responds within 24-48 hours.",
            "error": "If you're facing errors:\n1. Use the 'Fix' button to let AI auto-fix errors\n2. Check if you're logged in with valid tokens\n3. Make sure project is fully generated before downloading\n\nIf issues persist, contact support@bharatbuild.ai",
            "default": "Hi! I'm BharatBuild AI Assistant. I can help you with:\n- General questions and conversations\n- Programming and technology queries\n- BharatBuild AI platform (pricing, features, how-to)\n- Technical support\n\nHow can I assist you today?"
        }

        # Knowledge base about BharatBuild AI
        self.system_prompt = """You are BharatBuild AI Assistant - a helpful, friendly, and intelligent chatbot.

## Your Role
You are a versatile AI assistant that can:
1. Help users with BharatBuild AI platform questions
2. Have general conversations on any topic
3. Answer programming and technology questions
4. Provide helpful information on various subjects

## About BharatBuild AI (When Asked)
BharatBuild AI is India's #1 AI-powered development platform that helps students and developers build complete projects using AI. Users describe their project idea, and AI generates full working code, documentation, and more.

Key Features:
- AI Project Generation: Describe your idea, get complete working code
- Multiple Technologies: React, Next.js, Flutter, Django, FastAPI, Node.js, and more
- Complete Documentation: SRS, SDS, Project Report (60-80 pages), PPT, Viva Q&A
- Bug Fixing: AI automatically detects and fixes errors
- Code Preview: Run and test code in browser before downloading

Pricing:
- Free Plan: Preview 3 files, see project structure
- Premium Plan: ₹4,499 one-time payment for 1 complete project with full code, documentation, PPT, and Viva Q&A

## Your Behavior Guidelines
1. Be helpful, friendly, and conversational
2. Answer ANY question the user asks - not just BharatBuild related
3. For general questions, provide informative and helpful responses
4. For coding questions, provide clear explanations and examples
5. Keep responses concise but complete
6. Be natural and engaging in conversation
7. If asked about BharatBuild, provide accurate platform information
8. For complex technical issues with the platform, suggest support@bharatbuild.ai

## Current Date
{current_date}

Remember: You're a friendly AI assistant. Help users with whatever they need!"""

    def _get_fallback_response(self, user_message: str) -> str:
        """Get a rule-based fallback response based on keywords"""
        message_lower = user_message.lower()

        # BharatBuild-specific queries
        if any(word in message_lower for word in ["price", "cost", "pricing", "pay", "fee", "rupee", "rs", "inr", "plan"]):
            return self.fallback_responses["pricing"]
        elif any(word in message_lower for word in ["feature", "what can", "capability", "include", "bharatbuild"]):
            return self.fallback_responses["features"]
        elif any(word in message_lower for word in ["generate", "create project", "build project", "start project"]):
            return self.fallback_responses["how"]
        elif any(word in message_lower for word in ["error", "bug", "fix", "issue", "problem", "not working"]):
            return self.fallback_responses["error"]
        elif any(word in message_lower for word in ["support", "contact", "email"]):
            return self.fallback_responses["support"]

        # General greetings
        elif any(word in message_lower for word in ["hi", "hello", "hey", "good morning", "good evening"]):
            return "Hello! 👋 I'm BharatBuild AI Assistant. I can help you with questions about our platform, programming, or just have a chat. What's on your mind?"

        # General conversation - acknowledge and try to help
        elif "?" in user_message:
            return f"That's an interesting question! While I'm primarily designed to help with BharatBuild AI platform, I'd love to help. For the best experience with general questions, please make sure the AI service is fully configured. In the meantime, feel free to ask about our platform features, pricing, or technical support!"

        else:
            return self.fallback_responses["default"]

    async def get_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        user_context: Optional[Dict] = None
    ) -> str:
        """
        Get AI response for user query using Gemini with fallback.

        Args:
            user_message: The user's question/message
            conversation_history: Previous messages in the conversation
            user_context: Optional context about the user (logged in, plan, etc.)

        Returns:
            AI response string
        """
        # Use fallback if Gemini is not available
        if self.use_fallback or not self.client:
            return self._get_fallback_response(user_message)

        try:
            # Build system prompt with current date
            system = self.system_prompt.format(
                current_date=datetime.now().strftime("%B %d, %Y")
            )

            # Add user context if available
            if user_context:
                context_info = "\n\n## Current User Context\n"
                if user_context.get("is_logged_in"):
                    context_info += "- User is logged in\n"
                if user_context.get("plan"):
                    context_info += f"- Current plan: {user_context['plan']}\n"
                if user_context.get("has_project"):
                    context_info += "- Has active project\n"
                system += context_info

            # Build conversation contents for Gemini
            contents = []

            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages
                    role = "user" if msg.get("role") == "user" else "model"
                    contents.append(
                        types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=msg.get("content", ""))]
                        )
                    )

            # Add current user message
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message)]
                )
            )

            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=500,
                    temperature=0.7,
                )
            )

            return response.text

        except Exception as e:
            import traceback
            logger.error(f"[Chatbot] Gemini error: {e}, using fallback")
            logger.debug(f"[Chatbot] Traceback: {traceback.format_exc()}")
            # Fall back to rule-based response on error
            return self._get_fallback_response(user_message)

    async def get_quick_replies(self, category: Optional[str] = None) -> List[Dict]:
        """
        Get suggested quick reply buttons.

        Args:
            category: Optional category to filter suggestions

        Returns:
            List of quick reply options
        """
        all_replies = [
            {"text": "What is BharatBuild AI?", "category": "general"},
            {"text": "How much does it cost?", "category": "pricing"},
            {"text": "What's included in Premium?", "category": "pricing"},
            {"text": "How do I generate a project?", "category": "technical"},
            {"text": "My code has errors", "category": "technical"},
            {"text": "How to download my project?", "category": "technical"},
            {"text": "I need help with payment", "category": "payment"},
            {"text": "Contact support", "category": "support"},
        ]

        if category:
            return [r for r in all_replies if r["category"] == category]
        return all_replies[:4]  # Return top 4 by default


# Singleton instance
chatbot_service = ChatbotService()
