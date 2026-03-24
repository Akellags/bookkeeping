2026-03-24 13:44:40 - uvicorn.access - INFO - 2401:4900:1cb5:8d7a:cdc9:95ab:7c1e:b241:0 - "GET /api/user/stats?whatsapp_id=919000521868 HTTP/1.1" 500
2026-03-24 13:44:40 - uvicorn.error - ERROR - Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\uvicorn\protocols\http\h11_impl.py", line 410, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\fastapi\applications.py", line 1160, in __call__   
    await super().__call__(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\applications.py", line 107, in __call__  
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
    raise exc
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\middleware\exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\fastapi\middleware\asyncexitstack.py", line 18, in 
__call__
    await self.app(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\routing.py", line 716, in __call__       
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\fastapi\routing.py", line 119, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\fastapi\routing.py", line 105, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\fastapi\routing.py", line 431, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\venv\Lib\site-packages\fastapi\routing.py", line 313, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\ALIENWARE\Projects\helpU\bookkeeper\src\api\frontend.py", line 58, in get_user_stats
    "bills": ledger_stats["count"],
             ~~~~~~~~~~~~^^^^^^^^^
KeyError: 'count'
2026-03-24 13:44:41 - uvicorn.access - INFO - 2401:4900:1cb5:8d7a:cdc9:95ab:7c1e:b241:0 - "GET /api/user/businesses?whatsapp_id=919000521868 HTTP/1.1" 200