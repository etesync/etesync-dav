class HttpException(Exception):
    pass


class UnauthorizedException(HttpException):
    pass


class UserInactiveException(HttpException):
    pass


class ServiceUnavailableException(HttpException):
    pass


class VersionTooNew(Exception):
    pass


class SecurityException(Exception):
    pass


class IntegrityException(SecurityException):
    pass


class DoesNotExist(Exception):
    pass
