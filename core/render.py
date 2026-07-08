from fastapi import Request
from core.templates import templates

# Helper function for rendering the content of different pages from the admin
def render_section(
    request: Request,
    full_template: str,
    fragment_template: str,
    context: dict,
):
    """
    Render an admin-panel section.

    - Direct navigation / refresh / bookmark -> full page (layout + content)
    - htmx nav click (HX-Request header present) -> the content fragment
      that gets swapped into #main-content
    """
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        request=request,
        name=fragment_template if is_htmx else full_template,
        context=context,
    )