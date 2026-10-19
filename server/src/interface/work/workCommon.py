from dataclasses import dataclass
from typing import Any


TOKEN_KEY               : str                   = 'token'
SESSION_PREFIX          : str                   = 'session:'
SESSION_TTL             : int                   = 3600          # 用户 Session 有效期



@dataclass
class WorkResult:
    '''
    业务方法统一返回结果对象

    Attributes:
        code    : 业务错误码，0 表示成功
        msg     : 结果说明信息
        content : 业务数据，无数据时为 None
        token   : 需下发的会话令牌，无则保持 None
    '''
    code        : int
    msg         : str
    content     : Any
    token       : str | None = None


@dataclass
class SessionInfo:
    '''
    会话信息对象

    Attributes:
        id        : 账户唯一标识
        email     : 账户邮箱
        groupId   : 账户所在组标识，未入组时为 None
        groupName : 账户所在组名称，未入组时为 None
        sysAdmin  : 是否为系统管理员，普通用户会话为 False
    '''
    id          : str
    email       : str
    groupId     : str | None
    groupName   : str | None
    sysAdmin    : bool = False
