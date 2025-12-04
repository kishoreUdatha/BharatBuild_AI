"""
Mock Claude Client for Testing
Provides mock responses without calling the actual API
"""
from typing import AsyncGenerator, Optional, Dict, Any
import json


class MockClaudeClient:
    """Mock Claude client that returns predefined responses"""
    
    def __init__(self):
        self.call_count = 0
        self.last_prompt = None
        self.last_system = None
        self.responses = {}
    
    def set_response(self, key: str, response: str):
        """Set a custom response for a specific key"""
        self.responses[key] = response
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = 'sonnet',
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """Mock generate method"""
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system = system
        
        # Check for custom response
        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return response
        
        # Default response based on prompt content
        if 'plan' in prompt.lower():
            return self._get_plan_response()
        elif 'code' in prompt.lower() or 'write' in prompt.lower():
            return self._get_code_response()
        elif 'analyze' in prompt.lower():
            return self._get_analysis_response()
        else:
            return 'Mock response from Claude'
    
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = 'sonnet',
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Mock streaming generate method"""
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system = system
        
        response = await self.generate(prompt, system, model, max_tokens, temperature)
        
        # Simulate streaming by yielding chunks
        words = response.split()
        for i in range(0, len(words), 3):
            chunk = ' '.join(words[i:i+3])
            yield chunk + ' '
    
    def _get_plan_response(self) -> str:
        """Return a mock project plan"""
        return json.dumps({
            'project_name': 'Test Project',
            'description': 'A test project for unit testing',
            'files': [
                {'path': 'src/main.py', 'description': 'Main entry point'},
                {'path': 'src/utils.py', 'description': 'Utility functions'},
                {'path': 'requirements.txt', 'description': 'Dependencies'},
                {'path': 'README.md', 'description': 'Documentation'}
            ],
            'technologies': ['Python', 'FastAPI', 'SQLAlchemy'],
            'estimated_tokens': 5000
        })
    
    def _get_code_response(self) -> str:
        """Return mock code"""
        return '# main.py\ndef main():\n    print("Hello from BharatBuild AI")\n\nif __name__ == "__main__":\n    main()'
    
    def _get_analysis_response(self) -> str:
        """Return mock analysis"""
        return json.dumps({
            'paper_info': {
                'title': 'Test Paper',
                'domain': 'Machine Learning'
            },
            'methodology': {
                'approach': 'Neural Network',
                'steps': ['Data preprocessing', 'Model training', 'Evaluation']
            },
            'technologies': {
                'programming_languages': ['Python'],
                'frameworks': ['TensorFlow', 'PyTorch']
            }
        })
    
    def reset(self):
        """Reset mock state"""
        self.call_count = 0
        self.last_prompt = None
        self.last_system = None
        self.responses = {}


# Singleton mock client
mock_claude_client = MockClaudeClient()
