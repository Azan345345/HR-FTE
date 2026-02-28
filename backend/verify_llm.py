try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("SUCCESS: langchain-google-genai imported")
except ImportError:
    print("ERROR: langchain-google-genai NOT found")

try:
    from langchain_groq import ChatGroq
    print("SUCCESS: langchain-groq imported")
except ImportError:
    print("ERROR: langchain-groq NOT found")
