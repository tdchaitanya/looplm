#!/usr/bin/env python3
"""
Enhanced Demo for LoopLM Compact Functionality

This demo showcases the improved compact functionality with the new CompactHandler,
including error handling, progress indication, and better user experience.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import datetime
from unittest.mock import Mock

from rich.console import Console

from looplm.chat.compact_handler import CompactHandler
from looplm.chat.session import ChatSession, Message


def create_sample_session() -> ChatSession:
    """Create a sample session with multiple conversation turns"""
    session = ChatSession()
    session.set_system_prompt(
        "You are LoopLM, a helpful AI assistant specializing in software development."
    )

    # Add a realistic conversation
    conversations = [
        (
            "user",
            "I'm building a Python web application and need help with authentication. What's the best approach?",
        ),
        (
            "assistant",
            "For Python web applications, I'd recommend using a well-established authentication library. Here are some popular options:\n\n1. **Flask-Login** (for Flask apps)\n2. **Django's built-in auth** (for Django apps)\n3. **FastAPI-Users** (for FastAPI apps)\n4. **Authlib** (framework-agnostic)\n\nWhat framework are you using?",
        ),
        (
            "user",
            "I'm using FastAPI. Can you show me how to implement JWT authentication with FastAPI-Users?",
        ),
        (
            "assistant",
            'Absolutely! Here\'s a complete example of JWT authentication with FastAPI-Users:\n\n```python\nfrom fastapi import FastAPI, Depends\nfrom fastapi_users import FastAPIUsers, BaseUserManager\nfrom fastapi_users.authentication import JWTAuthentication\nfrom fastapi_users.db import SQLAlchemyUserDatabase\n\n# JWT Configuration\nSECRET = "your-secret-key-here"\njwt_authentication = JWTAuthentication(secret=SECRET, lifetime_seconds=3600)\n\n# User model and database setup\nclass UserManager(BaseUserManager):\n    user_db_model = User\n    reset_password_token_secret = SECRET\n    verification_token_secret = SECRET\n\n# FastAPI app setup\napp = FastAPI()\nfastapi_users = FastAPIUsers(\n    user_manager,\n    [jwt_authentication],\n    User,\n    UserCreate,\n    UserUpdate,\n    UserDB,\n)\n\n# Routes\napp.include_router(fastapi_users.get_auth_router(jwt_authentication), prefix="/auth/jwt")\napp.include_router(fastapi_users.get_register_router(), prefix="/auth")\n```\n\nWould you like me to explain any specific part?',
        ),
        (
            "user",
            "This looks great! How do I protect specific routes that require authentication?",
        ),
        (
            "assistant",
            'To protect routes in FastAPI-Users, you use dependency injection. Here\'s how:\n\n```python\n# Get the current user dependency\ncurrent_user = fastapi_users.current_user()\n\n@app.get("/protected")\nasync def protected_route(user: User = Depends(current_user)):\n    return {"message": f"Hello {user.email}, this is a protected route!"}\n\n# For optional authentication\ncurrent_user_optional = fastapi_users.current_user(optional=True)\n\n@app.get("/optional-auth")\nasync def optional_auth_route(user: User = Depends(current_user_optional)):\n    if user:\n        return {"message": f"Hello {user.email}!"}\n    return {"message": "Hello anonymous user!"}\n\n# For admin-only routes\n@app.get("/admin")\nasync def admin_route(user: User = Depends(current_user)):\n    if not user.is_superuser:\n        raise HTTPException(status_code=403, detail="Admin access required")\n    return {"message": "Admin panel"}\n```\n\nThe `Depends(current_user)` automatically validates the JWT token and returns the user object.',
        ),
        ("user", "Perfect! One last question - how do I handle token refresh?"),
        (
            "assistant",
            "Great question! JWT token refresh is crucial for security. Here's how to implement it:\n\n```python\nfrom fastapi_users.authentication import JWTAuthentication\n\n# Configure JWT with refresh capability\njwt_authentication = JWTAuthentication(\n    secret=SECRET,\n    lifetime_seconds=900,  # 15 minutes for access token\n    tokenUrl=\"auth/jwt/login\",\n)\n\n# Refresh token route\n@app.post(\"/auth/jwt/refresh\")\nasync def refresh_jwt_token(\n    response: Response,\n    user: User = Depends(fastapi_users.current_user())\n):\n    # Generate new token\n    token = await jwt_authentication.get_login_response(user, response)\n    return token\n```\n\nClient-side handling:\n```javascript\n// Store tokens\nlocalStorage.setItem('access_token', response.access_token);\nlocalStorage.setItem('refresh_token', response.refresh_token);\n\n// Auto-refresh before expiration\nsetInterval(async () => {\n    const refreshToken = localStorage.getItem('refresh_token');\n    const response = await fetch('/auth/jwt/refresh', {\n        method: 'POST',\n        headers: {\n            'Authorization': `Bearer ${refreshToken}`\n        }\n    });\n    const data = await response.json();\n    localStorage.setItem('access_token', data.access_token);\n}, 14 * 60 * 1000); // Refresh every 14 minutes\n```",
        ),
    ]

    for role, content in conversations:
        session.messages.append(Message(role, content, timestamp=datetime.now()))

    return session


def mock_llm_completion(model: str, messages: list) -> Mock:
    """Mock LLM completion for demo purposes"""
    mock_response = Mock()
    mock_response.choices = [Mock()]

    # Generate a realistic summary
    summary = """<analysis>
The conversation covers a comprehensive discussion about implementing JWT authentication in a FastAPI web application. The user asked about authentication approaches, received framework-specific recommendations, and then dove deep into FastAPI-Users implementation with JWT tokens.

Key topics covered:
- Authentication library recommendations for Python web frameworks
- Complete FastAPI-Users setup with JWT authentication
- Route protection using dependency injection
- Token refresh mechanisms for security

The conversation progressed logically from general authentication concepts to specific implementation details, with code examples provided for each step.
</analysis>

<summary>
1. **Primary Requests and Objectives**:
   - User needed guidance on authentication for a Python web application
   - Specifically wanted to implement JWT authentication with FastAPI
   - Required information on protecting routes and handling token refresh

2. **Key Concepts and Topics**:
   - FastAPI web framework
   - JWT (JSON Web Tokens) authentication
   - FastAPI-Users library
   - Route protection and dependency injection
   - Token refresh mechanisms
   - Security best practices

3. **Specific Details and Examples**:
   - Complete FastAPI-Users setup code with JWT configuration
   - Route protection examples using `Depends(current_user)`
   - Token refresh implementation with client-side handling
   - Security considerations (token lifetime, secret management)

4. **Problem Solving and Solutions**:
   - Provided framework-specific authentication library recommendations
   - Delivered working code examples for JWT implementation
   - Explained dependency injection for route protection
   - Addressed token refresh security concerns with practical solutions

5. **Pending Items**:
   - No explicit pending items mentioned in the conversation

6. **Current Focus**:
   The conversation concluded with token refresh implementation, covering both server-side JWT refresh endpoints and client-side automatic token renewal strategies.

7. **Potential Next Steps**:
   Based on the conversation flow, logical next steps could include:
   - User database setup and configuration
   - Error handling and validation
   - Testing the authentication system
   - Deployment considerations for JWT secrets
</summary>"""

    mock_response.choices[0].message.content = summary
    return mock_response


def demonstrate_compact_functionality():
    """Demonstrate the enhanced compact functionality"""
    console = Console()

    console.print(
        "\n[bold blue]🚀 Enhanced LoopLM Compact Functionality Demo[/bold blue]\n"
    )

    # Create sample session
    console.print(
        "[bold green]1. Creating sample session with realistic conversation...[/bold green]"
    )
    session = create_sample_session()

    # Show original session stats
    console.print(f"\n[dim]Original session: {len(session.messages)} messages[/dim]")

    # Create compact handler
    console.print("\n[bold green]2. Setting up CompactHandler...[/bold green]")

    # Mock the PromptManager
    mock_prompt_manager = Mock()
    mock_prompt_manager.get_prompt.return_value = (
        "Please provide a comprehensive summary..."
    )

    # Create a mock ChatConsole that wraps the Rich Console
    mock_chat_console = Mock()
    mock_chat_console.console = console
    mock_chat_console.display_error = lambda msg: console.print(
        f"[red]Error: {msg}[/red]"
    )
    mock_chat_console.display_success = lambda msg: console.print(
        f"[green]{msg}[/green]"
    )
    mock_chat_console.display_info = lambda msg, style="blue": console.print(
        f"[{style}]{msg}[/{style}]"
    )

    compact_handler = CompactHandler(mock_chat_console, mock_prompt_manager)

    # Show session info before compact
    console.print(
        "\n[bold green]3. Session information before compacting:[/bold green]"
    )
    compact_handler.show_compact_info(session)

    # Test compact validation
    console.print(
        "\n[bold green]4. Validating session can be compacted...[/bold green]"
    )
    can_compact, reason = compact_handler.can_compact(session)
    console.print(f"Can compact: [green]{can_compact}[/green] - {reason}")

    # Mock the LLM call for demo
    console.print(
        "\n[bold green]5. Compacting session (mocked LLM call)...[/bold green]"
    )

    # Temporarily patch the completion function
    import looplm.chat.compact_handler as compact_module

    original_completion = getattr(compact_module, "completion", None)
    compact_module.completion = mock_llm_completion

    try:
        success = compact_handler.compact_session(session, show_progress=False)
        if success:
            console.print("[green]✓ Session compacted successfully![/green]")
        else:
            console.print("[red]✗ Failed to compact session[/red]")
    finally:
        # Restore original function if it existed
        if original_completion:
            compact_module.completion = original_completion

    # Show session info after compact
    console.print("\n[bold green]6. Session information after compacting:[/bold green]")
    compact_handler.show_compact_info(session)

    # Demonstrate context for API calls
    console.print("\n[bold green]7. Context sent to LLM before compact:[/bold green]")
    session.reset_compact()  # Reset to show full context
    full_context = session.get_messages_for_api()
    console.print(f"[dim]Messages: {len(full_context)}[/dim]")

    console.print("\n[bold green]8. Context sent to LLM after compact:[/bold green]")
    session.set_compact_summary(
        session.compact_summary or "Test summary"
    )  # Restore compact state
    compact_context = session.get_messages_for_api()
    console.print(f"[dim]Messages: {len(compact_context)}[/dim]")

    # Add new message after compact
    console.print("\n[bold green]9. Adding new message after compact...[/bold green]")
    session.messages.append(
        Message("user", "How do I deploy this to production?", timestamp=datetime.now())
    )

    final_context = session.get_messages_for_api()
    console.print(f"[dim]Final context: {len(final_context)} messages[/dim]")

    # Demonstrate reset functionality
    console.print("\n[bold green]10. Resetting compact state...[/bold green]")
    compact_handler.reset_compact(session)

    console.print("\n[bold blue]✨ Demo completed successfully![/bold blue]")
    console.print(
        "\n[dim]The compact functionality reduces token usage while preserving[/dim]"
    )
    console.print(
        "[dim]the complete conversation history for session management.[/dim]\n"
    )


if __name__ == "__main__":
    demonstrate_compact_functionality()
