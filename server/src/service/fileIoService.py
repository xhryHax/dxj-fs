
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from interface.work.fileIoWork import FileIoWork
from interface.work.workCommon import SESSION_TTL, TOKEN_KEY, SessionInfo, WorkResult



fileIoWork           = FileIoWork()
fileIoServiceRouter  = APIRouter(prefix='/file-io-service', tags=['file-io-service'])


async def shutdownHook() -> None:
    '''
    释放本微服务持有的数据库与缓存连接

    由应用生命周期钩子在退出阶段统一调用，仅处理本服务资源

    Returns:
        None: 无返回值
    '''
    await fileIoWork.close()



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
    sessionInfo: SessionInfo | None = await fileIoWork.authenticate(token)
    if sessionInfo is None:
        return None, _makeResponse(2001, '未登录', None)
    return sessionInfo, None



@fileIoServiceRouter.get('/groups/{groupId}/files/upload-info')
async def getUploadInfoList(request: Request, groupId: str) -> JSONResponse:
    '''
    获取指定组下已有的全部上传进度信息

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 统一结构的 JSON 响应，成功时 content 为上传进度列表
    '''
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileIoWork.getUploadInfoList(
        accountId=sessionInfo.id,
        groupId=groupId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileIoServiceRouter.delete('/groups/{groupId}/files/upload-info/{uploadInfoId}')
async def deleteUploadInfo(request: Request, groupId: str, uploadInfoId: str) -> JSONResponse:
    '''
    删除指定的上传记录并清理对应缓存资源

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        uploadInfoId: 待删除的上传记录标识

    Returns:
        JSONResponse: 统一结构的 JSON 响应
    '''
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileIoWork.deleteUploadInfo(
        accountId=sessionInfo.id,
        groupId=groupId,
        uploadInfoId=uploadInfoId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileIoServiceRouter.post('/groups/{groupId}/files/upload-info')
async def prepareUpload(request: Request, groupId: str) -> JSONResponse:
    '''
    就绪文件上传环境并创建上传记录

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识

    Returns:
        JSONResponse: 统一结构的 JSON 响应，成功时 content 为上传环境信息
    '''
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    body, bodyError = await _parseBody(request)
    if bodyError is not None:
        return bodyError
    assert body is not None
    checkError: tuple[int, str] | None = _checkBody(
        body, {'size': int, 'fileName': str, 'label': str}
    )
    if checkError is not None:
        errorCode, errorMsg = checkError
        return _makeResponse(errorCode, errorMsg, None)
    result: WorkResult = await fileIoWork.prepareUpload(
        accountId=sessionInfo.id,
        groupId=groupId,
        size=int(body['size']),
        fileName=str(body['fileName']),
        label=str(body['label'])
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileIoServiceRouter.put('/groups/{groupId}/files/upload-info/{uploadInfoId}/data')
async def uploadData(request: Request, groupId: str, uploadInfoId: str) -> JSONResponse:
    '''
    上传文件分片数据并更新接收进度

    Args:
        request: FastAPI 请求对象，须携带 Content-Range 标头声明片段位置
        groupId: 目标组标识
        uploadInfoId: 上传记录标识

    Returns:
        JSONResponse: 统一结构的 JSON 响应，成功时 content 为 {size, progress}
    '''
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    contentRange: str | None = request.headers.get('Content-Range')
    if contentRange is None:
        return _makeResponse(3016, '分片范围不合法', None)
    data: bytes = await request.body()
    result: WorkResult = await fileIoWork.uploadData(
        accountId=sessionInfo.id,
        groupId=groupId,
        uploadInfoId=uploadInfoId,
        contentRange=contentRange,
        data=data
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileIoServiceRouter.post('/groups/{groupId}/files/upload-info/{uploadInfoId}/complete')
async def completeUpload(request: Request, groupId: str, uploadInfoId: str) -> JSONResponse:
    '''
    完成文件上传，同步元数据与文件到全局

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        uploadInfoId: 上传记录标识

    Returns:
        JSONResponse: 统一结构的 JSON 响应，成功时 content 为序列化的文件信息
    '''
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileIoWork.completeUpload(
        accountId=sessionInfo.id,
        groupId=groupId,
        uploadInfoId=uploadInfoId
    )
    return _makeResponse(result.code, result.msg, result.content)


@fileIoServiceRouter.get('/groups/{groupId}/files/{fileId}')
async def getDownloadLink(request: Request, groupId: str, fileId: str) -> JSONResponse:
    '''
    获取指定文件的下载链接

    Args:
        request: FastAPI 请求对象
        groupId: 目标组标识
        fileId: 文件标识

    Returns:
        JSONResponse: 统一结构的 JSON 响应，成功时 content 为 {fileURL, fileName}
    '''
    sessionInfo, errorResponse = await _requireLogin(request)
    if errorResponse is not None:
        return errorResponse
    assert sessionInfo is not None
    result: WorkResult = await fileIoWork.getDownloadLink(
        accountId=sessionInfo.id,
        groupId=groupId,
        fileId=fileId
    )
    return _makeResponse(result.code, result.msg, result.content)




