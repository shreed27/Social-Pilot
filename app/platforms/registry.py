from app.pages import Page
from app.platforms.base import DryRunClient, PlatformClient
from app.platforms.instagram import InstagramClient
from app.platforms.linkedin import LinkedInClient
from app.platforms.x import XClient
from app.settings import get_settings

CLIENTS = {"instagram": InstagramClient, "linkedin": LinkedInClient, "x": XClient}


def client_for(page: Page) -> PlatformClient:
    if not get_settings().live:
        return DryRunClient(page)
    return CLIENTS[page.platform](page)
