class HTTPStatus:
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


class MessageTypes:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ServiceTypes:
    INDIVIDUAL_THERAPY = "individual_therapy"
    GROUP_THERAPY = "group_therapy"
    PSYCHIATRY = "psychiatry"
    CRISIS_SUPPORT = "crisis_support"
    SUBSTANCE_ABUSE = "substance_abuse"
    FAMILY_THERAPY = "family_therapy"


class ChatStates:
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


API_PREFIX = "/api/v1"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100