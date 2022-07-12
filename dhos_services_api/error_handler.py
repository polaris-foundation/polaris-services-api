import neomodel
from flask import Flask
from flask_batteries_included.helpers.error_handler import (
    catch_bad_request,
    catch_database_exception,
    catch_deflate_error,
    catch_internal_error,
    catch_invalid_database_credentials,
    catch_invalid_database_uri,
    catch_not_found,
    catch_query_exception,
)
from neo4j.exceptions import AuthError, CypherError, ServiceUnavailable
from neobolt import addressing


def init_neo4j_error_handler(app: Flask) -> None:

    app.errorhandler(neomodel.RequiredProperty)(catch_bad_request)
    app.errorhandler(neomodel.UniqueProperty)(catch_bad_request)
    app.errorhandler(neomodel.NotConnected)(catch_internal_error)
    app.errorhandler(neomodel.InflateError)(catch_internal_error)
    app.errorhandler(neomodel.exceptions.ConstraintValidationFailed)(
        catch_internal_error
    )
    app.errorhandler(neomodel.DeflateError)(catch_internal_error)
    app.errorhandler(neomodel.MultipleNodesReturned)(catch_internal_error)
    app.errorhandler(neomodel.DoesNotExist)(catch_not_found)

    app.errorhandler(FileNotFoundError)(catch_not_found)
    app.errorhandler(ServiceUnavailable)(catch_database_exception)
    app.errorhandler(CypherError)(catch_query_exception)

    app.errorhandler(neomodel.exceptions.DeflateError)(catch_deflate_error)

    app.errorhandler(AuthError)(catch_invalid_database_credentials)
    app.errorhandler(addressing.AddressError)(catch_invalid_database_uri)
