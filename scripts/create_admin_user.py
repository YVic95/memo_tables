# creates an admin user in Supabase
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_PROJECT_URL_LOCAL"),
    os.getenv("SUPABASE_SECRET_KEY_LOCAL")
)

response = supabase.auth.admin.create_user({
    "email": os.getenv("ADMIN_EMAIL"),
    "password": os.getenv("ADMIN_PASSWORD"),
    "email_confirm": True  # auto-confirms, no email verification needed
})

print(response)