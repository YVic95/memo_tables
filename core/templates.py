from fastapi.templating import Jinja2Templates
from country_flags import get_flag

templates = Jinja2Templates(directory="templates")
templates.env.filters["flag"] = get_flag