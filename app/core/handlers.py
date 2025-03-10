from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, FastAPIError


def custom_request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    errors = exc.errors()
    content = []
    print(exc.errors())
    if not errors:
        return JSONResponse(status_code=400, content={'detail': 'Unknown error. Go to file handlers.py'})
    # if errors[0]["type"] == "json_invalid":
    #     status_code = 400
    #     result = dict()
    #     result.update({"type": errors[0]["type"]})
    #     result.update(errors[0]["ctx"])
    #     content.append(result)
    #     return JSONResponse(status_code=status_code, content={"detail": content})
    # elif errors[0]["type"] == "missing":
    #     status_code = 400
    #     content.append({error["loc"][-1]: "Обязательное поле" for error in errors})
    #     return JSONResponse(status_code=status_code, content={"detail": content})
    else:
        status_code = 400
        for error in errors:
            content.append(error)
            # error_type = error.get('type', 'Unknown type')
            # error_msg = error.get('msg', 'No message provided')
            # error_loc = error.get('loc', [])
            # content.append(
            #     {"type_error": error_type, "message": error_msg, "location": error_loc}
            # )
        return JSONResponse(status_code=status_code, content={"detail": content})
