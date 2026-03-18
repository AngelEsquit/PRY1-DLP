from __future__ import annotations


def format_user_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return f"No se encontró el archivo: {exc.filename or ''}".strip()
    if isinstance(exc, PermissionError):
        return f"Permiso denegado al acceder a: {exc.filename or ''}".strip()
    if isinstance(exc, UnicodeDecodeError):
        return "El archivo no está codificado en UTF-8 válido."
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, OSError):
        return str(exc)
    return "Error inesperado durante la ejecución."


def render_user_error(exc: Exception) -> str:
    return f"Error: {format_user_error(exc)}"
