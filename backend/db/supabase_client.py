import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")
service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL or SUPABASE_ANON_KEY missing in .env")

# Use service role key for backend-only admin tasks if available
supabase: Client = create_client(url, service_role_key if service_role_key else key)
