def create_error_response(message, code, details=None):
    """Create standardized error response"""
    response = {
        "error": {
            "message": message,
            "code": code
        }
    }
    if details:
        response["error"]["details"] = details
    return response