import json
from abc import ABCMeta
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import tornado
import tornado.web
from torngithub import json_decode

from user_account_helpers import *

MAX_WORKERS = 16


class Endpoint(Enum):
    """
    An Enum to distinguish push from pull APIs.
    Push APIs need to validate the user's API key.
    """

    PUSH_API = 1
    PULL_API = 2


class BaseHandler(tornado.web.RequestHandler):
    """
    A handler that all Brainspell handlers should extend.

    All class names should be CamelCase.

    JSON endpoints should:
    1) be named [*]EndpointHandler,
    2) specify the "parameters" dictionary,
    3) override the "process" function, and
    4) specify the "endpoint_type" using the Endpoint enum.

    The resulting API endpoint will be the hyphenated form of the name.
    e.g., SplitTableEndpointHandler => /json/split-table

    You can view the parameters for any JSON endpoint at /json/*/help.
    e.g., /json/split-table/help

    Specifying the "parameters" dictionary:

    parameters ::= {
        parameter_name: {
            "type": parseFn
        }
        ...
    }

    where "type" is a key mapped to a function that can be used to parse
    a string into the desired type. e.g.,
    parseFn ::= str | int | float | json.loads | ...

    If a parameter is optional, you can indicate that by including a default value:

    parameters ::= {
        parameter_name: {
            "type": int,
            "default": 0
        }
        ...
    }

    The "process" function:

    "process" function signature:
    def process(self, response, args)

    By default, "response" is a dictionary that contains a key
    called "success" with a value of 1. The process function should
    mutate the "response" dictionary as necessary and return it (unless
    it is an asynchronous endpoint, described below).

    "args" is a dictionary with parameter values, such that the keys
    are those specified in the "parameters" dictionary.

    The "endpoint_type" enum:

    endpoint_type ::= Endpoint.PULL_API | Endpoint.PUSH_API

    If "endpoint_type" is set to Endpoint.PUSH_API, then there
    will be one additional required parameter: the "key" parameter,
    which is the user's API key. This key will be automatically validated
    before the "process" function is called, and it will be included in
    the "args" dict.

    Asynchronous endpoints:
    If your endpoint is going to block the main thread for a reasonable
    period of time, please make it asynchronous. It's as easy as setting
    the "asynchronous" boolean, decorating your "process" function with
    @tornado.gen.coroutine, and calling self.finish_async when your
    function finishes execution (MANDATORY). Then, any blocking code
    should be decorated with @run_on_executor.

    asynchronous :: True | False

    @run_on_executor
    def blocker(self):
        # blocking code here
        ...

    @tornado.gen.coroutine
    def process(self, response, args):
        blocked_result = yield self.blocker()
        ...
        self.finish_async(response)

    Web interface handlers should be named [*]Handler, and use the
    "render_with_user_info" function (rather than self.render).

    The following variables will be included for use by the Tornado
    HTML template:
    - "github_name"
    - "github_username"
    - "github_avatar"
    - "github_access_token"
    - "api_key"
    """

    parameters = None
    endpoint_type = None
    process = None

    asynchronous = False
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def get_safe_arguments(self, arguments_dict, accessor):
        """ Enforce type safety; do not verify API key. """

        args = {}
        for k in self.parameters:
            if k not in arguments_dict:
                if "default" not in self.parameters[k]:
                    return {
                        "success": 0,
                        "description": "Missing required parameter: " + k
                    }
                else:
                    args[k] = self.parameters[k]["type"](
                        self.parameters[k]["default"])
            else:
                try:
                    args[k] = self.parameters[k]["type"](accessor(k))
                except BaseException:
                    return {
                        "success": 0,
                        "description": "Bad input for argument (type " +
                        self.parameters[k]["type"].__name__ +
                        "): " +
                        k
                    }

        if self.endpoint_type == Endpoint.PUSH_API or (
                "key" in self.request.arguments):
            try:
                args["key"] = str(accessor("key"))
            except BaseException:
                args["key"] = ""

        return {
            "success": 1,
            "args": args
        }

    @tornado.gen.coroutine
    @tornado.web.asynchronous
    def get(self):
        """
        Provide a guarantee for a valid API key on PUSH endpoints,
        documentation at /help, and type-checked arguments.
        """

        assert self.endpoint_type, "You must indicate what type of endpoint this is by setting the endpoint_type variable."
        self.set_header("Content-Type", "application/json")

        assert self.parameters is not None, "You haven't indicated the parameters for this endpoint."

        # provide help documentation
        components = [x for x in self.request.path.split("/") if x]
        if len(components) >= 3 and components[2] == "help":
            formatted_parameters = {}
            for p in self.parameters:
                formatted_parameters[p] = {}
                if "default" not in self.parameters[p]:
                    formatted_parameters[p]["required"] = True
                else:
                    formatted_parameters[p]["required"] = False
                    formatted_parameters[p]["default"] = self.parameters[p]["default"]
                type_name = self.parameters[p]["type"].__name__
                if type_name == "loads":  # account for loads function
                    type_name = "json"
                formatted_parameters[p]["type"] = type_name
                if "description" in self.parameters[p]:
                    formatted_parameters[p]["description"] = self.parameters[p]["description"]
            if self.endpoint_type == Endpoint.PUSH_API:
                formatted_parameters["key"] = {}
                formatted_parameters["key"]["required"] = True
                formatted_parameters["key"]["type"] = str.__name__
            self.finish_async({
                "success": 1,
                "parameters": formatted_parameters
            })
        else:
            # type check arguments
            argsDict = self.get_safe_arguments(
                self.request.arguments, self.get_argument)
            if argsDict["success"] == 1:
                # validate API key if push endpoint
                if self.endpoint_type == Endpoint.PULL_API or (
                    self.endpoint_type == Endpoint.PUSH_API and valid_api_key(
                        argsDict["args"]["key"])):
                    response = {"success": 1}
                    if not self.asynchronous:
                        response = self.process(response, argsDict["args"])
                        self.finish_async(response)
                    else:
                        self.process(response, argsDict["args"])
                else:
                    self.finish_async(
                        {"success": 0, "description": "That API key is not valid."})
            else:
                # print the error message from argument parsing
                self.finish_async(argsDict)

    post = get

    def finish_async(self, response):
        """ Write the response dictionary, and finish this asynchronous call. """

        self.write(json.dumps(response))
        self.finish()

    def render_with_user_info(self, url, params={}):
        """
        Render a Tornado HTML template, automatically
        appending user information.
        Do NOT mutate the params dict.
        """

        login_dict = {
            "github_name": self.get_current_github_name(),
            "github_username": self.get_current_github_username(),
            "github_avatar": self.get_current_github_avatar(),
            "github_access_token": self.get_current_github_access_token(),
            "api_key": self.get_current_api_key()
        }
        for k in params:
            # rather than passing both dicts, make it 3.4 compatible by merging
            login_dict[k] = params[k]
        self.render(url, **login_dict)

    def __get_current_github_object__(self):
        """
        Return an object representing the user's name, avatar, and
        access_token, or None is the user is not logged in.
        Technically a "private" method; please use the get_current_* methods.
        """

        try:
            return json_decode(self.get_secure_cookie("user"))
        except BaseException:
            return None

    def get_current_github_name(self):
        """ Get the user's name from GitHub. """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["name"]
        return ""

    def get_current_github_username(self):
        """
        Get the user's GitHub username. Guaranteed to exist iff logged in.
        """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["login"]
        return ""

    def get_current_github_avatar(self):
        """ Get the user's avatar from GitHub. """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["avatar_url"]
        return ""

    def get_current_github_access_token(self):
        """
        Get the user's access token from GitHub. Guaranteed to exist iff logged in.
        """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["access_token"]
        return ""

    def get_current_api_key(self):
        """
        Get the user's API key. Guaranteed to exist iff logged in.
        """

        return self.get_secure_cookie("api_key")

    def set_default_headers(self):
        """
        Set the headers to allow JS API requests. Potentially a security concern.
        """

        origin = self.request.headers.get('Origin')
        if origin:
            self.set_header('Access-Control-Allow-Origin', origin)
        self.set_header('Access-Control-Allow-Credentials', 'true')


class AbstractEndpoint(metaclass=ABCMeta):
    """ An abstract class to enforce the structure of API endpoints. """

    def register(subclass):
        """
        Enforce the API specification described in BaseHandler.
        Called by the "brainspell" module on all API endpoints.
        """

        assert subclass.endpoint_type, "The class " + subclass.__name__ + \
            " does not indicate what type of endpoint it is (using the endpoint_type variable). Please reimplement the class to conform to this specification."
        assert subclass.process, "The class " + subclass.__name__ + \
            " does not override the \"process\" function. Please reimplement the class to conform to this specification."
        assert subclass.parameters is not None, "The class " + subclass.__name__ + \
            " does not specify its parameters. Please reimplement the class to conform to this specification."
