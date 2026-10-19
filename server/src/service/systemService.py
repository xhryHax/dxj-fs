
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from interface.tools.networkDomainManager import networkDomainManager
from interface.work.systemWork import SystemWork
from interface.work.workCommon import (
    SESSION_TTL,
    TOKEN_KEY,
    SessionInfo
)



systemWork               = SystemWork()
systemServiceRouter      = APIRouter(prefix='/system-service', tags=['system-service'])


async def startupHook() -> None:
    '''
    系统服务启动钩子，将 serviceConfig.json 中的网络域配置写入 Redis

    由应用生命周期钩子在启动阶段统一调用，仅处理本服务资源

    Returns:
        None: 无返回值
    '''
    _ = await networkDomainManager.syncFromConfig()


async def shutdownHook() -> None:
    '''
    释放本微服务持有的数据库与缓存连接

    由应用生命周期钩子在退出阶段统一调用，仅处理本服务资源

    Returns:
        None: 无返回值
    '''
    await systemWork.close()



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
        rawBody: Any = await request.json()
        if not isinstance(rawBody, dict):
            return None, _makeResponse(1003, '请求体类型不正确', None)
        body: dict[str, Any] = rawBody # type: ignore
        return body, None
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


async def _requireSysAdmin(request: Request) -> tuple[SessionInfo | None, JSONResponse | None]:
    '''
    校验请求是否由系统管理员发起

    Args:
        request: FastAPI 请求对象

    Returns:
        tuple[SessionInfo | None, JSONResponse | None]: 校验通过时返回（会话信息, None），
        未登录返回（None, 2001 响应），非系统管理员返回（None, 2002 响应）
    '''
    token: str | None = request.cookies.get(TOKEN_KEY)
    sessionInfo: SessionInfo | None = await systemWork.authenticate(token)
    if sessionInfo is None:
        return None, _makeResponse(2001, '未登录', None)
    if not sessionInfo.sysAdmin:
        return None, _makeResponse(2002, '不具备操作权限', None)
    return sessionInfo, None



@systemServiceRouter.post('/sessions')
async def loginSysAdmin(request: Request) -> JSONResponse:
    '''
    系统管理员登录

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 登录结果响应，成功后通过 Cookie 下发会话令牌
    '''
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'id': str, 'password': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result = await systemWork.loginSysAdmin(id=body['id'], password=body['password'])
    return _makeResponse(result.code, result.msg, result.content, result.token)



@systemServiceRouter.get('/system/users/online')
async def getOnlineUsers(request: Request) -> JSONResponse:
    '''
    获取当前在线用户信息

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 在线用户列表响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.getOnlineUsers()
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.get('/system/groups')
async def getAllGroupsWithMembers(request: Request) -> JSONResponse:
    '''
    获取所有组的信息和对应的成员信息

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 组列表响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.getAllGroupsWithMembers()
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.get('/system/storage/info')
async def getStorageInfo(request: Request) -> JSONResponse:
    '''
    获取存储系统使用情况

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 整体与各组存储使用情况响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.getStorageInfo()
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.get('/system/groups/storage-quota')
async def getGroupsStorageQuota(request: Request) -> JSONResponse:
    '''
    获取所有组的存储空间配额信息

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 各组配额列表响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.getGroupsStorageQuota()
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.patch('/system/groups/{groupId}/storage-quota')
async def setGroupStorageQuota(request: Request, groupId: str) -> JSONResponse:
    '''
    对指定组进行存储空间配额

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 更新后的配额信息响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'groupId': str, 'size': int})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result = await systemWork.setGroupStorageQuota(groupId=groupId, size=body['size'])
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.get('/system/groups/{groupId}/members')
async def getGroupMembers(request: Request, groupId: str) -> JSONResponse:
    '''
    获取指定组中的成员信息

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 成员列表响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.getGroupMembers(groupId=groupId)
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.put('/system/groups/{groupId}/administrator')
async def appointAdministrator(request: Request, groupId: str, userId: str) -> JSONResponse:
    '''
    将指定成员任命为组管理员

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        userId: 目标成员账户标识

    Returns:
        JSONResponse: 任命结果响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.appointAdministrator(groupId=groupId, userId=userId)
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.delete('/system/groups/{groupId}/administrator')
async def dismissAdministrator(request: Request, groupId: str, userId: str) -> JSONResponse:
    '''
    将指定成员免除组管理员

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        userId: 目标成员账户标识

    Returns:
        JSONResponse: 免除结果响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.dismissAdministrator(groupId=groupId, userId=userId)
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.post('/system/groups')
async def createGroup(request: Request) -> JSONResponse:
    '''
    创建组

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 新建组信息响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'groupName': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result = await systemWork.createGroup(groupName=body['groupName'])
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.delete('/system/groups/{groupId}')
async def deleteGroup(request: Request, groupId: str) -> JSONResponse:
    '''
    删除组

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 删除结果响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.deleteGroup(groupId=groupId)
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.patch('/system/groups/{groupId}')
async def renameGroup(request: Request, groupId: str) -> JSONResponse:
    '''
    修改组名

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 修改结果响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'groupName': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result = await systemWork.renameGroup(groupId=groupId, groupName=body['groupName'])
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.get('/system/groups/{groupId}/join-requests')
async def getGroupJoinRequests(request: Request, groupId: str) -> JSONResponse:
    '''
    获取申请加入指定组的请求列表

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 申请者列表响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.getGroupJoinRequests(groupId=groupId)
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.patch('/system/groups/{groupId}/join-requests/{userId}')
async def reviewGroupJoinRequest(request: Request, groupId: str, userId: str) -> JSONResponse:
    '''
    审批加入组的请求

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        userId: 申请者的账户标识

    Returns:
        JSONResponse: 审批结果响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'status': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result = await systemWork.reviewGroupJoinRequest(
        groupId=groupId, userId=userId, status=body['status']
    )
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.get('/system/network/accessible')
async def getAccessibleDomain(request: Request) -> JSONResponse:
    '''
    获取当前可访问域白名单列表

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 可访问域列表响应
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.getAccessibleDomain()
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.post('/system/network/accessible')
async def addAccessibleDomain(request: Request) -> JSONResponse:
    '''
    向可访问域白名单添加网络域

    Args:
        request: FastAPI 请求对象

    Returns:
        JSONResponse: 添加结果响应，content 为最新列表
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'value': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result = await systemWork.addAccessibleDomain(value=body['value'])
    return _makeResponse(result.code, result.msg, result.content)



@systemServiceRouter.delete('/system/network/accessible')
async def deleteAccessibleDomain(request: Request, value: str) -> JSONResponse:
    '''
    从可访问域白名单移除网络域

    Args:
        request: FastAPI 请求对象
        value: 待移除的网络域表达式

    Returns:
        JSONResponse: 删除结果响应，content 为最新列表
    '''
    _, errorResponse = await _requireSysAdmin(request)
    if errorResponse is not None:
        return errorResponse
    result = await systemWork.deleteAccessibleDomain(value=value)
    return _makeResponse(result.code, result.msg, result.content)






