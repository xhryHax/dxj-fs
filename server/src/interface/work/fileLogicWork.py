
import json
from datetime import datetime, timezone
from typing import Any

from interface.data.mysqlInteraction import (
    MySqlInteraction,
    accountModel,
    fileModel,
    groupAndSpecificModel,
    groupModel,
    publicPageAndFileModel,
    specificPageAndFileModel,
    specificPageModel
)
from interface.data.redisInteraction import RedislInteraction
from interface.data.rustFslInteraction import RustFsInteraction
from interface.tools.globalTools import ConfigObject, generateIdentificationFileCode, loadConfig
from interface.work.workCommon import (
    SESSION_PREFIX,
    SessionInfo,
    WorkResult
)



NAME_MAX_LENGTH             : int   = 255
LABEL_MAX_LENGTH            : int   = 255
ANNOUNCEMENT_MAX_LENGTH     : int   = 255
PAGE_SIZE_MAX               : int   = 10000



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


def _isValidAnnouncement(announcement: str) -> bool:
    '''
    校验公告内容长度是否合法

    Args:
        announcement: 待校验的公告内容字符串

    Returns:
        bool: 公告长度合法返回 True，否则返回 False
    '''
    return len(announcement) <= ANNOUNCEMENT_MAX_LENGTH


def _isValidVisibleGroups(visibleGroups: list[str]|Any) -> bool:
    '''
    校验指定页可见组列表是否合法

    Args:
        visibleGroups: 待校验的可见组标识列表

    Returns:
        bool: 可见组列表为合法的字符串列表时返回 True，否则返回 False
    '''
    return (
        isinstance(visibleGroups, list)
        and all(isinstance(groupId, str) and bool(groupId) for groupId in visibleGroups) # type: ignore
    )


def _isValidPage(page: int, size: int) -> bool:
    '''
    校验分页窗口参数是否合法

    Args:
        page: 窗口起始位置，须为非负整数
        size: 窗口大小，须在 1 到 PAGE_SIZE_MAX 之间

    Returns:
        bool: 分页参数合法返回 True，否则返回 False
    '''
    return page >= 0 and 1 <= size <= PAGE_SIZE_MAX


def _formatDateTime(atTime: datetime | None) -> str | None:
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
        atTime = atTime.astimezone(timezone.utc)
    return atTime.strftime('%Y-%m-%dT%H:%M:%SZ')



class FileLogicWork:
    '''
    文件逻辑业务类
    ~~~
    负责文件元数据管理、公开页与指定页管理、文件与页面关联管理等业务处理，
    并对接 MySQL、Redis 与 RustFS 数据层
    '''

    def __init__(
        self,
        mysql: MySqlInteraction | None = None,
        redis: RedislInteraction | None = None,
        rustFs: RustFsInteraction | None = None
    ) -> None:
        '''
        初始化 FileLogicWork 业务对象

        Args:
            mysql: 可选的 MySQL 交互对象，未提供时依据配置文件自动构建
            redis: 可选的 Redis 交互对象，未提供时依据配置文件自动构建
            rustFs: 可选的 RustFS 交互对象，未提供时依据配置文件自动构建
        '''
        configObject: ConfigObject = loadConfig()
        self.mysql: MySqlInteraction = mysql if mysql is not None else MySqlInteraction(
            mysqlUser=configObject.mysql.user,
            mysqlPassword=configObject.mysql.pw,
            mysqlHost=configObject.mysql.host,
            mysqlPort=configObject.mysql.port,
            database=configObject.mysql.database
        )
        self.redis: RedislInteraction = redis if redis is not None else RedislInteraction(
            host=configObject.redis.host,
            port=configObject.redis.port,
            db=configObject.redis.db,
            password=configObject.redis.pw
        )
        self.rustFs: RustFsInteraction = rustFs if rustFs is not None else RustFsInteraction(
            endpointUrl=configObject.rustFS.endpointUrl,
            accessKey=configObject.rustFS.accessKey,
            secretKey=configObject.rustFS.secretKey,
            region=configObject.rustFS.region
        )


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
        try:
            payload: dict[str, str | None] = json.loads(rawPayload)
            sessionId: str | None = payload.get('id')
            sessionEmail: str | None = payload.get('email')
            groupId: str | None = payload.get('groupId')
            groupName: str | None = payload.get('groupName')
            if sessionId is None or sessionEmail is None:
                return None
            return SessionInfo(
                id=sessionId,
                email=sessionEmail,
                groupId=groupId,
                groupName=groupName
            )
        except (json.JSONDecodeError, TypeError):
            return None


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


    async def _isGroupAdmin(self, accountId: str, groupId: str) -> bool:
        '''
        判断指定账户是否为指定组的管理员

        Args:
            accountId: 账户唯一标识
            groupId: 目标组标识

        Returns:
            bool: 账户为该组管理员返回 True，否则返回 False
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        return account is not None and account.beInGroupId == groupId and account.admin == 1


    def _serializeFileInfo(self, file: fileModel, uploaderName: str) -> dict[str, Any]:
        '''
        将文件模型序列化为对外输出结构

        Args:
            file: 文件模型实例
            uploaderName: 上传者的用户名称

        Returns:
            dict[str, Any]: 包含文件核心信息的字典，软删除文件额外携带 atDeleted 字段
        '''
        fileInfo: dict[str, Any] = {
            'fileId': file.fileId,
            'label': file.label,
            'fileName': file.name,
            'atCreated': _formatDateTime(file.atCreated),
            'size': file.size,
            'uploader': uploaderName
        }
        if file.atDeleted is not None:
            fileInfo['atDeleted'] = _formatDateTime(file.atDeleted)
        return fileInfo


    async def _serializeFilesInfo(self, files: list[fileModel]) -> list[dict[str, Any]]:
        '''
        批量将文件模型序列化为对外输出结构，并补充上传者名称

        Args:
            files: 文件模型实例列表

        Returns:
            list[dict[str, Any]]: 文件信息字典列表
        '''
        uploaderIds: set[str] = {
            file.uploader for file in files if file.uploader is not None
        }
        uploaderNameMap: dict[str, str] = {}
        for uploaderId in uploaderIds:
            uploader: accountModel | None = await self.mysql.getRecord(
                accountModel, accountId=uploaderId
            )
            if uploader is not None:
                uploaderNameMap[uploaderId] = uploader.name
        return [
            self._serializeFileInfo(file, uploaderNameMap.get(file.uploader, '')) # type: ignore
            for file in files
        ]


    def _paginate(self, records: list[Any], page: int, size: int) -> tuple[dict[str, Any] | None, str | None]:
        '''
        对记录列表执行分页切片并计算窗口信息

        Args:
            records: 待分页的记录列表
            page: 窗口起始位置
            size: 窗口大小

        Returns:
            tuple[dict[str, Any] | None, str | None]: 分页成功时返回
            （窗口信息字典, None），否则返回（None, 超出范围说明）
        '''
        total: int = len(records)
        if total == 0:
            if page == 0:
                return {'total': 0, 'page': page, 'info': []}, None
            return None, '请求的范围超出实际的范围'
        if page * size >= total:
            return None, '请求的范围超出实际的范围'
        window: list[Any] = records[page * size:(page + 1) * size]
        return {'total': total, 'page': page, 'info': window}, None


    async def getGroupFiles(self, accountId: str, groupId: str, page: int, size: int) -> WorkResult:
        '''
        获取指定组内未被删除的文件信息窗口

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            page: 窗口起始位置
            size: 窗口大小

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为分页窗口信息；
                        参数不合法返回 1002；非组内成员返回 2002；窗口越界返回 3008
        '''
        if not _isValidPage(page, size):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
        files: list[fileModel] = await self.mysql.listRecords(
            fileModel, groupId=groupId, atDeleted=None
        )
        files.sort(key=lambda file: file.atCreated)
        content: dict[str, Any] | None
        errorMsg: str | None
        content, errorMsg = self._paginate(files, page, size)
        if errorMsg is not None:
            return WorkResult(code=3008, msg=errorMsg, content=None)
        assert content is not None
        content['info'] = await self._serializeFilesInfo(content['info'])
        return WorkResult(code=0, msg='获取成功', content=content)


    async def getPublicPageFiles(self, accountId: str, groupId: str, page: int, size: int) -> WorkResult:
        '''
        获取指定组公开页下未被删除的文件信息窗口

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            page: 窗口起始位置
            size: 窗口大小

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为分页窗口信息；
                        参数不合法返回 1002；非组内成员返回 2002；窗口越界返回 3008
        '''
        if not _isValidPage(page, size):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        # 公开页不需要校验是否本组，对所有人员开放
        # if not await self._isGroupMember(accountId, groupId):
        #     return WorkResult(code=2002, msg='不具备获取权限', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
        relations: list[publicPageAndFileModel] = await self.mysql.listRecords(
            publicPageAndFileModel, publicPageId=group.publicPageId
        )
        files: list[fileModel] = []
        for relation in relations:
            file: fileModel | None = await self.mysql.getRecord(
                fileModel, fileId=relation.fileId
            )
            if file is not None and file.atDeleted is None:
                files.append(file)
        files.sort(key=lambda file: file.atCreated)
        content: dict[str, Any] | None
        errorMsg: str | None
        content, errorMsg = self._paginate(files, page, size)
        if errorMsg is not None:
            return WorkResult(code=3008, msg=errorMsg, content=None)
        assert content is not None
        content['info'] = await self._serializeFilesInfo(content['info'])
        return WorkResult(code=0, msg='获取成功', content=content)


    async def getSpecificPageFiles(
        self, accountId: str, groupId: str, specificPageId: str, page: int, size: int
    ) -> WorkResult:
        '''
        获取指定页下未被删除的文件信息窗口

        Args:
            accountId: 发起请求的账户标识
            groupId: 请求者所在组标识
            specificPageId: 目标指定页标识
            page: 窗口起始位置
            size: 窗口大小

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为分页窗口信息；
                        参数不合法返回 1002；指定页不存在返回 3009；
                        非组内成员或页面不可见返回 2002；窗口越界返回 3008
        '''
        if not _isValidPage(page, size):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        pageRecord: specificPageModel | None = await self.mysql.getRecord(
            specificPageModel, specificPageId=specificPageId
        )
        if pageRecord is None:
            return WorkResult(code=3009, msg='对应的指定页不存在', content=None)
        # if not await self._isGroupMember(accountId, groupId):
        #     return WorkResult(code=2002, msg='不具备获取权限', content=None)
        isOwner: bool = pageRecord.ownerGroupId == groupId
        visibleRelation: groupAndSpecificModel | None = await self.mysql.getRecord(
            groupAndSpecificModel,
            specificPageId=specificPageId,
            provideToGroupId=groupId
        )
        if not isOwner and visibleRelation is None:
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
        relations: list[specificPageAndFileModel] = await self.mysql.listRecords(
            specificPageAndFileModel, specificPageId=specificPageId
        )
        files: list[fileModel] = []
        for relation in relations:
            file: fileModel | None = await self.mysql.getRecord(
                fileModel, fileId=relation.fileId
            )
            if file is not None and file.atDeleted is None:
                files.append(file)
        files.sort(key=lambda file: file.atCreated)
        content: dict[str, Any] | None
        errorMsg: str | None
        content, errorMsg = self._paginate(files, page, size)
        if errorMsg is not None:
            return WorkResult(code=3008, msg=errorMsg, content=None)
        assert content is not None
        content['info'] = await self._serializeFilesInfo(content['info'])
        return WorkResult(code=0, msg='获取成功', content=content)


    async def getDeletedFiles(self, accountId: str, groupId: str, page: int, size: int) -> WorkResult:
        '''
        获取指定组内已软删除的文件信息窗口

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            page: 窗口起始位置
            size: 窗口大小

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为分页窗口信息；
                        参数不合法返回 1002；非组内成员返回 2002；窗口越界返回 3008
        '''
        if not _isValidPage(page, size):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
        allFiles: list[fileModel] = await self.mysql.listRecords(fileModel, groupId=groupId)
        deletedFiles: list[fileModel] = [
            file for file in allFiles if file.atDeleted is not None
        ]
        deletedFiles.sort(key=lambda file: file.atDeleted) # type: ignore
        content: dict[str, Any] | None
        errorMsg: str | None
        content, errorMsg = self._paginate(deletedFiles, page, size)
        if errorMsg is not None:
            return WorkResult(code=3008, msg=errorMsg, content=None)
        assert content is not None
        content['info'] = await self._serializeFilesInfo(content['info'])
        return WorkResult(code=0, msg='获取成功', content=content)


    async def renameFile(self, accountId: str, groupId: str, fileId: str, fileName: str) -> WorkResult:
        '''
        修改指定文件的文件名称

        Args:
            accountId: 发起请求的账户标识
            groupId: 文件所在组标识
            fileId: 目标文件标识
            fileName: 新的文件名称

        Returns:
            WorkResult: 修改成功时 code 为 0，content 为更新后的文件信息；
                        文件名不合法返回 3011；非组内成员返回 2002；
                        文件不存在或不属于该组返回 3010
        '''
        if not _isValidFileName(fileName):
            return WorkResult(code=3011, msg='文件名不合法', content=None)
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.groupId != groupId:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        updatedFile: fileModel | None = await self.mysql.updateRecord(
            fileModel, {'name': fileName}, fileId=fileId
        )
        if updatedFile is None:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        return WorkResult(
            code=0,
            msg='文件更名成功',
            content=self._serializeFileInfo(updatedFile, '')
        )


    async def changeFileLabel(self, accountId: str, groupId: str, fileId: str, label: str) -> WorkResult:
        '''
        修改指定文件的文件标签

        Args:
            accountId: 发起请求的账户标识
            groupId: 文件所在组标识
            fileId: 目标文件标识
            label: 新的文件标签

        Returns:
            WorkResult: 修改成功时 code 为 0，content 为更新后的文件信息；
                        标签不合法返回 3012；非组内成员返回 2002；
                        文件不存在或不属于该组返回 3010
        '''
        if not _isValidLabel(label):
            return WorkResult(code=3012, msg='文件标签不合法', content=None)
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.groupId != groupId:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        updatedFile: fileModel | None = await self.mysql.updateRecord(
            fileModel, {'label': label}, fileId=fileId
        )
        if updatedFile is None:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        return WorkResult(
            code=0,
            msg='文件标签修改成功',
            content=self._serializeFileInfo(updatedFile, '')
        )


    async def softDeleteFile(self, accountId: str, groupId: str, fileId: str) -> WorkResult:
        '''
        软删除指定文件，将其移入组回收站

        Args:
            accountId: 发起请求的账户标识
            groupId: 文件所在组标识
            fileId: 目标文件标识

        Returns:
            WorkResult: 删除成功时 code 为 0，content 为 None；
                        非组内成员返回 2002；文件不存在或不属于该组返回 3010
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.groupId != groupId:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        _ = await self.mysql.updateRecord(
            fileModel, {'atDeleted': datetime.now()}, fileId=fileId
        )
        return WorkResult(code=0, msg='文件已移入回收站', content=None)


    async def restoreFile(self, accountId: str, groupId: str, fileId: str) -> WorkResult:
        '''
        恢复已软删除的文件，使其重新在组内可见

        Args:
            accountId: 发起请求的账户标识
            groupId: 文件所在组标识
            fileId: 目标文件标识

        Returns:
            WorkResult: 恢复成功时 code 为 0，content 为 None；
                        非组内成员返回 2002；文件不存在或不属于该组返回 3010
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.groupId != groupId:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        _ = await self.mysql.updateRecord(
            fileModel, {'atDeleted': None}, fileId=fileId
        )
        return WorkResult(code=0, msg='文件已恢复', content=None)


    async def hardDeleteFile(self, accountId: str, groupId: str, fileId: str) -> WorkResult:
        '''
        物理删除回收站中的文件，并清理其页面关联与实际存储

        Args:
            accountId: 发起请求的账户标识
            groupId: 文件所在组标识
            fileId: 目标文件标识

        Returns:
            WorkResult: 删除成功时 code 为 0，content 为 None；
                        非组内成员返回 2002；文件不存在或不属于该组返回 3010；
                        文件未处于软删除状态返回 3013
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.groupId != groupId:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        if file.atDeleted is None:
            return WorkResult(code=3013, msg='文件未处于回收站中', content=None)
        publicRelations: list[publicPageAndFileModel] = await self.mysql.listRecords(
            publicPageAndFileModel, fileId=fileId
        )
        for relation in publicRelations:
            _ = await self.mysql.deleteRecord(
                publicPageAndFileModel,
                publicPageId=relation.publicPageId,
                fileId=fileId
            )
        specificRelations: list[specificPageAndFileModel] = await self.mysql.listRecords(
            specificPageAndFileModel, fileId=fileId
        )
        for relation in specificRelations:
            _ = await self.mysql.deleteRecord(
                specificPageAndFileModel,
                specificPageId=relation.specificPageId,
                fileId=fileId
            )
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is not None:
            store = self.rustFs.generateStore(group.storageFieldKey)
            _ = await self.rustFs.delete(store, fileId)
        _ = await self.mysql.deleteRecord(fileModel, fileId=fileId)
        return WorkResult(code=0, msg='文件已物理删除', content=None)


    async def getGroupStorageQuota(self, accountId: str, groupId: str) -> WorkResult:
        '''
        获取指定组的存储配额与已用空间信息

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为配额信息字典；
                        非组内成员时返回 2002，存储信息获取失败时返回 2001
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
        quotaInfo: tuple[int, int] | None = await self.rustFs.getBucketQuota(group.storageFieldKey)
        if quotaInfo is None:
            return WorkResult(code=2001, msg='获取失败', content=None)
        quotaBytes, occupiedBytes = quotaInfo
        return WorkResult(
            code=0,
            msg='获取成功',
            content={
                'groupId': group.groupId,
                'groupName': group.name,
                'size': quotaBytes,
                'occupied': occupiedBytes
            }
        )


    async def getAllPublicPages(self) -> WorkResult:
        '''
        获取系统中全部组的公开页信息

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为公开页列表
        '''
        groups: list[groupModel] = await self.mysql.listRecords(groupModel)
        publicPageList: list[dict[str, str]] = [
            {
                'groupId': group.groupId,
                'groupName': group.name,
                'publicPageId': group.publicPageId,
                'announcement': group.publicPageAnnouncement
            }
            for group in groups
        ]
        return WorkResult(code=0, msg='获取成功', content=publicPageList)


    async def getVisiblePages(self, accountId: str) -> WorkResult:
        '''
        获取当前账户所在组可见的全部指定页信息

        Args:
            accountId: 发起请求的账户标识

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为可见指定页列表
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        if account is None or account.beInGroupId is None:
            return WorkResult(code=0, msg='获取成功', content=[])
        relations: list[groupAndSpecificModel] = await self.mysql.listRecords(
            groupAndSpecificModel, provideToGroupId=account.beInGroupId
        )
        visiblePageList: list[dict[str, str]] = []
        for relation in relations:
            pageRecord: specificPageModel | None = await self.mysql.getRecord(
                specificPageModel, specificPageId=relation.specificPageId
            )
            if pageRecord is None:
                continue
            ownerGroup: groupModel | None = await self.mysql.getRecord(
                groupModel, groupId=pageRecord.ownerGroupId
            )
            if ownerGroup is None:
                continue
            visiblePageList.append({
                'groupId': ownerGroup.groupId,
                'groupName': ownerGroup.name,
                'specificPageId': pageRecord.specificPageId,
                'announcement': pageRecord.announcement
            })
        return WorkResult(code=0, msg='获取成功', content=visiblePageList)


    async def getGroupSpecificPages(self, accountId: str, groupId: str) -> WorkResult:
        '''
        获取当前所在组拥有的全部指定页信息

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为指定页列表；
                        非组内成员返回 2002
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
        pages: list[specificPageModel] = await self.mysql.listRecords(
            specificPageModel, ownerGroupId=groupId
        )
        specificPageList: list[dict[str, Any]] = []
        for pageRecord in pages:
            visibleRelations: list[groupAndSpecificModel] = await self.mysql.listRecords(
                groupAndSpecificModel, specificPageId=pageRecord.specificPageId
            )
            visibleGroups: list[str] = [
                relation.provideToGroupId for relation in visibleRelations
            ]
            specificPageList.append({
                'specificPageId': pageRecord.specificPageId,
                'visibleGroups': visibleGroups,
                'announcement': pageRecord.announcement
            })
        return WorkResult(code=0, msg='获取成功', content=specificPageList)


    async def createSpecificPage(
        self, accountId: str, groupId: str, announcement: str, visibleGroups: list[str]
    ) -> WorkResult:
        '''
        为当前所在组创建指定页并配置可见组

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            announcement: 指定页公告内容
            visibleGroups: 可见该指定页的组标识列表

        Returns:
            WorkResult: 创建成功时 code 为 0，content 为创建的指定页信息；
                        参数不合法返回 1002；非组管理员返回 2002
        '''
        if not _isValidAnnouncement(announcement) or not _isValidVisibleGroups(visibleGroups):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        if not await self._isGroupAdmin(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        specificPageId: str = generateIdentificationFileCode()
        uniqueVisibleGroups: list[str] = list(dict.fromkeys(visibleGroups))
        pageRecord: specificPageModel = specificPageModel(
            specificPageId=specificPageId,
            ownerGroupId=groupId,
            announcement=announcement
        )
        _ = await self.mysql.createRecord(pageRecord)
        for targetGroupId in uniqueVisibleGroups:
            relation: groupAndSpecificModel = groupAndSpecificModel(
                specificPageId=specificPageId,
                provideToGroupId=targetGroupId
            )
            _ = await self.mysql.createRecord(relation)
        return WorkResult(
            code=0,
            msg='指定页创建成功',
            content={
                'specificPageId': specificPageId,
                'visibleGroups': uniqueVisibleGroups,
                'announcement': announcement
            }
        )


    async def updatePublicPageAnnouncement(
        self, accountId: str, groupId: str, publicPageId: str, announcement: str
    ) -> WorkResult:
        '''
        修改指定组公开页的公告内容

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            publicPageId: 目标公开页标识
            announcement: 新的公告内容

        Returns:
            WorkResult: 修改成功时 code 为 0，content 为更新后的公开页信息；
                        参数不合法返回 1002；非组管理员返回 2002；
                        页面不存在返回 3022；归属检查不通过返回 3023
        '''
        if not _isValidAnnouncement(announcement):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        if not await self._isGroupAdmin(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3022, msg='对应的页面不存在', content=None)
        if group.publicPageId != publicPageId:
            return WorkResult(code=3023, msg='归属检查不通过', content=None)
        updatedGroup: groupModel | None = await self.mysql.updateRecord(
            groupModel, {'publicPageAnnouncement': announcement}, groupId=groupId
        )
        if updatedGroup is None:
            return WorkResult(code=3022, msg='对应的页面不存在', content=None)
        return WorkResult(
            code=0,
            msg='公开页公告修改成功',
            content={
                'publicPageId': updatedGroup.publicPageId,
                'announcement': updatedGroup.publicPageAnnouncement
            }
        )


    async def updateSpecificPageAnnouncement(
        self, accountId: str, groupId: str, specificPageId: str, announcement: str
    ) -> WorkResult:
        '''
        修改指定页的公告内容

        Args:
            accountId: 发起请求的账户标识
            groupId: 指定页所属组标识
            specificPageId: 目标指定页标识
            announcement: 新的公告内容

        Returns:
            WorkResult: 修改成功时 code 为 0，content 为更新后的指定页信息；
                        参数不合法返回 1002；非组管理员返回 2002；
                        页面不存在或不属于该组返回 3022
        '''
        if not _isValidAnnouncement(announcement):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        if not await self._isGroupAdmin(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        pageRecord: specificPageModel | None = await self.mysql.getRecord(
            specificPageModel, specificPageId=specificPageId
        )
        if pageRecord is None or pageRecord.ownerGroupId != groupId:
            return WorkResult(code=3022, msg='对应的页面不存在', content=None)
        updatedPage: specificPageModel | None = await self.mysql.updateRecord(
            specificPageModel, {'announcement': announcement}, specificPageId=specificPageId
        )
        if updatedPage is None:
            return WorkResult(code=3022, msg='对应的页面不存在', content=None)
        visibleRelations: list[groupAndSpecificModel] = await self.mysql.listRecords(
            groupAndSpecificModel, specificPageId=specificPageId
        )
        visibleGroups: list[str] = [
            relation.provideToGroupId for relation in visibleRelations
        ]
        return WorkResult(
            code=0,
            msg='指定页公告修改成功',
            content={
                'specificPageId': updatedPage.specificPageId,
                'visibleGroups': visibleGroups,
                'announcement': updatedPage.announcement
            }
        )


    async def updateSpecificPageVisibleGroups(
        self, accountId: str, groupId: str, specificPageId: str, visibleGroups: list[str]
    ) -> WorkResult:
        '''
        修改指定页的可见组配置

        Args:
            accountId: 发起请求的账户标识
            groupId: 指定页所属组标识
            specificPageId: 目标指定页标识
            visibleGroups: 新的可见组标识列表

        Returns:
            WorkResult: 修改成功时 code 为 0，content 为更新后的指定页信息；
                        参数不合法返回 1002；非组管理员返回 2002；
                        页面不存在或不属于该组返回 3022
        '''
        if not _isValidVisibleGroups(visibleGroups):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        if not await self._isGroupAdmin(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        pageRecord: specificPageModel | None = await self.mysql.getRecord(
            specificPageModel, specificPageId=specificPageId
        )
        if pageRecord is None or pageRecord.ownerGroupId != groupId:
            return WorkResult(code=3022, msg='对应的页面不存在', content=None)
        oldRelations: list[groupAndSpecificModel] = await self.mysql.listRecords(
            groupAndSpecificModel, specificPageId=specificPageId
        )
        for relation in oldRelations:
            _ = await self.mysql.deleteRecord(
                groupAndSpecificModel,
                specificPageId=specificPageId,
                provideToGroupId=relation.provideToGroupId
            )
        uniqueVisibleGroups: list[str] = list(dict.fromkeys(visibleGroups))
        for targetGroupId in uniqueVisibleGroups:
            relation: groupAndSpecificModel = groupAndSpecificModel(
                specificPageId=specificPageId,
                provideToGroupId=targetGroupId
            )
            _ = await self.mysql.createRecord(relation)
        return WorkResult(
            code=0,
            msg='指定页可见组修改成功',
            content={
                'specificPageId': specificPageId,
                'visibleGroups': uniqueVisibleGroups,
                'announcement': pageRecord.announcement
            }
        )


    async def addFileToPublicPage(self, accountId: str, groupId: str, fileId: str) -> WorkResult:
        '''
        将指定文件添加到当前所在组的公开页

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            fileId: 目标文件标识

        Returns:
            WorkResult: 添加成功时 code 为 0，content 为 None；
                        非组内成员返回 2002；文件不存在或不属于该组返回 3010
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.groupId != groupId or file.atDeleted is not None:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        existingRelation: publicPageAndFileModel | None = await self.mysql.getRecord(
            publicPageAndFileModel,
            publicPageId=group.publicPageId,
            fileId=fileId
        )
        if existingRelation is None:
            relation: publicPageAndFileModel = publicPageAndFileModel(
                publicPageId=group.publicPageId,
                fileId=fileId
            )
            _ = await self.mysql.createRecord(relation)
        return WorkResult(code=0, msg='文件已添加到公开页', content=None)


    async def removeFileFromPublicPage(self, accountId: str, groupId: str, fileId: str) -> WorkResult:
        '''
        将指定文件从当前所在组的公开页移除

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            fileId: 目标文件标识

        Returns:
            WorkResult: 移除成功时 code 为 0，content 为 None；
                        非组内成员返回 2002
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        _ = await self.mysql.deleteRecord(
            publicPageAndFileModel,
            publicPageId=group.publicPageId,
            fileId=fileId
        )
        return WorkResult(code=0, msg='文件已从公开页移除', content=None)


    async def addFileToSpecificPage(
        self, accountId: str, groupId: str, specificPageId: str, fileId: str
    ) -> WorkResult:
        '''
        将指定文件添加到当前所在组拥有的指定页

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            specificPageId: 目标指定页标识
            fileId: 目标文件标识

        Returns:
            WorkResult: 添加成功时 code 为 0，content 为 None；
                        非组内成员返回 2002；指定页不存在或不属于该组返回 3009；
                        文件不存在或不属于该组返回 3010
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        pageRecord: specificPageModel | None = await self.mysql.getRecord(
            specificPageModel, specificPageId=specificPageId
        )
        if pageRecord is None or pageRecord.ownerGroupId != groupId:
            return WorkResult(code=3009, msg='对应的指定页不存在', content=None)
        file: fileModel | None = await self.mysql.getRecord(fileModel, fileId=fileId)
        if file is None or file.groupId != groupId or file.atDeleted is not None:
            return WorkResult(code=3010, msg='对应的文件不存在', content=None)
        existingRelation: specificPageAndFileModel | None = await self.mysql.getRecord(
            specificPageAndFileModel,
            specificPageId=specificPageId,
            fileId=fileId
        )
        if existingRelation is None:
            relation: specificPageAndFileModel = specificPageAndFileModel(
                specificPageId=specificPageId,
                fileId=fileId
            )
            _ = await self.mysql.createRecord(relation)
        return WorkResult(code=0, msg='文件已添加到指定页', content=None)


    async def deleteSpecificPage(self, accountId: str, groupId: str, specificPageId: str) -> WorkResult:
        '''
        删除指定页及其全部关联配置

        Args:
            accountId: 发起请求的账户标识
            groupId: 指定页所属组标识
            specificPageId: 目标指定页标识

        Returns:
            WorkResult: 删除成功时 code 为 0，content 为 None；
                        非组管理员返回 2002；页面不存在或不属于该组返回 3022
        '''
        if not await self._isGroupAdmin(accountId, groupId):
            return WorkResult(code=2002, msg='无权限删除', content=None)
        pageRecord: specificPageModel | None = await self.mysql.getRecord(
            specificPageModel, specificPageId=specificPageId
        )
        if pageRecord is None or pageRecord.ownerGroupId != groupId:
            return WorkResult(code=3022, msg='对应的页面不存在', content=None)
        pageFileRelations: list[specificPageAndFileModel] = await self.mysql.listRecords(
            specificPageAndFileModel, specificPageId=specificPageId
        )
        for relation in pageFileRelations:
            _ = await self.mysql.deleteRecord(
                specificPageAndFileModel,
                specificPageId=specificPageId,
                fileId=relation.fileId
            )
        visibleRelations: list[groupAndSpecificModel] = await self.mysql.listRecords(
            groupAndSpecificModel, specificPageId=specificPageId
        )
        for relation in visibleRelations:
            _ = await self.mysql.deleteRecord(
                groupAndSpecificModel,
                specificPageId=specificPageId,
                provideToGroupId=relation.provideToGroupId
            )
        _ = await self.mysql.deleteRecord(specificPageModel, specificPageId=specificPageId)
        return WorkResult(code=0, msg='删除成功', content=None)


    async def removeFileFromSpecificPage(
        self, accountId: str, groupId: str, specificPageId: str, fileId: str
    ) -> WorkResult:
        '''
        将指定文件从当前所在组拥有的指定页移除

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识
            specificPageId: 目标指定页标识
            fileId: 目标文件标识

        Returns:
            WorkResult: 移除成功时 code 为 0，content 为 None；
                        非组内成员返回 2002
        '''
        if not await self._isGroupMember(accountId, groupId):
            return WorkResult(code=2002, msg='不具备操作权限', content=None)
        _ = await self.mysql.deleteRecord(
            specificPageAndFileModel,
            specificPageId=specificPageId,
            fileId=fileId
        )
        return WorkResult(code=0, msg='文件已从指定页移除', content=None)


    async def registerFileRecord(
        self, groupId: str, name: str, label: str, size: int, uploader: str
    ) -> WorkResult:
        '''
        注册文件元数据记录，供文件上传服务完成上传后同步信息到全局

        Args:
            groupId: 文件所属组标识
            name: 文件名称
            label: 文件标签
            size: 文件大小（字节）
            uploader: 上传者的账户标识

        Returns:
            WorkResult: 注册成功时 code 为 0，content 为完整的文件信息
        '''
        fileId: str = generateIdentificationFileCode()
        file: fileModel = fileModel(
            fileId=fileId,
            name=name,
            label=label,
            atDeleted=None,
            groupId=groupId,
            atCreated=datetime.now(),
            size=size,
            uploader=uploader
        )
        _ = await self.mysql.createRecord(file)
        uploaderAccount: accountModel | None = await self.mysql.getRecord(
            accountModel, accountId=uploader
        )
        uploaderName: str = uploaderAccount.name if uploaderAccount is not None else ''
        return WorkResult(
            code=0,
            msg='文件注册成功',
            content=self._serializeFileInfo(file, uploaderName)
        )











