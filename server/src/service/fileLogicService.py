
from typing import Any
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from interface.work.fileLogicWork import FileLogicWork
from interface.work.workCommon import TOKEN_KEY, SESSION_TTL, SessionInfo, WorkResult



fileLogicWork           = FileLogicWork()
fileLogicServiceRouter  = APIRouter(prefix='/file-logic-service', tags=['file-logic-service'])


async def shutdownHook() -> None:
    '''
    释放本微服务持有的数据库与缓存连接

    由应用生命周期钩子在退出阶段统一调用，仅处理本服务资源

    Returns:
        None: 无返回值
    '''
    await fileLogicWork.close()



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
    sessionInfo: SessionInfo | None = await fileLogicWork.authenticate(token)
    if sessionInfo is None:
        return None, _makeResponse(2001, '未登录', None)
    return sessionInfo, None


def _parsePagination(
    pageValue: str | None, sizeValue: str | None
) -> tuple[int, int] | JSONResponse:
    '''
    解析分页查询参数并校验其类型

    Args:
        pageValue: 窗口位置查询参数原始值
        sizeValue: 窗口大小查询参数原始值

    Returns:
        tuple[int, int] | JSONResponse: 参数类型正确时返回（page, size），
        缺失时返回 1001，类型不正确时返回 1003
    '''
    if pageValue is None or sizeValue is None:
        return _makeResponse(1001, '缺少分页参数', None)
    try:
        page: int = int(pageValue)
        size: int = int(sizeValue)
    except ValueError:
        return _makeResponse(1003, '参数类型不正确', None)
    return page, size


def _parsePaginationOrResponse(request: Request) -> tuple[int, int] | JSONResponse:
    '''
    从请求中提取分页参数并完成类型解析

    Args:
        request: FastAPI 请求对象

    Returns:
        tuple[int, int] | JSONResponse: 解析成功返回（page, size），否则返回错误响应
    '''
    return _parsePagination(
        request.query_params.get('page'),
        request.query_params.get('size')
    )



@fileLogicServiceRouter.get('/groups/{groupId}/files')
async def getGroupFiles(request: Request, groupId: str) -> JSONResponse:
    '''
    获取指定组下对应窗口的文件信息

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
    pageSize: tuple[int, int] | JSONResponse = _parsePaginationOrResponse(request)
    if isinstance(pageSize, JSONResponse):
        return pageSize
    page, size = pageSize
    result: WorkResult = await fileLogicWork.getGroupFiles(
        accountId=sessionInfo.id,
        groupId=groupId,
        page=page,
        size=size
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.get('/groups/{groupId}/public-pages/files')
async def getPublicPageFiles(request: Request, groupId: str) -> JSONResponse:
    '''
    获取指定组公开页下对应窗口的文件信息

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
    pageSize: tuple[int, int] | JSONResponse = _parsePaginationOrResponse(request)
    if isinstance(pageSize, JSONResponse):
        return pageSize
    page, size = pageSize
    result: WorkResult = await fileLogicWork.getPublicPageFiles(
        accountId=sessionInfo.id,
        groupId=groupId,
        page=page,
        size=size
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.get('/groups/{groupId}/specific-pages/{specificPagesId}/files')
async def getSpecificPageFiles(request: Request, groupId: str, specificPagesId: str) -> JSONResponse:
    '''
    获取指定页下对应窗口的文件信息

    Args:
        request: FastAPI 请求对象
        groupId: 请求者所在组标识
        specificPagesId: 目标指定页标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    pageSize: tuple[int, int] | JSONResponse = _parsePaginationOrResponse(request)
    if isinstance(pageSize, JSONResponse):
        return pageSize
    page, size = pageSize
    result: WorkResult = await fileLogicWork.getSpecificPageFiles(
        accountId=sessionInfo.id,
        groupId=groupId,
        specificPageId=specificPagesId,
        page=page,
        size=size
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.get('/groups/{groupId}/deleted/files')
async def getDeletedFiles(request: Request, groupId: str) -> JSONResponse:
    '''
    获取指定组下已软删除的对应窗口的文件信息

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
    pageSize: tuple[int, int] | JSONResponse = _parsePaginationOrResponse(request)
    if isinstance(pageSize, JSONResponse):
        return pageSize
    page, size = pageSize
    result: WorkResult = await fileLogicWork.getDeletedFiles(
        accountId=sessionInfo.id,
        groupId=groupId,
        page=page,
        size=size
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.get('/groups/{groupId}/storage-quota')
async def getGroupStorageQuota(request: Request, groupId: str) -> JSONResponse:
    '''
    获取指定组的存储配额与已用空间信息

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
    result: WorkResult = await fileLogicWork.getGroupStorageQuota(
        accountId=sessionInfo.id,
        groupId=groupId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.patch('/groups/{groupId}/files/{fileId}/name')
async def renameFile(request: Request, groupId: str, fileId: str) -> JSONResponse:
    '''
    修改指定文件的文件名称

    Args:
        request: FastAPI 请求对象
        groupId: 文件所在组标识
        fileId: 目标文件标识

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
    checkResult: tuple[int, str] | None = _checkBody(body, {'fileName': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await fileLogicWork.renameFile(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=fileId,
        fileName=body['fileName']
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.patch('/groups/{groupId}/files/{fileId}/label')
async def changeFileLabel(request: Request, groupId: str, fileId: str) -> JSONResponse:
    '''
    修改指定文件的文件标签

    Args:
        request: FastAPI 请求对象
        groupId: 文件所在组标识
        fileId: 目标文件标识

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
    checkResult: tuple[int, str] | None = _checkBody(body, {'label': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await fileLogicWork.changeFileLabel(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=fileId,
        label=body['label']
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.delete('/groups/{groupId}/files/{fileId}')
async def softDeleteFile(request: Request, groupId: str, fileId: str) -> JSONResponse:
    '''
    软删除指定文件，将其移入组回收站

    Args:
        request: FastAPI 请求对象
        groupId: 文件所在组标识
        fileId: 目标文件标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileLogicWork.softDeleteFile(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=fileId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.post('/groups/{groupId}/files/{fileId}/restore')
async def restoreFile(request: Request, groupId: str, fileId: str) -> JSONResponse:
    '''
    恢复已软删除的文件，使其重新在组内可见

    Args:
        request: FastAPI 请求对象
        groupId: 文件所在组标识
        fileId: 目标文件标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileLogicWork.restoreFile(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=fileId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.delete('/groups/{groupId}/deleted/files/{fileId}')
async def hardDeleteFile(request: Request, groupId: str, fileId: str) -> JSONResponse:
    '''
    物理删除回收站中的文件，并清理其页面关联与实际存储

    Args:
        request: FastAPI 请求对象
        groupId: 文件所在组标识
        fileId: 目标文件标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileLogicWork.hardDeleteFile(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=fileId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.get('/arbitrary-groups/public-pages')
async def getAllPublicPages(request: Request) -> JSONResponse:
    '''
    获取系统中全部组的公开页信息

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
    result: WorkResult = await fileLogicWork.getAllPublicPages()
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.get('/accounts/me/visible-pages')
async def getVisiblePages(request: Request) -> JSONResponse:
    '''
    获取当前账户所在组可见的全部指定页信息

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
    result: WorkResult = await fileLogicWork.getVisiblePages(
        accountId=sessionInfo.id
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.get('/groups/{groupId}/specific-pages')
async def getGroupSpecificPages(request: Request, groupId: str) -> JSONResponse:
    '''
    获取当前所在组拥有的全部指定页信息

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
    result: WorkResult = await fileLogicWork.getGroupSpecificPages(
        accountId=sessionInfo.id,
        groupId=groupId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.post('/groups/{groupId}/specific-pages')
async def createSpecificPage(request: Request, groupId: str) -> JSONResponse:
    '''
    为当前所在组创建指定页并配置可见组

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
    body: dict[str, Any] | None
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(
        body, {'announcement': str, 'visibleGroups': list}
    )
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await fileLogicWork.createSpecificPage(
        accountId=sessionInfo.id,
        groupId=groupId,
        announcement=body['announcement'],
        visibleGroups=body['visibleGroups']
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.patch('/groups/{groupId}/public-pages/{publicPageId}')
async def updatePublicPageAnnouncement(request: Request, groupId: str, publicPageId: str) -> JSONResponse:
    '''
    修改指定组公开页的公告内容

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        publicPageId: 目标公开页标识

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
    checkResult: tuple[int, str] | None = _checkBody(body, {'announcement': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await fileLogicWork.updatePublicPageAnnouncement(
        accountId=sessionInfo.id,
        groupId=groupId,
        publicPageId=publicPageId,
        announcement=body['announcement']
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.patch('/groups/{groupId}/specific-pages/{specificPageId}')
async def updateSpecificPage(request: Request, groupId: str, specificPageId: str) -> JSONResponse:
    '''
    修改指定页的公告内容或可见组配置，按请求体字段进行分发

    Args:
        request: FastAPI 请求对象
        groupId: 指定页所属组标识
        specificPageId: 目标指定页标识

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
    hasAnnouncement: bool = 'announcement' in body
    hasVisibleGroups: bool = 'visibleGroups' in body
    if hasAnnouncement == hasVisibleGroups:
        return _makeResponse(1001, '参数映射不符', None)
    result: WorkResult
    if hasAnnouncement:
        if not isinstance(body['announcement'], str):
            return _makeResponse(1003, '参数类型不正确：announcement', None)
        result = await fileLogicWork.updateSpecificPageAnnouncement(
            accountId=sessionInfo.id,
            groupId=groupId,
            specificPageId=specificPageId,
            announcement=body['announcement']
        )
    else:
        if not isinstance(body['visibleGroups'], list):
            return _makeResponse(1003, '参数类型不正确：visibleGroups', None)
        result = await fileLogicWork.updateSpecificPageVisibleGroups(
            accountId=sessionInfo.id,
            groupId=groupId,
            specificPageId=specificPageId,
            visibleGroups=body['visibleGroups'] # type: ignore
        )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.post('/groups/{groupId}/public-pages/files')
async def addFileToPublicPage(request: Request, groupId: str) -> JSONResponse:
    '''
    将指定文件添加到当前所在组的公开页

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
    body: dict[str, Any] | None
    body, errorResponse = await _parseBody(request)
    if errorResponse is not None:
        return errorResponse
    assert body is not None
    checkResult: tuple[int, str] | None = _checkBody(body, {'fileId': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await fileLogicWork.addFileToPublicPage(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=body['fileId']
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.delete('/groups/{groupId}/public-pages/files/{fileId}')
async def removeFileFromPublicPage(request: Request, groupId: str, fileId: str) -> JSONResponse:
    '''
    将指定文件从当前所在组的公开页移除

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        fileId: 目标文件标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileLogicWork.removeFileFromPublicPage(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=fileId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.post('/groups/{groupId}/specific-pages/{specificPagesId}/files')
async def addFileToSpecificPage(request: Request, groupId: str, specificPagesId: str) -> JSONResponse:
    '''
    将指定文件添加到当前所在组拥有的指定页

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        specificPagesId: 目标指定页标识

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
    checkResult: tuple[int, str] | None = _checkBody(body, {'fileId': str})
    if checkResult is not None:
        return _makeResponse(checkResult[0], checkResult[1], None)
    result: WorkResult = await fileLogicWork.addFileToSpecificPage(
        accountId=sessionInfo.id,
        groupId=groupId,
        specificPageId=specificPagesId,
        fileId=body['fileId']
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.delete('/groups/{groupId}/specific-pages/{specificPagesId}/files/{fileId}')
async def removeFileFromSpecificPage(request: Request, groupId: str, specificPagesId: str, fileId: str) -> JSONResponse:
    '''
    将指定文件从当前所在组拥有的指定页移除

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        specificPagesId: 目标指定页标识
        fileId: 目标文件标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileLogicWork.removeFileFromSpecificPage(
        accountId=sessionInfo.id,
        groupId=groupId,
        specificPageId=specificPagesId,
        fileId=fileId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileLogicServiceRouter.delete('/groups/{groupId}/specific-pages/{specificPageId}')
async def deleteSpecificPage(request: Request, groupId: str, specificPageId: str) -> JSONResponse:
    '''
    删除指定页及其全部关联配置

    Args:
        request: FastAPI 请求对象
        groupId: 指定页所属组标识
        specificPageId: 目标指定页标识

    Returns:
        JSONResponse: 统一 JSON 响应
    '''
    sessionInfo: SessionInfo | None
    errorResponse: JSONResponse | None
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileLogicWork.deleteSpecificPage(
        accountId=sessionInfo.id,
        groupId=groupId,
        specificPageId=specificPageId
    )
    return _makeResponse(result.code, result.msg, result.content)
