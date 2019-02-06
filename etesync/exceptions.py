class HttpException(Exception):
    pass


class UnauthorizedException(HttpException):
    pass


class UserInactiveException(HttpException):
    pass


class ServiceUnavailableException(HttpException):
    pass


class HttpNotFound(HttpException):
    pass


class VersionTooNew(Exception):
    pass


class SecurityException(Exception):
    pass


class IntegrityException(SecurityException):
    pass


class StorageException(Exception):
    pass


class DoesNotExist(StorageException):
    pass


class AlreadyExists(StorageException):
    pass


class TypeMismatch(StorageException):
    pass
