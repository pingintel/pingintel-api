import configparser
import logging
import os
import pathlib
from typing import IO, Collection, overload

import click
import requests
import requests
from requests.adapters import HTTPAdapter, Retry

from .utils import is_fileobj, censor

from pingintel_api.__about__ import __version__


class AuthTokenNotFound(Exception):
    pass


class APIClientBase:
    api_subdomain: str
    api_base_domain: str
    auth_token_env_name: str
    product: str
    include_legacy_dashes: bool = False

    @overload
    def __init__(self, api_url: str, environment: str | None = None, auth_token=None) -> None:
        """Initialize the API client with an API URL and an optional auth token.

        :param api_url: The URL of the API.  e.g. "https://vision.pingintel.com"
        """
        ...

    @overload
    def __init__(self, environment: str = "prod", auth_token=None) -> None: ...

    def __init__(
        self,
        api_url: str | None = None,
        environment: str | None = "prod",
        auth_token=None,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)

        if api_url is None and environment is None:
            environment = "prod"

        if api_url is None:
            if environment is None:
                raise ValueError("Need either api_url or environment.")
            api_url = self.get_api_url_by_environment(environment)

        env_var = None
        if not auth_token and environment:
            env_var, auth_token = self.get_auth_token_by_environment(environment)
            if auth_token:
                self.logger.debug(f"Using auth token from {env_var}: {censor(auth_token, 5)}")
        if not auth_token:
            auth_token = os.environ.get(self.auth_token_env_name)
            if auth_token:
                self.logger.debug(f"Using auth token from {self.auth_token_env_name}: {censor(auth_token, 5)}")
        serverspace = None
        if not auth_token:
            config = configparser.ConfigParser()
            config.read(os.path.expanduser("~/.pingintel.ini"))
            if environment:
                serverspace = self.get_serverspace_from_environment(environment)
                try:
                    auth_token = config.get(self.product, f"{self.auth_token_env_name}_{serverspace.upper()}")
                    if auth_token:
                        self.logger.debug(
                            f"Using auth token from '~/.pingintel.ini', [{self.product}] {self.auth_token_env_name}_{serverspace.upper()}: {censor(auth_token, 5)}"
                        )
                except (configparser.NoOptionError, configparser.NoSectionError):
                    pass
            if not auth_token:
                try:
                    auth_token = config.get(self.product, self.auth_token_env_name)
                    if auth_token:
                        self.logger.debug(
                            f"Using auth token from '~/.pingintel.ini', [{self.product}] {self.auth_token_env_name}: {censor(auth_token, 5)}"
                        )
                except (configparser.NoOptionError, configparser.NoSectionError):
                    pass

        if not auth_token:
            s = []
            s.append(f"No auth_token was found.  Please provide it via:")
            s.append(f"   * --auth-token on commandline")
            s.append(f"   * {self.auth_token_env_name} environment variable")
            s.append(f"   * In ~/.pingintel.ini, under [{self.product}] as {self.auth_token_env_name}")
            s.append(
                f"   * In ~/.pingintel.ini, under [{self.product}] as {self.auth_token_env_name}_{(serverspace or '<environment>').upper()}"
            )

            raise AuthTokenNotFound("\n".join(s))
        assert api_url
        self.api_url = api_url
        self.auth_token = auth_token
        self.environment = environment if api_url is None else None
        self.session = self._create_session()

    def get(self, url, **kwargs):
        self.logger.debug(f"GET {url}")
        return self.session.get(url, **kwargs)

    def post(self, url, **kwargs):
        self.logger.debug(f"POST {url}")
        if "data" in kwargs:
            self.logger.debug(f"POST data: {kwargs['data']}")
        return self.session.post(url, **kwargs)

    def patch(self, url, **kwargs):
        self.logger.debug(f"PATCH {url}")
        if "data" in kwargs:
            self.logger.debug(f"PATCH data: {kwargs['data']}")
        return self.session.patch(url, **kwargs)

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
                return f"https://{self.api_subdomain}-{environment}.{self.api_base_domain}"
        else:
            return f"https://{self.api_subdomain}.{environment}.{self.api_base_domain}"

    def get_auth_token_by_environment(self, environment: str) -> str:
        serverspace = self.get_serverspace_from_environment(environment)
        env_var = f"{self.auth_token_env_name}_{serverspace}".upper()
        # env_var = f"PING_{serverspace}_AUTH_TOKEN".upper()
        auth_token = os.environ.get(env_var)
        return env_var, auth_token

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
    def _get_files_for_request(
        cls, file: IO[bytes] | str | pathlib.Path | Collection[IO[bytes] | str | pathlib.Path], filename=None
    ) -> list[tuple[str, tuple[str, IO[bytes]]]]:
        if is_fileobj(file) or isinstance(file, (str, pathlib.Path)):
            # if it's a singular input...
            files = [(file, filename)]
        else:
            if filename is None:
                filename = [None] * len(file)
            if len(file) != len(filename):
                raise ValueError("Length of file and filename must be the same.")

            files = [(_, fname) for _, fname in zip(file, filename)]

        ret = []
        for f, fname in files:
            # files = [('file', open('report.xls', 'rb')), ('file', open('report2.xls', 'rb'))]
            if is_fileobj(f):
                if fname is None:
                    raise ValueError("Need filename if file is a file object.")

                ret.append(("file", (fname, f)))
            else:
                assert isinstance(f, (str, pathlib.Path)), f"Expected str or pathlib.Path, got {type(f)}"
                if not os.path.exists(f):
                    raise click.ClickException(f"Path {f} does not exist.")

                ret.append(("file", open(f, "rb")))
        return ret
