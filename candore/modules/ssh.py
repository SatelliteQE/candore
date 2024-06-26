from hussh import Connection
from functools import cached_property
from candore.config import candore_settings
from urllib.parse import urlparse


class Session:

    def __init__(self, settings=None):
        self.settings = settings
        self.hostname = urlparse(settings.candore.base_url).hostname
        self.username = settings.candore.ssh.username or 'root'

    @cached_property
    def auth(self):
        auth_kwargs = {}
        if self.settings.candore.ssh.private_key:
            auth_kwargs["private_key"] = self.settings.candore.ssh.private_key
        elif self.settings.candore.ssh.password:
            auth_kwargs["password"] = self.settings.candore.ssh.password
        return auth_kwargs

    def __enter__(self):
        self.client = Connection(self.hostname, username=self.username, **self.auth)
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
