
from typing import Any
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from interface.work.accountWork import TOKEN_KEY, SESSION_TTL, AccountWork, SessionInfo, WorkResult



accountWork             = AccountWork()
accountServiceRouter    = APIRouter(prefix='/account-service', tags=['account-service'])


async def shutdownHook() -> None:
    '''
    释放本微服务持有的数据库与缓存连接

    由应用生命周期钩子在退出阶段统一调用，仅处理本服务资源

    Returns:
        None: 无返回值
    '''
    await accountWork.close()



def _makeResponse(code: int, msg: str, content: Any, token: str | None = None) -> JSONResponse:
    '''
    构建统一的 JSON 响应对象，可同时下发会话 Cookie

    Args:
        code: 业务错误码，0 表示成功
        msg: 结果说明信息
        content: 业务数据，无数据时为 None
        token: 会话令牌，不为 None 时写入响应 Cookie

    Returns:
        JSONResponse: 携带统一响应结构的 HTTP 响应
    '''
    response: JSONResponse = JSONResponse(
        status_code=200,
        content={
            'code': code,
            'msg': msg,
            'content': content
        }
    )
    if token is not None:
        _setSessionCookie(response, token)
    return response


async def _parseBody(request: Request) -> tuple[dict[str, Any] | None, JSONResponse | None]:
    '''
    解析请求体中的 JSON 数据

    Args:
        request: FastAPI 请求对象

    Returns:
        tuple[dict[str, Any] | None, JSONResponse | None]: 解析成功且为对象时
        返回（body, None），否则返回（None, 错误响应对象）
    '''
    try:
        body: Any = await request.json()
        if not isinstance(body, dict):
            return None, _makeResponse(1003, '请求体类型不正确', None)
        return body, None # type: ignore
    except Exception:
        return None, _makeResponse(1001, '请求体解析失败', None)


def _checkBody(body: dict[str, Any], expectedFields: dict[str, type]) -> tuple[int, str] | None:
    '''
    校验请求体字段的存在性与类型

    Args:
        body: 已解析的请求体
        expectedFields: 期望字段名到期望类型的映射

    Returns:
        tuple[int, str] | None: 校验通过返回 None，
        否则返回（错误码, 错误信息）
    '''
    for fieldName, fieldType in expectedFields.items():
        if fieldName not in body:
            return (1001, f'缺少参数：{fieldName}')
        if not isinstance(body[fieldName], fieldType):
            return (1003, f'参数类型不正确：{fieldName}')
    return None


def _setSessionCookie(response: Response, token: str) -> None:
    '''
    将会话令牌写入响应 Cookie

    Args:
        response: FastAPI 响应对象
        token: 会话令牌

    Returns:
        None: 无返回值
    '''
    # 部署 HTTPS 时 secure 需置为 True
    response.set_cookie(
        key=TOKEN_KEY,
        value=token,
        httponly=True,
        max_age=SESSION_TTL,
        samesite='lax',
        path='/',
        secure=False
    )


async def _requireLogin(request: Request) -> tuple[SessionInfo | None, JSONResponse | None]:
    '''
    校验请求是否已登录并解析会话信息

    Args:
        request: FastAPI 请求对象

    Returns:
        tuple[SessionInfo | None, JSONResponse | None]: 已登录时返回（会话信息, None），
        未登录时返回（None, 未登录错误响应）
    '''
    token: str | None = request.cookies.get(TOKEN_KEY)
    sessionInfo: SessionInfo | None = await accountWork.authenticate(token)
    if sessionInfo is None:
        return None, _makeResponse(2001, '未登录', None)
    return sessionInfo, None



@accountServiceRouter.post('/accounts')
async def registerAccount(request: Request) -> JSONResponse:
    '''
    注册并登录新账户

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    body: dict[str, Any] | None
    errorResponse: JSONResponse | None
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(
        body, {'email': str, 'password': str, 'userName': str}
    )
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await accountWork.registerAccount(
        email=body['email'],
        password=body['password'],
        userName=body['userName']
    )
    return _makeResponse(result.code, result.msg, result.content, result.token)


@accountServiceRouter.post('/sessions')
async def loginAccount(request: Request) -> JSONResponse:
    '''
    登录已注册账户

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    body: dict[str, Any] | None
    errorResponse: JSONResponse | None
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(
        body, {'email': str, 'password': str}
    )
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await accountWork.loginAccount(
        email=body['email'],
        password=body['password']
    )
    return _makeResponse(result.code, result.msg, result.content, result.token)


@accountServiceRouter.patch('/accounts/me/name')
async def changeUserName(request: Request) -> JSONResponse:
    '''
    修改当前账户的用户名称

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    body: dict[str, Any] | None
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'userName': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await accountWork.changeUserName(
        accountId=sessionInfo.id,
        userName=body['userName']
    )
    return _makeResponse(result.code, result.msg, result.content)


@accountServiceRouter.patch('/accounts/me/password')
async def changePassword(request: Request) -> JSONResponse:
    '''
    修改当前账户密码并重新下发会话 Cookie

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    body: dict[str, Any] | None
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(
        body, {'oldPassword': str, 'newPassword': str}
    )
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await accountWork.changePassword(
        accountId=sessionInfo.id,
        oldPassword=body['oldPassword'],
        newPassword=body['newPassword'],
        oldToken=request.cookies.get(TOKEN_KEY)
    )
    return _makeResponse(result.code, result.msg, result.content, result.token)


@accountServiceRouter.get('/accounts/me/admin')
async def getIsAdmin(request: Request) -> JSONResponse:
    '''
    获取当前账户是否为组管理员

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await accountWork.getIsAdmin(accountId=sessionInfo.id)
    return _makeResponse(result.code, result.msg, result.content)


@accountServiceRouter.get('/groups/{groupId}/members')
async def getGroupMembers(request: Request, groupId: str) -> JSONResponse:
    '''
    获取指定组内的全部成员信息

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await accountWork.getGroupMembers(
        accountId=sessionInfo.id,
        groupId=groupId
    )
    return _makeResponse(result.code, result.msg, result.content)


@accountServiceRouter.get('/groups')
async def getAllGroups(request: Request) -> JSONResponse:
    '''
    获取系统中的全部组信息

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await accountWork.getAllGroups()
    return _makeResponse(result.code, result.msg, result.content)


@accountServiceRouter.post('/groups/{groupId}/join-requests')
async def createJoinRequest(request: Request, groupId: str) -> JSONResponse:
    '''
    发起加入指定组的请求

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await accountWork.createJoinRequest(
        accountId=sessionInfo.id,
        groupId=groupId
    )
    return _makeResponse(result.code, result.msg, result.content)


@accountServiceRouter.get('/groups/{groupId}/join-requests')
async def getJoinRequests(request: Request, groupId: str) -> JSONResponse:
    '''
    获取申请加入指定组的请求列表

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await accountWork.getJoinRequests(groupId=groupId)
    return _makeResponse(result.code, result.msg, result.content)


@accountServiceRouter.patch('/groups/{groupId}/join-requests/{userId}')
async def reviewJoinRequest(request: Request, groupId: str, userId: str) -> JSONResponse:
    '''
    审批加入组的请求

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        userId: 申请者的账户标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    body: dict[str, Any] | None
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'status': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await accountWork.reviewJoinRequest(
        accountId=sessionInfo.id,
        groupId=groupId,
        userId=userId,
        status=body['status']
    )
    return _makeResponse(result.code, result.msg, result.content)


@accountServiceRouter.delete('/groups/{groupId}/members/me')
async def leaveGroup(request: Request, groupId: str) -> JSONResponse:
    '''
    退出指定组

    Args:
        request: FastAPI 请求对象
        groupId: 请求退出的组标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await accountWork.leaveGroup(
        accountId=sessionInfo.id,
        groupId=groupId
    )
    return _makeResponse(result.code, result.msg, result.content)







