
import asyncio
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import asdict
from datetime import datetime

from interface.data.mysqlInteraction import MySqlInteraction, accountModel, groupModel
from interface.data.redisInteraction import RedislInteraction
from interface.tools.globalTools import ConfigObject, generateIdentificationAccountCode, loadConfig
from interface.work.workCommon import (
    SESSION_PREFIX,
    SESSION_TTL,
    TOKEN_KEY, # type: ignore
    SessionInfo,
    WorkResult
)



PBKDF2_ITERATIONS       : int                   = 100000
PASSWORD_MIN_LENGTH     : int                   = 6
PASSWORD_MAX_LENGTH     : int                   = 64
NAME_MAX_LENGTH         : int                   = 255
EMAIL_PATTERN           : re.Pattern[str]       = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _isValidEmail(email: str) -> bool:
    '''
    校验邮箱格式是否合法

    Args:
        email: 待校验的邮箱字符串

    Returns:
        bool: 邮箱格式合法返回 True，否则返回 False
    '''
    return EMAIL_PATTERN.match(email) is not None


def _isValidPassword(password: str) -> bool:
    '''
    校验密码长度是否在合法范围内

    Args:
        password: 待校验的密码字符串

    Returns:
        bool: 密码长度合法返回 True，否则返回 False
    '''
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH


def _isValidName(name: str) -> bool:
    '''
    校验用户名称是否非空且长度合法

    Args:
        name: 待校验的用户名称字符串

    Returns:
        bool: 名称合法返回 True，否则返回 False
    '''
    return bool(name) and len(name) <= NAME_MAX_LENGTH



class AccountWork:
    '''
    账户与组管理业务逻辑类
    ~~~
    负责账户注册登录、账户信息修改、组信息查询、入组申请与审批、退出组等业务处理，
    并对接 MySQL 与 Redis 数据层
    '''

    def __init__(self, mysql: MySqlInteraction | None = None, redis: RedislInteraction | None = None) -> None:
        '''
        初始化 AccountWork 业务对象

        Args:
            mysql: 可选的 MySQL 交互对象，未提供时依据配置文件自动构建
            redis: 可选的 Redis 交互对象，未提供时依据配置文件自动构建
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


    async def createSession(self, accountId: str) -> str:
        '''
        为指定账户创建会话并写入 Redis

        Args:
            accountId: 账户唯一标识

        Returns:
            str: 生成的会话令牌（Cookie 值）
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        groupId: str | None = None
        groupName: str | None = None
        email: str = ''
        if account is not None:
            email = account.email
            groupId = account.beInGroupId
            if groupId is not None:
                group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
                if group is not None:
                    groupName = group.name
        sessionInfo: SessionInfo = SessionInfo(
            id=accountId, email=email, groupId=groupId, groupName=groupName
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


    async def destroyAccountSessions(self, accountId: str) -> None:
        '''
        删除指定账户名下的全部会话

        Args:
            accountId: 账户唯一标识

        Returns:
            None: 无返回值
        '''
        sessionKeys: list[str] = await self.redis.scanKeys(f'{SESSION_PREFIX}*')
        matchedKeys: list[str] = []
        for sessionKey in sessionKeys:
            rawPayload: str | None = await self.redis.read(sessionKey)
            if rawPayload is None:
                continue
            try:
                payload: dict[str, str | None] = json.loads(rawPayload)
            except (json.JSONDecodeError, TypeError):
                continue
            if payload.get('id') == accountId:
                matchedKeys.append(sessionKey)
        if matchedKeys:
            _ = await self.redis.delete(*matchedKeys)


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


    async def registerAccount(self, email: str, password: str, userName: str) -> WorkResult:
        '''
        注册并登录新账户

        Args:
            email: 账户邮箱
            password: 明文密码
            userName: 用户名称

        Returns:
            WorkResult: 注册成功时 code 为 0，携带会话令牌；邮箱已存在返回 3001；
                        参数非法返回 1002
        '''
        if not _isValidEmail(email) or not _isValidPassword(password) or not _isValidName(userName):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        existingAccounts: list[accountModel] = await self.mysql.listRecords(accountModel, email=email)
        if existingAccounts:
            return WorkResult(code=3001, msg='已有对应的账户', content=None)
        accountId: str = generateIdentificationAccountCode()
        passwordHash: str = await self._hashPassword(password)
        account: accountModel = accountModel(
            accountId=accountId,
            email=email,
            pw=passwordHash,
            name=userName,
            atCreated=datetime.now(),
            admin=0,
            beInGroupId=None,
            applicationGroupId=None
        )
        _ = await self.mysql.createRecord(account)
        token: str = await self.createSession(accountId)
        return WorkResult(
            code=0,
            msg='注册成功',
            content={
                'userId': accountId,
                'userName': userName,
                'email': email,
                'groupId': None
            },
            token=token
        )


    async def loginAccount(self, email: str, password: str) -> WorkResult:
        '''
        登录已注册账户

        Args:
            email: 账户邮箱
            password: 明文密码

        Returns:
            WorkResult: 登录成功时 code 为 0，携带会话令牌；校验失败返回 3002；
                        参数非法返回 1002
        '''
        if not _isValidEmail(email) or not _isValidPassword(password):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        accounts: list[accountModel] = await self.mysql.listRecords(accountModel, email=email)
        if not accounts:
            return WorkResult(code=3002, msg='登录失败', content=None)
        account: accountModel = accounts[0]
        if not await self._verifyPassword(password, account.pw):
            return WorkResult(code=3002, msg='登录失败', content=None)
        await self.destroyAccountSessions(account.accountId)
        token: str = await self.createSession(account.accountId)
        return WorkResult(
            code=0,
            msg='登录成功',
            content={
                'userId': account.accountId,
                'userName': account.name,
                'email': account.email,
                'groupId': account.beInGroupId
            },
            token=token
        )


    async def changeUserName(self, accountId: str, userName: str) -> WorkResult:
        '''
        修改当前账户的用户名称

        Args:
            accountId: 账户唯一标识
            userName: 新的用户名称

        Returns:
            WorkResult: 修改成功时 code 为 0；账户不存在或名称非法返回 3003
        '''
        if not _isValidName(userName):
            return WorkResult(code=3003, msg='修改失败', content=None)
        updatedAccount: accountModel | None = await self.mysql.updateRecord(
            accountModel, {'name': userName}, accountId=accountId
        )
        if updatedAccount is None:
            return WorkResult(code=3003, msg='修改失败', content=None)
        return WorkResult(
            code=0,
            msg='修改成功',
            content={
                'userId': updatedAccount.accountId,
                'userName': updatedAccount.name,
                'email': updatedAccount.email
            }
        )


    async def changePassword(self, accountId: str, oldPassword: str, newPassword: str, oldToken: str | None) -> WorkResult:
        '''
        修改当前账户密码并重新签发会话

        Args:
            accountId: 账户唯一标识
            oldPassword: 原密码
            newPassword: 新密码
            oldToken: 当前会话令牌，用于修改成功后销毁旧会话

        Returns:
            WorkResult: 修改成功时 code 为 0，携带新会话令牌；账户不存在、
                        原密码错误或新密码非法返回 3004
        '''
        if not _isValidPassword(newPassword):
            return WorkResult(code=3004, msg='修改失败', content=None)
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        if account is None or not await self._verifyPassword(oldPassword, account.pw):
            return WorkResult(code=3004, msg='修改失败', content=None)
        passwordHash: str = await self._hashPassword(newPassword)
        updatedAccount: accountModel | None = await self.mysql.updateRecord(
            accountModel, {'pw': passwordHash}, accountId=accountId
        )
        if updatedAccount is None:
            return WorkResult(code=3004, msg='修改失败', content=None)
        if oldToken is not None:
            await self.destroySession(oldToken)
        newToken: str = await self.createSession(accountId)
        return WorkResult(
            code=0,
            msg='修改成功',
            content={
                'userId': updatedAccount.accountId,
                'userName': updatedAccount.name,
                'email': updatedAccount.email
            },
            token=newToken
        )


    async def getGroupMembers(self, accountId: str, groupId: str) -> WorkResult:
        '''
        获取指定组内的全部成员信息

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为成员列表；
                        当前账户不在该组内返回 2002
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        if account is None or account.beInGroupId != groupId:
            return WorkResult(code=2002, msg='不具备获取权限', content=None)
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


    async def getAllGroups(self) -> WorkResult:
        '''
        获取系统中的全部组信息

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为组列表
        '''
        groups: list[groupModel] = await self.mysql.listRecords(groupModel)
        groupList: list[dict[str, str]] = [
            {
                'groupId': group.groupId,
                'groupName': group.name
            }
            for group in groups
        ]
        return WorkResult(code=0, msg='获取成功', content=groupList)


    async def createJoinRequest(self, accountId: str, groupId: str) -> WorkResult:
        '''
        发起加入指定组的请求

        Args:
            accountId: 发起请求的账户标识
            groupId: 目标组标识

        Returns:
            WorkResult: 发起成功时 code 为 0；目标组不存在返回 3005
        '''
        group: groupModel | None = await self.mysql.getRecord(groupModel, groupId=groupId)
        if group is None:
            return WorkResult(code=3005, msg='对应的组不存在', content=None)
        _ = await self.mysql.updateRecord(
            accountModel, {'applicationGroupId': groupId}, accountId=accountId
        )
        return WorkResult(code=0, msg='发起加入请求成功', content=None)


    async def getJoinRequests(self, groupId: str) -> WorkResult:
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


    async def reviewJoinRequest(self, accountId: str, groupId: str, userId: str, status: str) -> WorkResult:
        '''
        审批加入组的请求

        Args:
            accountId: 发起审批的账户标识（须为本组管理员）
            groupId: 目标组标识
            requestId: 申请者的账户标识
            status: 审批结果，仅支持 APPROVED 或 REJECTED

        Returns:
            WorkResult: 审批成功时 code 为 0；参数非法返回 1002；
                        当前账户非本组管理员返回 2002；无对应申请返回 3006
        '''
        if status not in ('APPROVED', 'REJECTED'):
            return WorkResult(code=1002, msg='参数值不合法', content=None)
        adminAccount: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        if adminAccount is None or adminAccount.admin == 0 or adminAccount.beInGroupId != groupId:
            return WorkResult(code=2002, msg='不具备此权限', content=None)
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


    async def leaveGroup(self, accountId: str, groupId: str) -> WorkResult:
        '''
        退出指定组

        Args:
            accountId: 当前账户标识
            groupId: 请求退出的组标识

        Returns:
            WorkResult: 退出成功时 code 为 0；当前账户所在组与请求不符返回 3007
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        if account is None or account.beInGroupId != groupId:
            return WorkResult(code=3007, msg='实际所在的组与请求的组不符', content=None)
        _ = await self.mysql.updateRecord(
            accountModel,
            {'beInGroupId': None, 'applicationGroupId': None, 'admin': 0},
            accountId=accountId
        )
        return WorkResult(code=0, msg='已退出组', content=None)


    async def getIsAdmin(self, accountId: str) -> WorkResult:
        '''
        获取当前账户是否为组管理员

        Args:
            accountId: 当前账户唯一标识

        Returns:
            WorkResult: 获取成功时 code 为 0，content 为布尔值；
                        账户不存在时返回 3004
        '''
        account: accountModel | None = await self.mysql.getRecord(accountModel, accountId=accountId)
        if account is None:
            return WorkResult(code=3004, msg='获取失败', content=None)
        return WorkResult(code=0, msg='获取成功', content=account.admin != 0)








