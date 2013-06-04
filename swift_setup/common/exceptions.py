""" See COPYING for license information """


class Error(StandardError):
    """
    Base class for all errors and exceptions
    """
    pass


class ResponseError(Error):
    """
    A General response error
    """
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        Error.__init__(self)

    def __str__(self):
        return '%d - %s' % (self.status, self.reason)

    def __repr__(self):
        return '%d - %s' % (self.status, self.reason)


class HostListError(ResponseError):
    """
    Raised when host list generation fails.
    """
    pass


class ConfigFileError(ResponseError):
    """
    Raised when host list generation fails.
    """
    pass


class ConfigSyncError(ResponseError):
    """
    Raised when issue syncing configs to system's root
    """
    pass


class TemplateFileError(ResponseError):
    """
    Raised when something goes wrong manipulating a template file.
    """
    pass


class DiskSetupError(ResponseError):
    """
    Raised when something goes wrong setting up the disks.
    """
    pass

class UploadTemplatesError(ResponseError):
    """
    Raised when something goes wrong uploading templates
    """
    pass
