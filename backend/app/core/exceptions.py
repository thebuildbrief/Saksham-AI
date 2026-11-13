"""HTTP exceptions used by API and service layers."""
from fastapi import HTTPException


class SakshamException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(SakshamException):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(404, f"{entity} '{entity_id}' was not found")


class ForbiddenException(SakshamException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(403, detail)
