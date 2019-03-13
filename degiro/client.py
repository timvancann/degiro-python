import functools
import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import List

from requests import Session, Response
from functional import seq

logger = logging.getLogger(__name__)


def log_request(f):
    @functools.wraps(f)
    def wrapper_decorator(*args, **kwargs):
        response = f(*args, **kwargs)
        logger.info(f"Status code: {response.status_code}")
        if response.status_code not in (200, 201, 204):
            logger.error(response.text)
        return response

    return wrapper_decorator


@dataclass(frozen=True)
class Endpoint(object):
    http_type: str
    url: str
    params: List[str] = field(default_factory=lambda: [])


class DeGiro:
    ROOT_URL = "https://trader.degiro.nl"

    _LOGIN = Endpoint(
        "POST",
        f"{ROOT_URL}/login/secure/login",
        ["username", "password", "isPassCodeReset", "isRedirectToMobile"],
    )
    CLIENT = Endpoint("GET", f"{ROOT_URL}/pa/secure/client", ["sessionId"])
    TRANSACTIONS = Endpoint(
        "GET",
        f"{ROOT_URL}/reporting/secure/v4/transactions",
        ["sessionId", "intAccount", "fromDate", "toDate"],
    )
    PRODUCTS = Endpoint(
        "POST",
        f"{ROOT_URL}/product_search/secure/v5/products/info?sessionId={{session_id}}&intAccount={{account_id}}",
    )
    PORTFOLIO = Endpoint(
        "GET",
        f"{ROOT_URL}/trading/secure/v5/update/{{account_id}};jsessionid={{session_id}}",
        ["portfolio", "totalPortfolio"],
    )

    def __init__(self, username, password):
        self.username = username
        self.password = password

    @staticmethod
    @log_request
    def _perform_post(
        session: Session, endpoint: Endpoint, override_url: str = None, override_payload=None, **params
    ) -> Response:
        params_ = {_: params[_] for _ in endpoint.params}
        url = endpoint.url if not override_url else override_url
        logger.debug(f"Performing POST to {url} with {params_}")
        headers = {"content-type": "application/json"}
        return session.post(
            url, headers=headers, data=json.dumps(params_ if not override_payload else override_payload)
        )

    @staticmethod
    @log_request
    def _perform_get(session: Session, endpoint: Endpoint, override_url: str = None, **params) -> Response:
        params_ = {_: params[_] for _ in endpoint.params}
        url = endpoint.url if not override_url else override_url
        logger.info(f"Performing GET to {url} with {params_}")
        return session.get(url, params=params_)

    def login(self, session: Session) -> str:
        """Login user to DeGiro and return session id.

        :param session: A requests.Session object
        :return: the current session id
        """
        payload = {
            "username": self.username,
            "password": self.password,
            "isPassCodeReset": False,
            "isRedirectToMobile": False,
        }

        response = self.query_endpoint(session, self._LOGIN, **payload)
        session_id = self._get_session_id(response.headers)
        return session_id

    @staticmethod
    def _get_session_id(response_headers: dict) -> str:
        try:
            return response_headers["Set-Cookie"].split(";")[0].split("=")[1]
        except (IndexError, KeyError) as e:
            logger.info("Could not find session id from header", e)

    def account_data(self, session: Session, session_id: str) -> (str, dict):

        response = self.query_endpoint(session=session, endpoint=self.CLIENT, sessionId=session_id)

        data = self._get_root_json(response)
        return (self._get_account_id(data), data)

    @staticmethod
    def _get_root_json(response: Response):
        return response.json()["data"]

    @staticmethod
    def _get_account_id(data: dict):
        return data["intAccount"]

    def query_endpoint(self, session: Session, endpoint: Endpoint, **kwargs):
        if endpoint.http_type == "GET":
            return self._perform_get(session=session, endpoint=endpoint, **kwargs)
        elif endpoint.http_type == "POST":
            return self._perform_post(session=session, endpoint=endpoint, **kwargs)

    def transactions(self, session, session_id, account_id, from_date: date, to_date: date):
        response = self.query_endpoint(
            session=session,
            endpoint=self.TRANSACTIONS,
            sessionId=session_id,
            intAccount=account_id,
            fromDate=from_date.strftime("%d/%m/%Y"),
            toDate=to_date.strftime("%d/%m/%Y"),
        )

        transactions = self._get_root_json(response)

        ids = [_["productId"] for _ in transactions]
        products = self.products(session, session_id, account_id, ids)

        for t in transactions:
            t["product"] = products[str(t["productId"])]
            del (t["productId"])

        return transactions

    def products(self, session, session_id, account_id, ids):
        response = self._perform_post(
            session=session,
            endpoint=self.PRODUCTS,
            override_url=self.PRODUCTS.url.format(session_id=session_id, account_id=account_id),
            override_payload=ids,
        )
        return self._get_root_json(response)

    def portfolio(self, session, session_id, account_id):
        response = self._perform_get(
            session=session,
            endpoint=self.PORTFOLIO,
            override_url=self.PORTFOLIO.url.format(session_id=session_id, account_id=account_id),
            portfolio=0,
            totalPortfolio=0,
        )

        def unpack(lst_of_dict):
            return {_["name"]: _["value"] for _ in lst_of_dict if "value" in _.keys()}

        values = (
            seq(response.json()["portfolio"]["value"])
            .map(lambda x: x["value"])
            .map(unpack)
            .filter(lambda x: x["size"] > 0)
            .to_list()
        )

        ids = [int(_["id"]) for _ in values]
        products = self.products(session, session_id, account_id, ids)

        for v in values:
            v["product"] = products[v["id"]]
            del (v["id"])

        return values
