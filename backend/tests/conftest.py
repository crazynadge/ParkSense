import os

# Tests never call a real Vision provider; environment variables win over backend/.env.
os.environ["VISION_PROVIDER"] = "mock"
