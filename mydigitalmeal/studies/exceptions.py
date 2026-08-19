from django.http import Http404


class StudyProjectNotFoundError(Http404):
    """Raised when a study project_id is missing, unregistered, or unknown."""

    def __init__(self, message="Study project not found."):
        super().__init__(message)


class ProjectNotRegisteredAsStudyError(Http404):
    """Raised when a project exists but isn't registered as a study project."""

    def __init__(self, message="Project not registered as a study project."):
        super().__init__(message)


class ProjectInactiveError(Http404):
    """Raised when a project is set to inactive."""

    def __init__(self, message="Project is inactive."):
        super().__init__(message)
