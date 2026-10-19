
import asyncio
import hashlib
import hmac
import json
import secrets
from dataclasses import asdict
from typing import Any

from obstore.store import S3Store

from interface.data.mysqlInteraction import (
    MySqlInteraction,
    accountModel,
    fileModel,
    groupModel,
    sysAccountModel
)
from interface.data.redisInteraction import RedislInteraction
from interface.data.rustFslInteraction import RustFsInteraction
from interface.tools.globalTools import (
    ConfigObject,
    generateIdentificationAccountCode,
    generateIdentificationBucketCode,
    generateIdentificationFileCode,
    loadConfig
)
from interface.tools.networkDomainManager import (
    isValidNetworkDomain,
    networkDomainManager
)
from interface.work.workCommon import (
    SESSION_PREFIX,
    SESSION_TTL,
    SessionInfo,
    WorkResult
)



PBKDF2_ITERATIONS       : int                   = 100000
GROUP_NAME_MAX_LENGTH   : int                   = 255



class SystemWork:
    '''
    系统管理业务逻辑类
    ~~~
    负责系统管理员登录、在线用户查看、组管理、组内成员管理与存储配额管理等业务处理，
    并对接 MySQL、Redis 与 RustFS 数据层，独立于其它微服务
    '''

    def __init__(self, mysql: MySqlInteraction | None = None, redis: RedislInteraction | None = None, rustFs: RustFsInteraction | None = None) -> None:
        '''
        初始化 SystemWork 业务对象

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


    def _computePasswordHash(self, password: str) -> str:
        '''
        同步计算密码的 PBKDF2-HMAC-SHA256 哈希值

        Args:
            password: 明文密码

        Returns:
            str: 形如 pbkdf2_sha256$迭代次数$盐$哈希的存储字符串
        '''
        saltBytes: bytes = secrets.token_bytes(16)
        derivedBytes: bytes = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), saltBytes, PBKDF2_ITERATIONS
        )
        return f'pbkdf2_sha256${PBKDF2_ITERATIONS}${saltBytes.hex()}${derivedBytes.hex()}'


    async def _hashPassword(self, password: str) -> str:
        '''
        异步计算密码哈希，避免阻塞事件循环

        Args:
            password: 明文密码

        Returns:
            str: 密码哈希存储字符串
        '''
        return await asyncio.to_thread(self._computePasswordHash, password)


    def _checkPassword(self, password: str, storedHash: str) -> bool:
        '''
        同步校验明文密码与存储哈希是否匹配

        Args:
            password: 待校验的明文密码
            storedHash: 数据库中存储的密码哈希串

        Returns:
            bool: 匹配返回 True，否则返回 False
        '''
        parts: list[str] = storedHash.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        try:
            saltBytes: bytes = bytes.fromhex(parts[2])
            expectedBytes: bytes = bytes.fromhex(parts[3])
        except ValueError:
            return False
        iterations: int = int(parts[1])
        actualBytes: bytes = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), saltBytes, iterations
        )
        return hmac.compare_digest(actualBytes, expectedBytes)


    async def _verifyPassword(self, password: str, storedHash: str) -> bool:
        '''
        异步校验明文密码与存储哈希是否匹配

        Args:
            password: 待校验的明文密码
            storedHash: 数据库中存储的密码哈希串

        Returns:
            bool: 匹配返回 True，否则返回 False
        '''
        return await asyncio.to_thread(self._checkPassword, password, storedHash)


    async def createSession(self, accountId: str, sysAdmin: bool = False) -> str:
        '''
        为指定账户或系统管理员创建会话并写入 Redis

        Args:
            accountId: 账户或系统管理员唯一标识
            sysAdmin: 是否为系统管理员会话，为 True 时跳过普通账户信息查询

        Returns:
            str: 生成的会话令牌（Cookie 值）
        '''
        email: str = ''
        groupId: str | None = None
        groupName: str | None = None
        if not sysAdmin:
            account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
            if account is not None:
                email = account.email
                groupId = account.beInGroupId
                if groupId is not None:
                    group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
                    if group is not None:
                        groupName = group.name
        sessionInfo: SessionInfo = SessionInfo(
            id=accountId, email=email, groupId=groupId, groupName=groupName, sysAdmin=sysAdmin
        )
        sessionPayload: str = json.dumps(asdict(sessionInfo))
        while True:
            token: str = secrets.token_urlsafe(32)
            created: bool = await self.redis.create(
                f'{SESSION_PREFIX}{token}', sessionPayload, ex=SESSION_TTL
            )
            if created:
                return token


    async def destroySession(self, token: str) -> None:
        '''
        销毁指定令牌对应的会话

        Args:
            token: 会话令牌

        Returns:
            None: 无返回值
        '''
        _ = await self.redis.delete(f'{SESSION_PREFIX}{token}')


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
            payload: dict[str, Any] = json.loads(rawPayload)
            sessionId: str | None = payload.get('id')
            sessionEmail: str | None = payload.get('email')
            if sessionId is None or sessionEmail is None:
                return None
            return SessionInfo(
                id=sessionId,
                email=sessionEmail,
                groupId=payload.get('groupId'),
                groupName=payload.get('groupName'),
                sysAdmin=bool(payload.get('sysAdmin', False))
            )
        except (json.JSONDecodeError, TypeError):
            return None


    async def loginSysAdmin(self, id: str, password: str) -> WorkResult:
        '''
        系统管理员登录

        Args:
            id: 系统管理员标识
            password: 明文密码

        Returns:
            WorkResult: 登录成功时 code 为 0，携带会话令牌；校验失败返回 3002
        '''
        sysAccount: sysAccountModel | None = await self.mysql.getRecord(sysAccountModel, id=id)
        if sysAccount is None or not password == sysAccount.pw:
            return WorkResult(code=3002, msg='登录失败', content=None)
        # 不允许同一管理员账户同时在线，登录前清除该管理员已有的全部会话
        for key, sessionInfo in await self._listOnlineSessions():
            if sessionInfo.sysAdmin and sessionInfo.id == id:
                _ = await self.redis.delete(key)
        token: str = await self.createSession(id, sysAdmin=True)
        return WorkResult(
            code=0,
            msg='登录成功',
            content={
                'userId': id,
                'userName': id,
                'email': '',
                'groupId': None
            },
            token=token
        )


    async def _listOnlineSessions(self) -> list[tuple[str, SessionInfo]]:
        '''
        扫描 Redis 中全部有效会话

        Returns:
            list[tuple[str, SessionInfo]]: （会话键, 会话信息）列表，无效键已跳过
        '''
        sessionList: list[tuple[str, SessionInfo]] = []
        async for key in self.redis.client.scan_iter(match=f'{SESSION_PREFIX}*'): # type: ignore
            rawPayload: str | None = await self.redis.read(key) # type: ignore
            if rawPayload is None:
                continue
            try:
                payload: dict[str, Any] = json.loads(rawPayload)
                sessionId: str | None = payload.get('id')
                sessionEmail: str | None = payload.get('email')
                if sessionId is None or sessionEmail is None:
                    continue
                sessionInfo: SessionInfo = SessionInfo(
                    id=sessionId,
                    email=sessionEmail,
                    groupId=payload.get('groupId'),
                    groupName=payload.get('groupName'),
                    sysAdmin=bool(payload.get('sysAdmin', False))
                )
                sessionList.append((key, sessionInfo)) # type: ignore
            except (json.JSONDecodeError, TypeError):
                continue
        return sessionList


    async def _kickGroupSessions(self, groupId: str) -> None:
        '''
        踢下线指定组的所有在线会话

        Args:
            groupId: 目标组标识

        Returns:
            None: 无返回值
        '''
        for key, sessionInfo in await self._listOnlineSessions():
            if sessionInfo.groupId == groupId:
                _ = await self.redis.delete(key)


    async def getOnlineUsers(self) -> WorkResult:
        '''
        获取当前在线用户信息

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为在线用户列表
        '''
        sessionList: list[tuple[str, SessionInfo]] = await self._listOnlineSessions()
        userList: list[dict[str, Any]] = []
        for _, sessionInfo in sessionList:
            if sessionInfo.sysAdmin:
                userName: str = sessionInfo.id
            else:
                account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=sessionInfo.id)
                userName = account.name if account is not None else ''
            userList.append({
                'userId': sessionInfo.id,
                'email': sessionInfo.email,
                'userName': userName,
                'groupId': sessionInfo.groupId,
                'groupName': sessionInfo.groupName
            })
        return WorkResult(code=0, msg='获取成功', content=userList)


    async def getAllGroupsWithMembers(self) -> WorkResult:
        '''
        获取所有组的信息和对应的成员信息

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为组列表
        '''
        groups: list[groupModel] = await self.mysql.listRecords(groupModel)
        groupList: list[dict[str, Any]] = []
        for group in groups:
            members: list[accountModel] = await self.mysql.listRecords(accountModel, beInGroupId=group.groupId)
            groupList.append({
                'groupId': group.groupId,
                'groupName': group.name,
                'members': [
                    {
                        'userId': member.accountId,
                        'userName': member.name,
                        'email': member.email,
                        'isAdmin': member.admin == 1
                    }
                    for member in members
                ]
            })
        return WorkResult(code=0, msg='获取成功', content=groupList)


    async def getGroupMembers(self, groupId: str) -> WorkResult:
        '''
        获取指定组中的成员信息

        Args:
            groupId: 目标组标识

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为成员列表；
                        目标组不存在返回 3005
        '''
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3005, msg='对应的组不存在', content=None)
        members: list[accountModel] = await self.mysql.listRecords(accountModel, beInGroupId=groupId)
        memberList: list[dict[str, str]] = [
            {
                'userId': member.accountId,
                'userName': member.name,
                'email': member.email
            }
            for member in members
        ]
        return WorkResult(code=0, msg='获取成功', content=memberList)


    async def createGroup(self, groupName: str) -> WorkResult:
        '''
        创建组

        Args:
            groupName: 组名称

        Returns:
            WorkResult: 创建成功时 code 为 0，content 为新建组信息；
                        名称非法返回 1002
        '''
        if not groupName or len(groupName) > GROUP_NAME_MAX_LENGTH:
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        groupId: str = generateIdentificationAccountCode()
        storageFieldKey: str = generateIdentificationBucketCode()
        publicPageId: str = generateIdentificationFileCode()
        group: groupModel = groupModel(
            groupId=groupId,
            name=groupName,
            storageFieldKey=storageFieldKey,
            publicPageId=publicPageId,
            publicPageAnnouncement=''
        )

        if not await self.rustFs.createBucket(storageFieldKey):
            return WorkResult(code=4000, msg='创建失败', content=None)
            # TODO
            # 此处 code 的值不在标准中，后面需要补上

        _ = await self.mysql.createRecord(group)
        return WorkResult(code=0, msg='创建成功', content={'groupId': groupId, 'groupName': groupName})



    async def deleteGroup(self, groupId: str) -> WorkResult:
        '''
        删除组

        Args:
            groupId: 目标组标识

        Returns:
            WorkResult: 删除成功时 code 为 0；目标组不存在返回 3005
        '''
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3005, msg='对应的组不存在', content=None)
        files: list[fileModel] = await self.mysql.listRecords(fileModel, groupId=groupId)
        store: S3Store = self.rustFs.generateStore(group.storageFieldKey)
        for file in files:
            _ = await self.rustFs.delete(store, file.fileId)
        for file in files:
            _ = await self.mysql.deleteRecord(fileModel, fileId=file.fileId)
        _ = await self.mysql.deleteRecord(groupModel, groupId=groupId)
        bucketDeleted: bool = await self.rustFs.deleteBucket(group.storageFieldKey)
        await self._kickGroupSessions(groupId)
        return WorkResult(code=0, msg='删除成功', content=None)


    async def renameGroup(self, groupId: str, groupName: str) -> WorkResult:
        '''
        修改组名

        Args:
            groupId: 目标组标识
            groupName: 新的组名称

        Returns:
            WorkResult: 修改成功时 code 为 0；名称非法返回 1002；
                        目标组不存在返回 3005
        '''
        if not groupName or len(groupName) > GROUP_NAME_MAX_LENGTH:
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3005, msg='对应的组不存在', content=None)
        _ = await self.mysql.updateRecord(groupModel, {'name': groupName}, groupId=groupId)
        await self._kickGroupSessions(groupId)
        return WorkResult(code=0, msg='修改成功', content=None)


    async def appointAdministrator(self, groupId: str, userId: str) -> WorkResult:
        '''
        将指定成员任命为组管理员

        Args:
            groupId: 目标组标识
            userId: 目标成员账户标识

        Returns:
            WorkResult: 任命成功时 code 为 0；账户不存在返回 3021；
                        目标组不存在返回 3005
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=userId)
        if account is None:
            return WorkResult(code=3021, msg='对应的账户不存在', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3005, msg='对应的组不存在', content=None)
        _ = await self.mysql.updateRecord(accountModel, {'admin': 1}, accountId=userId)
        return WorkResult(code=0, msg='任命成功', content=None)


    async def dismissAdministrator(self, groupId: str, userId: str) -> WorkResult:
        '''
        将指定成员免除组管理员

        Args:
            groupId: 目标组标识
            userId: 目标成员账户标识

        Returns:
            WorkResult: 免除成功时 code 为 0；账户不存在返回 3021；
                        目标组不存在返回 3005
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=userId)
        if account is None:
            return WorkResult(code=3021, msg='对应的账户不存在', content=None)
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3005, msg='对应的组不存在', content=None)
        _ = await self.mysql.updateRecord(accountModel, {'admin': 0}, accountId=userId)
        return WorkResult(code=0, msg='免除成功', content=None)


    async def getGroupJoinRequests(self, groupId: str) -> WorkResult:
        '''
        获取申请加入指定组的请求列表

        Args:
            groupId: 目标组标识

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为申请者列表
        '''
        applicants: list[accountModel] = await self.mysql.listRecords(
            accountModel, applicationGroupId=groupId
        )
        applicantList: list[dict[str, str]] = [
            {
                'userId': applicant.accountId,
                'email': applicant.email,
                'userName': applicant.name
            }
            for applicant in applicants
        ]
        return WorkResult(code=0, msg='获取成功', content=applicantList)


    async def reviewGroupJoinRequest(self, groupId: str, userId: str, status: str) -> WorkResult:
        '''
        审批加入组的请求

        Args:
            groupId: 目标组标识
            userId: 申请者的账户标识
            status: 审批结果，仅支持 APPROVED 或 REJECTED

        Returns:
            WorkResult: 审批成功时 code 为 0；状态非法返回 1002；
                        无对应申请返回 3006
        '''
        if status not in ('APPROVED', 'REJECTED'):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        applicant: accountModel | None = await self.mysql.getRecord(accountModel, accountId=userId)
        if applicant is None or applicant.applicationGroupId != groupId:
            return WorkResult(code=3006, msg='申请已失效', content=None)
        if status == 'APPROVED':
            _ = await self.mysql.updateRecord(
                accountModel,
                {'beInGroupId': groupId, 'applicationGroupId': None},
                accountId=userId
            )
            return WorkResult(code=0, msg='加入请求已批准', content=None)
        _ = await self.mysql.updateRecord(
            accountModel, {'applicationGroupId': None}, accountId=userId
        )
        return WorkResult(code=0, msg='加入请求已拒绝', content=None)


    async def getStorageInfo(self) -> WorkResult:
        '''
        获取存储系统使用情况

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为整体与各组存储信息；
                        RustFS 操作失败返回 4001
        '''
        try:
            globalQuota: dict[str, int] = await self.rustFs.getGlobalQuota()
        except Exception:
            return WorkResult(code=4001, msg='获取失败', content=None)
        totalCapacity: int = globalQuota.get('totalCapacity', 0)
        totalUsed: int = globalQuota.get('totalUsed', 0)
        # 整体未限制配额时 size 为 -1
        size: int = totalCapacity if totalCapacity > 0 else -1 # type: ignore

        groups: list[groupModel] = await self.mysql.listRecords(groupModel)
        groupInfo: list[dict[str, Any]] = []
        for group in groups:
            quotaInfo: tuple[int, int] | None = await self.rustFs.getBucketQuota(group.storageFieldKey)
            if quotaInfo is None:
                continue
            quota, occupied = quotaInfo
            groupSize: int = quota if quota is not None and quota > 0 else -1 # type: ignore
            groupInfo.append({
                'groupId': group.groupId,
                'groupName': group.name,
                'size': groupSize,
                'occupied': occupied
            })
        return WorkResult(code=0, msg='获取成功', content={
            'size': size,
            'occupied': totalUsed,
            'groupInfo': groupInfo
        })


    async def getGroupsStorageQuota(self) -> WorkResult:
        '''
        获取所有组的存储空间配额信息

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为各组配额列表，
                        未进行配额的组 size 为 -1
        '''
        groups: list[groupModel] = await self.mysql.listRecords(groupModel)
        quotaList: list[dict[str, Any]] = []
        for group in groups:
            quotaInfo: tuple[int, int] | None = await self.rustFs.getBucketQuota(group.storageFieldKey)
            if quotaInfo is None:
                continue
            quota, occupied = quotaInfo
            size: int = quota if quota is not None and quota > 0 else -1 # type: ignore
            quotaList.append({
                'groupId': group.groupId,
                'groupName': group.name,
                'size': size,
                'occupied': occupied
            })
        return WorkResult(code=0, msg='获取成功', content=quotaList)


    async def setGroupStorageQuota(self, groupId: str, size: int) -> WorkResult:
        '''
        对指定组进行存储空间配额

        Args:
            groupId: 目标组标识
            size: 配额字节数，-1 表示不限制

        Returns:
            WorkResult: 设置成功时 code 为 0，content 为更新后的配额信息；
                        参数非法返回 1002；目标组不存在返回 3005；
                        RustFS 操作失败返回 4001
        '''
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3005, msg='对应的组不存在', content=None)
        if size < -1:
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        setSuccess: bool = await self.rustFs.setBucketQuota(group.storageFieldKey, size)
        if not setSuccess:
            return WorkResult(code=4001, msg='设置失败', content=None)
        quotaInfo: tuple[int, int] | None = await self.rustFs.getBucketQuota(group.storageFieldKey)
        if quotaInfo is None:
            return WorkResult(code=4001, msg='设置失败', content=None)
        quota, occupied = quotaInfo
        currentSize: int = quota if quota is not None and quota > 0 else -1 # type: ignore
        return WorkResult(code=0, msg='设置成功', content={
            'groupId': group.groupId,
            'groupName': group.name,
            'size': currentSize,
            'occupied': occupied
        })


    async def getAccessibleDomain(self) -> WorkResult:
        '''
        获取当前可访问域白名单列表

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为网络域列表；
                        Redis 中无配置时 content 为空列表
        '''
        allowIpList: list[str] | None = await networkDomainManager.getAllowIp()
        return WorkResult(
            code=0,
            msg='获取成功',
            content=allowIpList if allowIpList is not None else []
        )


    async def addAccessibleDomain(self, value: str) -> WorkResult:
        '''
        向可访问域白名单添加网络域

        Args:
            value: 待添加的网络域表达式

        Returns:
            WorkResult: 添加成功时 code 为 0，content 为最新列表；
                        网络域不合法返回 3020；
                        Redis 写入失败返回 2002（兜底错误码，非标准定义）
        '''
        if not isValidNetworkDomain(value):
            return WorkResult(code=3020, msg='网络域不合法', content=None)
        latestList: list[str] | None = await networkDomainManager.addAllowIp(value)
        if latestList is None:
            return WorkResult(code=2002, msg='操作失败', content=None)
        return WorkResult(code=0, msg='添加成功', content=latestList)


    async def deleteAccessibleDomain(self, value: str) -> WorkResult:
        '''
        从可访问域白名单移除网络域

        Args:
            value: 待移除的网络域表达式

        Returns:
            WorkResult: 删除成功时 code 为 0，content 为最新列表；
                        Redis 写入失败返回 2002（兜底错误码，非标准定义）
        '''
        latestList: list[str] | None = await networkDomainManager.deleteAllowIp(value)
        if latestList is None:
            return WorkResult(code=2002, msg='操作失败', content=None)
        return WorkResult(code=0, msg='删除成功', content=latestList)
