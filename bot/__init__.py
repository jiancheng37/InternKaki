import os
from dotenv import load_dotenv
from bot.config import init_db

# Load environment variables
load_dotenv()

# Ensure database setup
init_db()
