
from __future__ import annotations
import json
import uuid
from typing import Any
from dataclasses import dataclass
from email.header import Header
from email.mime.text import MIMEText

import aiosmtplib



@dataclass
class ConfigObject:
    @dataclass
    class ServerConfig:
        host            : str
        port            : int
        @classmethod
        def fromDict(cls, data:dict[Any, Any]) -> ConfigObject.ServerConfig:
            return cls(
                host            = data['host'],
                port            = data['port']
            )

    @dataclass
    class MysqlConfig:
        host            : str
        port            : int
        user            : str
        pw              : str
        database        : str
        @classmethod
        def fromDict(cls, data:dict[Any, Any]) -> ConfigObject.MysqlConfig:
            return cls(
                host            = data['host'],
                port            = data['port'],
                user            = data['user'],
                pw              = data['pw'],
                database        = data['database']
            )

    @dataclass
    class RedisConfig:
        host            : str
        port            : int
        pw              : str
        db              : int
        @classmethod
        def fromDict(cls, data:dict[Any, Any]) -> ConfigObject.RedisConfig:
            return cls(
                host            = data['host'],
                port            = data['port'],
                pw              = data['pw'],
                db              = data['db']
            )

    @dataclass
    class RustFSConfig:
        endpointUrl     : str
        accessKey       : str
        secretKey       : str
        region          : str
        signatureUrl    : str
        @classmethod
        def fromDict(cls, data:dict[Any, Any]) -> ConfigObject.RustFSConfig:
            return cls(
                endpointUrl     = data['endpointUrl'],
                accessKey       = data['accessKey'],
                secretKey       = data['secretKey'],
                region          = data['region'],
                signatureUrl    = data['signatureUrl']
            )

    @dataclass
    class CorsConfig:
        allowOrigins        : list[str]
        allowCredentials    : bool
        allowMethods        : list[str]
        allowHeaders        : list[str]
        @classmethod
        def fromDict(cls, data:dict[Any, Any]) -> ConfigObject.CorsConfig:
            return cls(
                allowOrigins        = data['allowOrigins'],
                allowCredentials    = data['allowCredentials'],
                allowMethods        = data['allowMethods'],
                allowHeaders        = data['allowHeaders']
            )

    @dataclass
    class NetworkDomainConfig:
        update  : int
        allowIp : list[str]
        @classmethod
        def fromDict(cls, data:dict[Any, Any]) -> ConfigObject.NetworkDomainConfig:
            return cls(
                update  = data['update'],
                allowIp = data['allowIp']
            )

    server  : ServerConfig
    mysql   : MysqlConfig
    redis   : RedisConfig
    rustFS  : RustFSConfig
    cors    : CorsConfig
    networkDomain   : NetworkDomainConfig


    @classmethod
    def fromDict(cls, data:dict[Any, Any]) -> ConfigObject:
        return cls(
            server  = ConfigObject.ServerConfig.fromDict(data['server']),
            mysql   = ConfigObject.MysqlConfig.fromDict(data['mysql']),
            redis   = ConfigObject.RedisConfig.fromDict(data['redis']),
            rustFS  = ConfigObject.RustFSConfig.fromDict(data['rustFS']),
            cors    = ConfigObject.CorsConfig.fromDict(data['cors']),
            networkDomain = ConfigObject.NetworkDomainConfig.fromDict(data['NetworkDomain'])
        )


def loadConfig() -> ConfigObject:
    '''
    读取配置文件中的内容并返回对应的表示对象
    ~~~
    默认路径为：server/config/serviceConfig.json
    '''
    with open('.\\config\\serviceConfig.json', 'r', encoding='utf-8') as f:
        raw = json.load(f)
    return ConfigObject.fromDict(raw)


def generateIdentificationAccountCode() -> str:
    '''
    生成随时间变化的账户唯一标识码
    ~~~
    直接返回字符串形式的标识码，长度固定为 30 位（大小写字母和数字）
    '''
    uuidBytes   : bytes = uuid.uuid7().bytes
    dataInt     : int   = int.from_bytes(uuidBytes, 'big')
    charset     : str   = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    if dataInt == 0:
        encodedStr: str = charset[0]
    else:
        chars: list[str] = []
        while dataInt > 0:
            dataInt, remainder = divmod(dataInt, 62)
            chars.append(charset[remainder])
        encodedStr = ''.join(reversed(chars))
    
    return f'dxj{encodedStr.zfill(27)}'


def generateIdentificationFileCode() -> str:
    '''
    生成随时间变化的文件唯一标识码
    ~~~
    直接返回字符串形式的标识码，长度固定为 30 位（大小写字母和数字）
    '''
    uuidBytes   : bytes = uuid.uuid7().bytes
    dataInt     : int   = int.from_bytes(uuidBytes, 'big')
    charset     : str   = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    if dataInt == 0:
        encodedStr: str = charset[0]
    else:
        chars: list[str] = []
        while dataInt > 0:
            dataInt, remainder = divmod(dataInt, 62)
            chars.append(charset[remainder])
        encodedStr = ''.join(reversed(chars))
    
    return f'dxj{encodedStr.zfill(27)}'


def generateIdentificationBucketCode() -> str:
    '''
    生成随时间变化的桶唯一标识码
    ~~~
    直接返回字符串形式的标识码，长度固定为 30 位（仅含数字、小写字母和连字符）
    '''
    uuidBytes: bytes = uuid.uuid7().bytes
    dataInt: int = int.from_bytes(uuidBytes, 'big')
    charset: str = '0123456789abcdefghijklmnopqrstuvwxyz-'

    if dataInt == 0:
        encodedStr: str = charset[0]
    else:
        chars: list[str] = []
        while dataInt > 0:
            dataInt, remainder = divmod(dataInt, 37)
            chars.append(charset[remainder])
        encodedStr = ''.join(reversed(chars))

    return f'dxj{encodedStr.zfill(27)}'


async def sendEmail(loginKey:str, sender:str, recipient:str, title:str, content:str) -> bool:
    '''
    发送邮件到指定的邮箱
    ~~~
    loginKey    : 邮箱登录密钥（与 sender 参数声明的发送方邮箱对应）
    sender      : 发送方邮箱
    recipient   : 接收方邮箱
    title       : 邮件标题
    content     : 邮件内容（html 格式）

    返回 True 表示发送成功，反之失败
    '''
    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = Header(title, 'utf-8') # type: ignore
    msg['From'] = sender
    msg['To'] = recipient

    try:
        smtp = aiosmtplib.SMTP(hostname='smtp.qq.com', port=587)
        await smtp.connect()
        # await smtp.starttls() # qq 邮箱奇怪的逻辑，587 默认会启用 tls
        await smtp.login(sender, loginKey)
        await smtp.sendmail(sender, recipient, msg.as_string())
        await smtp.quit()
        return True
    except Exception as e:
        print(e)
        return False















'''
import asyncio
async def run():
    print(await sendEmail('gdjooagbizpxcjaj', '3625115644@qq.com', '3068405251@qq.com', '测试邮件', '测试邮件'))
asyncio.run(run())
'''




