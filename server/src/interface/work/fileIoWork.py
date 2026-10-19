import asyncio
import datetime
import json
import os
import re
from typing import TypedDict, cast

import obstore
from obstore.store import S3Store

from interface.data.mysqlInteraction import (
    MySqlInteraction,
    accountModel,
    fileModel,
    groupAndSpecificModel,
    groupModel,
    publicPageAndFileModel,
    specificPageAndFileModel
)
from interface.data.redisInteraction import RedislInteraction
from interface.data.rustFslInteraction import RustFsInteraction
from interface.tools.globalTools import (
    ConfigObject,
    generateIdentificationFileCode,
    loadConfig
)
from interface.work.workCommon import SESSION_PREFIX, SessionInfo, WorkResult


NAME_MAX_LENGTH             : int   = 255
LABEL_MAX_LENGTH            : int   = 255
FILE_SIZE_MAX               : int   = 4 * 1024 * 1024 * 1024        # 单文件大小上限，4GiB
UPLOAD_INFO_TTL             : int   = 3600                          # 上传记录有效期，1 小时
DOWNLOAD_URL_TTL            : int   = 60                            # 下载链接有效期，1 分钟
UPLOAD_INFO_PREFIX          : str   = 'uploadInfo:'
UPLOAD_SEGMENT_PREFIX       : str   = 'uploadSegments:'
UPLOAD_GROUP_PREFIX         : str   = 'uploadGroup:'
CONTENT_RANGE_PATTERN       : re.Pattern[str] = re.compile(
    r'^bytes(?:=\s*|\s+)(\d+)-(\d+)/(\d+)$'
)
TEMP_DIR                    : str   = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'temp')
)
DOMAINNAME                  : str   = 'http://xyhraics.top/v1/io'   # 最后面不要带斜杠，否则 Nginx 拼接会不正确



class UploadRecord(TypedDict):
    '''
    上传记录在 Redis 中的元数据结构
    '''
    groupId: str
    size: int
    fileName: str
    label: str
    uploader: str
    progress: int



def _isValidFileName(fileName: str) -> bool:
    '''
    校验文件名是否非空且长度合法

    Args:
        fileName: 待校验的文件名字符串

    Returns:
        bool: 文件名合法返回 True，否则返回 False
    '''
    return bool(fileName) and len(fileName) <= NAME_MAX_LENGTH


def _isValidLabel(label: str) -> bool:
    '''
    校验文件标签长度是否合法

    Args:
        label: 待校验的文件标签字符串

    Returns:
        bool: 标签长度合法返回 True，否则返回 False
    '''
    return len(label) <= LABEL_MAX_LENGTH


def _parseContentRange(contentRange: str, size: int) -> tuple[int, int, int] | None:
    '''
    解析 Content-Range 标头并校验其合法性

    Args:
        contentRange: Content-Range 标头原始值，形如 bytes 0-1023/10240，
            兼容 bytes=0-1023/10240 的等号写法
        size: 文件总大小（字节）

    Returns:
        tuple[int, int, int] | None: 合法时返回（start, end, total），
        标头格式异常或范围与文件大小不符时返回 None
    '''
    match: re.Match[str] | None = CONTENT_RANGE_PATTERN.match(contentRange.strip())
    if match is None:
        return None
    start: int = int(match.group(1))
    end: int = int(match.group(2))
    total: int = int(match.group(3))
    if total != size or start > end or end >= size:
        return None
    return start, end, total


def _formatDateTime(atTime: datetime.datetime | None) -> str | None:
    '''
    将时间转换为统一的 UTC 字符串格式

    Args:
        atTime: 待格式化的时间对象，可为 None

    Returns:
        str | None: 形如 YYYY-MM-DDTHH:MM:SSZ 的字符串，时间为空时返回 None
    '''
    if atTime is None:
        return None
    if atTime.tzinfo is not None:
        atTime = atTime.astimezone(datetime.timezone.utc)
    return atTime.strftime('%Y-%m-%dT%H:%M:%SZ')


def _parseJsonObject(raw: str) -> object:
    '''
    将 JSON 字符串安全解析为对象

    Args:
        raw: 待解析的 JSON 字符串

    Returns:
        object: 解析成功返回解析结果对象，解析失败返回 None
    '''
    try:
        return cast(object, json.loads(raw))
    except json.JSONDecodeError:
        return None



class FileIoWork:
    '''
    文件 IO 业务类
    ~~~
    负责文件分片上传的缓存管理、完成上传时同步元数据与文件到全局，
    以及下载链接的生成，并对接 MySQL、Redis 与 RustFS 数据层
    '''

    def __init__(
        self,
        mysql: MySqlInteraction | None = None,
        redis: RedislInteraction | None = None,
        rustFs: RustFsInteraction | None = None
    ) -> None:
        '''
        初始化 FileIoWork 业务对象

        Args:
            mysql: 可选的 MySQL 交互对象，未提供时依据配置文件自动构建
            redis: 可选的 Redis 交互对象，未提供时依据配置文件自动构建
            rustFs: 可选的 RustFS 交互对象，未提供时依据配置文件自动构建
        '''
        self.configObject: ConfigObject = loadConfig()
        self.mysql: MySqlInteraction = mysql if mysql is not None else MySqlInteraction(
            mysqlUser= self.configObject.mysql.user,
            mysqlPassword= self.configObject.mysql.pw,
            mysqlHost=self.configObject.mysql.host,
            mysqlPort=self.configObject.mysql.port,
            database=self.configObject.mysql.database
        )
        self.redis: RedislInteraction = redis if redis is not None else RedislInteraction(
            host=self.configObject.redis.host,
            port=self.configObject.redis.port,
            db=self.configObject.redis.db,
            password=self.configObject.redis.pw
        )
        self.rustFs: RustFsInteraction = rustFs if rustFs is not None else RustFsInteraction(
            endpointUrl=self.configObject.rustFS.endpointUrl,
            accessKey=self.configObject.rustFS.accessKey,
            secretKey=self.configObject.rustFS.secretKey,
            region=self.configObject.rustFS.region
        )
        self._locks: dict[str, asyncio.Lock] = {}


    async def close(self) -> None:
        '''
        释放底层数据库与缓存连接

        Returns:
            None: 无返回值
        '''
        await self.mysql.close()
        await self.redis.close()


    async def authenticate(self, token: str | None) -> SessionInfo | None:
        '''
        根据令牌解析当前会话信息

        Args:
            token: 会话令牌，可为 None

        Returns:
            SessionInfo | None: 会话有效时返回会话信息对象，无效或缺失时返回 None
        '''
        if token is None:
            return None
        rawPayload: str | None = await self.redis.read(f'{SESSION_PREFIX}{token}')
        if rawPayload is None:
            return None
        payloadData: object = _parseJsonObject(rawPayload)
        if not isinstance(payloadData, dict):
            return None
        payload: dict[str, str | None] = cast(
            dict[str, str | None], cast(object, payloadData)
        )
        sessionId: str | None = payload.get('id')
        sessionEmail: str | None = payload.get('email')
        sessionGroupId: str | None = payload.get('groupId')
        sessionGroupName: str | None = payload.get('groupName')
        if sessionId is None or sessionEmail is None:
            return None
        return SessionInfo(
            id=sessionId,
            email=sessionEmail,
            groupId=sessionGroupId,
            groupName=sessionGroupName
        )


    async def _isGroupMember(self, accountId: str, groupId: str) -> bool:
        '''
        判断指定账户是否为指定组的成员

        Args:
            accountId: 账户唯一标识
            groupId: 目标组标识

        Returns:
            bool: 账户在该组内返回 True，否则返回 False
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        return account is not None and account.beInGroupId == groupId


    async def _canDownload(self, accountId: str, file: fileModel) -> bool:
        '''
        判断指定账户是否具备下载指定文件的权限

        以下条件任一成立即具备下载权限：
        1. 本组下载：账户所在组与文件所属组一致
        2. 指定页下载：账户所在组存在于包含该文件的指定页的可见组
        3. 公开页下载：该文件出现在其所属组的公开页上

        Args:
            accountId: 发起请求的账户标识
            file: 目标文件模型

        Returns:
            bool: 具备下载权限返回 True，否则返回 False
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        if account is None:
            return False
        # 1. 本组下载
        if account.beInGroupId == file.groupId:
            return True
        ownerGroup: groupModel | None = await self.mysql.getRecord(groupModel, groupId=file.groupId)
        if ownerGroup is None:
            return False
        # 3. 公开页下载
        publicRelation: publicPageAndFileModel | None = await self.mysql.getRecord(
            publicPageAndFileModel,
            publicPageId=ownerGroup.publicPageId,
            fileId=file.fileId
        )
        if publicRelation is not None:
            return True
        # 2. 指定页下载
        pageRelations: list[specificPageAndFileModel] = await self.mysql.listRecords(
            specificPageAndFileModel, fileId=file.fileId
        )
        for relation in pageRelations:
            visibleRelation: groupAndSpecificModel | None = await self.mysql.getRecord(
                groupAndSpecificModel,
                specificPageId=relation.specificPageId,
                provideToGroupId=account.beInGroupId
            )
            if visibleRelation is not None:
                return True
        return False


    def _getLock(self, uploadInfoId: str) -> asyncio.Lock:
        '''
        获取指定上传记录的进程内互斥锁

        Args:
            uploadInfoId: 上传记录标识

        Returns:
            asyncio.Lock: 对应的互斥锁对象
        '''
        if uploadInfoId not in self._locks:
            self._locks[uploadInfoId] = asyncio.Lock()
        return self._locks[uploadInfoId]


    def _dropLock(self, uploadInfoId: str) -> None:
        '''
        移除指定上传记录的进程内互斥锁

        Args:
            uploadInfoId: 上传记录标识

        Returns:
            None: 无返回值
        '''
        _ = self._locks.pop(uploadInfoId, None)


    def _ensureTempDir(self) -> None:
        '''
        确保缓存目录存在，不存在时自动创建

        Returns:
            None: 无返回值
        '''
        os.makedirs(TEMP_DIR, exist_ok=True)


    def _tempFilePath(self, uploadInfoId: str) -> str:
        '''
        计算指定上传记录的缓存文件绝对路径

        Args:
            uploadInfoId: 上传记录标识

        Returns:
            str: 缓存文件的绝对路径
        '''
        return os.path.join(TEMP_DIR, uploadInfoId)


    async def _upsertRedis(self, key: str, raw: str, ex: int | None = None) -> bool:
        '''
        覆盖写入 Redis 键值对，键不存在时创建，已存在时更新

        Args:
            key: 键名
            raw: 键值
            ex: 过期时间（秒），为 None 时不过期

        Returns:
            bool: 写入成功返回 True，否则返回 False
        '''
        updated: bool = await self.redis.update(key, raw, ex=ex)
        if updated:
            return True
        return await self.redis.create(key, raw, ex=ex)


    async def _readRecord(self, uploadInfoId: str) -> UploadRecord | None:
        '''
        读取指定上传记录的元数据

        Args:
            uploadInfoId: 上传记录标识

        Returns:
            UploadRecord | None: 记录存在且格式合法时返回记录字典，否则返回 None
        '''
        raw: str | None = await self.redis.read(f'{UPLOAD_INFO_PREFIX}{uploadInfoId}')
        if raw is None:
            return None
        recordData: object = _parseJsonObject(raw)
        if not isinstance(recordData, dict):
            return None
        return cast(UploadRecord, cast(object, recordData))


    async def _writeRecord(self, uploadInfoId: str, record: UploadRecord) -> bool:
        '''
        写入指定上传记录的元数据并刷新有效期

        Args:
            uploadInfoId: 上传记录标识
            record: 记录元数据字典

        Returns:
            bool: 写入成功返回 True，否则返回 False
        '''
        return await self._upsertRedis(
            f'{UPLOAD_INFO_PREFIX}{uploadInfoId}',
            json.dumps(record, ensure_ascii=False),
            ex=UPLOAD_INFO_TTL
        )


    async def _readSegments(self, uploadInfoId: str) -> list[list[int]]:
        '''
        读取指定上传记录已接收的片段列表

        Args:
            uploadInfoId: 上传记录标识

        Returns:
            list[list[int]]: 已接收片段列表，形如 [[start, end], ...]，
            无记录或格式异常时返回空列表
        '''
        raw: str | None = await self.redis.read(f'{UPLOAD_SEGMENT_PREFIX}{uploadInfoId}')
        if raw is None:
            return []
        segmentsData: object = _parseJsonObject(raw)
        if not isinstance(segmentsData, list):
            return []
        return cast(list[list[int]], cast(object, segmentsData))


    async def _writeSegments(self, uploadInfoId: str, segments: list[list[int]]) -> bool:
        '''
        写入指定上传记录已接收的片段列表

        Args:
            uploadInfoId: 上传记录标识
            segments: 已接收片段列表，形如 [[start, end], ...]

        Returns:
            bool: 写入成功返回 True，否则返回 False
        '''
        return await self._upsertRedis(
            f'{UPLOAD_SEGMENT_PREFIX}{uploadInfoId}',
            json.dumps(segments),
            ex=UPLOAD_INFO_TTL
        )


    async def _readGroupIndex(self, groupId: str) -> list[str]:
        '''
        读取指定组的全部上传记录标识列表

        Args:
            groupId: 组标识

        Returns:
            list[str]: 上传记录标识列表，无记录或格式异常时返回空列表
        '''
        raw: str | None = await self.redis.read(f'{UPLOAD_GROUP_PREFIX}{groupId}')
        if raw is None:
            return []
        uploadInfoIdsData: object = _parseJsonObject(raw)
        if not isinstance(uploadInfoIdsData, list):
            return []
        return cast(list[str], cast(object, uploadInfoIdsData))


    async def _writeGroupIndex(self, groupId: str, uploadInfoIds: list[str]) -> bool:
        '''
        写入指定组的全部上传记录标识列表

        Args:
            groupId: 组标识
            uploadInfoIds: 上传记录标识列表

        Returns:
            bool: 写入成功返回 True，否则返回 False
        '''
        return await self._upsertRedis(
            f'{UPLOAD_GROUP_PREFIX}{groupId}',
            json.dumps(uploadInfoIds),
            ex=UPLOAD_INFO_TTL
        )


    async def _removeUploadEntry(self, uploadInfoId: str, groupId: str | None = None) -> None:
        '''
        清理指定上传记录的全部缓存资源

        Args:
            uploadInfoId: 上传记录标识
            groupId: 所属组标识，提供时同步清理该组的记录索引

        Returns:
            None: 无返回值
        '''
        _ = await self.redis.delete(
            f'{UPLOAD_INFO_PREFIX}{uploadInfoId}',
            f'{UPLOAD_SEGMENT_PREFIX}{uploadInfoId}'
        )
        if groupId is not None:
            groupIndex: list[str] = await self._readGroupIndex(groupId)
            if uploadInfoId in groupIndex:
                groupIndex.remove(uploadInfoId)
                _ = await self._writeGroupIndex(groupId, groupIndex)
        filePath: str = self._tempFilePath(uploadInfoId)
        if os.path.exists(filePath):
            os.remove(filePath)


    def _writeSegment(self, uploadInfoId: str, start: int, data: bytes) -> None:
        '''
        将分片数据随机写入缓存文件

        Args:
            uploadInfoId: 上传记录标识
            start: 分片起始偏移（字节）
            data: 分片二进制数据

        Returns:
            None: 无返回值
        '''
        self._ensureTempDir()
        filePath: str = self._tempFilePath(uploadInfoId)
        try:
            with open(filePath, mode='r+b') as file:
                _ = file.seek(start)
                _ = file.write(data)
        except FileNotFoundError:
            with open(filePath, mode='wb'):
                pass
            with open(filePath, mode='r+b') as file:
                _ = file.seek(start)
                _ = file.write(data)


    async def _registerFileRecord(
        self, groupId: str, name: str, label: str, size: int, uploader: str
    ) -> fileModel:
        '''
        注册文件元数据记录，供完成上传后同步信息到全局

        Args:
            groupId: 文件所属组标识
            name: 文件名称
            label: 文件标签
            size: 文件大小（字节）
            uploader: 上传者的账户标识

        Returns:
            fileModel: 已持久化的文件模型实例
        '''
        fileId: str = generateIdentificationFileCode()
        file: fileModel = fileModel(
            fileId=fileId,
            name=name,
            label=label,
            atDeleted=None,
            groupId=groupId,
            atCreated=datetime.datetime.now(),
            size=size,
            uploader=uploader
        )
        _ = await self.mysql.createRecord(file)
        return file


    def _serializeFileInfo(self, file: fileModel, uploaderName: str) -> dict[str, str | int | None]:
        '''
        将文件模型序列化为对外输出结构

        Args:
            file: 文件模型实例
            uploaderName: 上传者的用户名称

        Returns:
            dict[str, str | int | None]: 包含文件核心信息的字典
        '''
        return {
            'fileId': file.fileId,
            'label': file.label,
            'fileName': file.name,
            'atCreated': _formatDateTime(file.atCreated),
            'size': file.size,
            'uploader': uploaderName
        }


    async def getUploadInfoList(self, accountId: str, groupId: str) -> WorkResult:
        '''
        获取指定组下已有的全部上传进度信息

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识

        Returns:
            WorkResult: 成功时 code 为 0，content 为
            [{uploadInfoId, size, progress}, ...] 列表
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        groupIndex: list[str] = await self._readGroupIndex(groupId)
        uploadInfoList: list[dict[str, int | str]] = []
        for uploadInfoId in groupIndex:
            record: UploadRecord | None = await self._readRecord(uploadInfoId)
            if record is None or record['groupId'] != groupId:
                continue
            segments: list[list[int]] = await self._readSegments(uploadInfoId)
            progress: int = sum(segEnd - segStart + 1 for segStart, segEnd in segments)
            uploadInfoList.append({
                'uploadInfoId': uploadInfoId,
                'size': record['size'],
                'progress': progress
            })
        return WorkResult(code=0, msg='获取成功', content=uploadInfoList)


    async def deleteUploadInfo(self, accountId: str, groupId: str, uploadInfoId: str) -> WorkResult:
        '''
        删除指定的上传记录并清理对应缓存资源

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            uploadInfoId: 待删除的上传记录标识

        Returns:
            WorkResult: 成功时 code 为 0，content 为 None；
            删除操作幂等，记录不存在时同样返回成功
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        record: UploadRecord | None = await self._readRecord(uploadInfoId)
        if record is not None and record['groupId'] != groupId:
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        lock: asyncio.Lock = self._getLock(uploadInfoId)
        async with lock:
            await self._removeUploadEntry(uploadInfoId, groupId)
        self._dropLock(uploadInfoId)
        return WorkResult(code=0, msg='删除成功', content=None)


    async def prepareUpload(
        self, accountId: str, groupId: str, size: int, fileName: str, label: str
    ) -> WorkResult:
        '''
        就绪文件上传环境并创建上传记录

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            size: 文件总大小（字节）
            fileName: 文件名称
            label: 文件标签

        Returns:
            WorkResult: 成功时 code 为 0，content 为
            {uploadInfoId, size, fileName, label, progress}
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        if size <= 0 or size > FILE_SIZE_MAX:
            return WorkResult(code=1002, msg='参数值范围不正确', content=None)
        if not _isValidFileName(fileName):
            return WorkResult(code=1002, msg='参数值范围不正确', content=None)
        if not _isValidLabel(label):
            return WorkResult(code=1002, msg='参数值范围不正确', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        quotaInfo: tuple[int, int] | None = await self.rustFs.getBucketQuota(group.storageFieldKey)
        if quotaInfo is not None:
            quota, used = quotaInfo
            if quota > 0 and size > quota - used:
                return WorkResult(code=3014, msg='服务端无法处理此文件', content=None)
        existingFiles: list[fileModel] = await self.mysql.listRecords(
            fileModel, groupId=groupId, name=fileName, atDeleted=None
        )
        if existingFiles:
            return WorkResult(code=3015, msg='文件已在组中', content=None)
        uploadInfoId: str = generateIdentificationFileCode()
        record: UploadRecord = {
            'groupId': groupId,
            'size': size,
            'fileName': fileName,
            'label': label,
            'uploader': accountId,
            'progress': 0
        }
        _ = await self._writeRecord(uploadInfoId, record)
        groupIndex: list[str] = await self._readGroupIndex(groupId)
        groupIndex.append(uploadInfoId)
        _ = await self._writeGroupIndex(groupId, groupIndex)
        return WorkResult(code=0, msg='就绪成功', content={
            'uploadInfoId': uploadInfoId,
            'size': size,
            'fileName': fileName,
            'label': label,
            'progress': 0
        })


    async def uploadData(
        self, accountId: str, groupId: str, uploadInfoId: str, contentRange: str, data: bytes
    ) -> WorkResult:
        '''
        上传文件分片数据并更新接收进度

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            uploadInfoId: 上传记录标识
            contentRange: Content-Range 标头原始值，形如 bytes 0-1023/10240
            data: 分片二进制数据

        Returns:
            WorkResult: 成功时 code 为 0，content 为 {size, progress}
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        lock: asyncio.Lock = self._getLock(uploadInfoId)
        async with lock:
            record: UploadRecord | None = await self._readRecord(uploadInfoId)
            if record is None or record['groupId'] != groupId:
                return WorkResult(code=3010, msg='不存在此文件', content=None)
            size: int = record['size']
            parsed: tuple[int, int, int] | None = _parseContentRange(contentRange, size)
            if parsed is None:
                return WorkResult(code=3016, msg='分片范围不合法', content=None)
            start, end, _ = parsed
            if len(data) != end - start + 1:
                return WorkResult(code=3016, msg='分片范围不合法', content=None)
            segments: list[list[int]] = await self._readSegments(uploadInfoId)
            progress: int = sum(segEnd - segStart + 1 for segStart, segEnd in segments)
            if progress >= size:
                return WorkResult(code=3017, msg='已完成上传，无需再传', content=None)
            if [start, end] in segments:
                return WorkResult(code=3017, msg='已完成上传，无需再传', content=None)
            self._writeSegment(uploadInfoId, start, data)
            segments.append([start, end])
            _ = await self._writeSegments(uploadInfoId, segments)
            progress += end - start + 1
            record['progress'] = progress
            _ = await self._writeRecord(uploadInfoId, record)
            return WorkResult(code=0, msg='数据上传成功', content={
                'size': size,
                'progress': progress
            })


    async def completeUpload(
        self, accountId: str, groupId: str, uploadInfoId: str
    ) -> WorkResult:
        '''
        完成文件上传，同步元数据与文件到全局

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            uploadInfoId: 上传记录标识

        Returns:
            WorkResult: 成功时 code 为 0，content 为序列化的文件信息
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        lock: asyncio.Lock = self._getLock(uploadInfoId)
        async with lock:
            record: UploadRecord | None = await self._readRecord(uploadInfoId)
            if record is None or record['groupId'] != groupId:
                return WorkResult(code=3010, msg='上传记录不存在', content=None)
            size: int = record['size']
            segments: list[list[int]] = await self._readSegments(uploadInfoId)
            progress: int = sum(segEnd - segStart + 1 for segStart, segEnd in segments)
            if progress != size:
                return WorkResult(code=3017, msg='上传未完成', content=None)
            fileName: str = record['fileName']
            label: str = record['label']
            uploader: str = record['uploader']
            file: fileModel = await self._registerFileRecord(
                groupId=groupId,
                name=fileName,
                label=label,
                size=size,
                uploader=uploader
            )
            group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
            if group is None:
                _ = await self.mysql.deleteRecord(fileModel, fileId=file.fileId)
                return WorkResult(code=3018, msg='服务端的文件分片异常', content=None)
            store: S3Store = self.rustFs.generateStore(group.storageFieldKey)
            uploaded: bool = await self.rustFs.put(
                store, file.fileId, self._tempFilePath(uploadInfoId)
            )
            if not uploaded:
                _ = await self.mysql.deleteRecord(fileModel, fileId=file.fileId)
                return WorkResult(code=3018, msg='服务端的文件分片异常', content=None)
            await self._removeUploadEntry(uploadInfoId, groupId)
            self._dropLock(uploadInfoId)
            uploaderAccount: accountModel | None = await self.mysql.getRecord(
                accountModel, accountId=uploader
            )
            uploaderName: str = uploaderAccount.name if uploaderAccount is not None else ''
            return WorkResult(code=0, msg='文件上传完成', content=self._serializeFileInfo(file, uploaderName))


    async def getDownloadLink(self, accountId: str, groupId: str, fileId: str) -> WorkResult:
        '''
        获取指定文件的下载链接

        Args:
            accountId: 发起请求的账户标识
            groupId: 请求者当前所在组标识，仅用于上下文记录，权限判定见 _canDownload
            fileId: 文件标识

        Returns:
            WorkResult: 成功时 code 为 0，content 为 {fileURL, fileName}；
                        文件不存在返回 3010；不具备下载权限返回 2002
        '''
        _ = groupId  # 保留路由签名参数，权限判定基于文件归属与用户所在组
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.atDeleted is not None:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        if not await self._canDownload(accountId, file):
            return WorkResult(code=2002, msg='无权限进行操作', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=file.groupId)
        if group is None:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        store: S3Store = self.rustFs.generateStore(group.storageFieldKey, self.configObject.rustFS.signatureUrl)
        try:
            fileURL: str = await obstore.sign_async(
                store,
                'GET',
                fileId,
                datetime.timedelta(seconds=DOWNLOAD_URL_TTL)
            )
            fileURL = fileURL.replace(self.configObject.rustFS.signatureUrl, DOMAINNAME)
        except Exception:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        return WorkResult(code=0, msg='获取成功', content={
            'fileURL': fileURL,
            'fileName': file.name
        })





