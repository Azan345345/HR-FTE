from app.config import settings

print(f"GOOGLE_AI_API_KEY: {'[SET]' if settings.GOOGLE_AI_API_KEY else '[MISSING]'}")
print(f"GROQ_API_KEY: {'[SET]' if settings.GROQ_API_KEY else '[MISSING]'}")
print(f"DATABASE_URL: {settings.DATABASE_URL}")
print(f"DEBUG: {settings.DEBUG}")
