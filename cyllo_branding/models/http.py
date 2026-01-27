# -*- coding: utf-8 -*-
import collections.abc

from werkzeug.exceptions import (NotFound)

from odoo.http import JsonRPCDispatcher, serialize_exception, SessionExpiredException


class RPCDispatcher(JsonRPCDispatcher):
    """A dispatcher class for handling JSON-RPC requests.

    This class extends JsonRPCDispatcher and provides additional functionality
    for handling errors and dispatching requests of type 'json'."""
    routing_type = 'json'

    def handle_error(self, exc: Exception) -> collections.abc.Callable:
        """
        Handle any exception that occurred while dispatching a request to
        a `type='json'` route. Also handle exceptions that occurred when
        no route matched the request path, that no fallback page could
        be delivered and that the request ``Content-Type`` was json.

        :param exc: the exception that occurred.
        :returns: a WSGI application
        """
        error = {
            'code': 200,  # this code is the JSON-RPC level code, it is distinct from the HTTP status code. This
                          # code is ignored and the value 200 (while misleading) is totally arbitrary.
            'message': "Cyllo Server Error",
            'data': serialize_exception(exc),
        }
        if isinstance(exc, NotFound):
            error['code'] = 404
            error['message'] = "404: Not Found"
        elif isinstance(exc, SessionExpiredException):
            error['code'] = 100
            error['message'] = "Cyllo Session Expired"
        return self._response(error=error)
