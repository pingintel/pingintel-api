import configparser
import os
from typing import overload

import click
import requests
import requests
from requests.adapters import HTTPAdapter, Retry

from .utils import is_fileobj, log

from pingintel_api.__about__ import __version__


class APIClientBase:
    api_subdomain: str
    api_base_domain: str
    auth_token_env_name: str
    product: str
    include_legacy_dashes: bool = False

    @overload
    def __init__(
        self, api_url: str, environment: str | None = None, auth_token=None
    ) -> None:
        """Initialize the API client with an API URL and an optional auth token.

        :param api_url: The URL of the API.  e.g. "https://radar.pingintel.com"
        """
        pass

    @overload
    def __init__(self, environment: str = "prod", auth_token=None) -> None: ...

    def __init__(
        self,
        api_url: str | None = None,
        environment: str | None = "prod",
        auth_token=None,
    ):
        if api_url is None:
            if environment is None:
                raise ValueError("Need either api_url or environment.")
            api_url = self.get_api_url_by_environment(environment)

        if not auth_token and environment:
            auth_token = self.get_auth_token_by_environment(environment)
        if not auth_token:
            auth_token = os.environ.get(self.auth_token_env_name)
        if not auth_token:
            config = configparser.ConfigParser()
            config.read(os.path.expanduser("~/.pingintel.ini"))
            if environment:
                serverspace = self.get_serverspace_from_environment(environment)
                try:
                    auth_token = config.get(
                        self.product, f"{self.auth_token_env_name}_{serverspace}"
                    )
                except (configparser.NoOptionError, configparser.NoSectionError):
                    pass
            if not auth_token:
                try:
                    auth_token = config.get(self.product, self.auth_token_env_name)
                except (configparser.NoOptionError, configparser.NoSectionError):
                    pass

        if not auth_token:
            raise ValueError(
                f"Provide auth_token as a parameter, in ~/.pingintel.ini, or set {self.auth_token_env_name} environment variable."
            )
        assert api_url
        self.api_url = api_url
        self.auth_token = auth_token
        self.environment = environment if api_url is None else None
        self.session = self._create_session()

    def get(self, url, **kwargs):
        log(f"GET {url}")
        return self.session.get(url, **kwargs)

    def post(self, url, **kwargs):
        log(f"POST {url}")
        return self.session.post(url, **kwargs)

    def _create_session(self):
        session = requests.Session()

        session.headers = {
            "Authorization": f"Token {self.auth_token}",
            "Accept-Encoding": "gzip",
            "User-Agent": f"pingintel_api/{self.__class__.__name__}/{__version__}",
        }

        retry = Retry(
            total=10,
            # backoff_factor=0.8,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )
        # retry.DEFAULT_BACKOFF_MAX = random.uniform(25.0, 35.0)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)

        return session

    def get_api_url_by_environment(self, environment: str) -> str:
        if self.include_legacy_dashes:
            if environment == "prod":
                return f"https://{self.api_subdomain}.{self.api_base_domain}"
            elif environment == "prod2":
                return f"https://{self.api_subdomain}2.{self.api_base_domain}"
            elif environment == "prodeu":
                return f"https://{self.api_subdomain}.eu.{self.api_base_domain}"
            elif environment == "local":
                return "http://api-local.sovfixer.com"
            else:
                return (
                    f"https://{self.api_subdomain}-{environment}.{self.api_base_domain}"
                )
        else:
            return f"https://{self.api_subdomain}.{environment}.{self.api_base_domain}"

    def get_auth_token_by_environment(self, environment: str) -> str:
        serverspace = self.get_serverspace_from_environment(environment)
        auth_token = os.environ.get(f"PING_{serverspace}_AUTH_TOKEN".upper())

    def get_serverspace_from_environment(self, environment: str) -> str:
        if environment in ["staging", "staging2"]:
            serverspace = "stg"
        elif environment in ["prod", "prod2"]:
            serverspace = "prd"
        elif environment in ["prodeu", "prodeu2"]:
            serverspace = "prdeu"
        elif environment in ["dev", "dev2"]:
            serverspace = "dev"
        elif environment in ["local", "local2"]:
            serverspace = "local"
        else:
            raise ValueError("Unknown environment.")

        return serverspace

    @classmethod
    def _get_files_for_request(cls, file, filename=None):
        if is_fileobj(file):
            if filename is None:
                raise ValueError("Need filename if file is a file object.")

            return {"file": (filename, file)}
        else:
            if not os.path.exists(file):
                raise click.ClickException(f"Path {file} does not exist.")

            return {"file": open(file, "rb")}
