
from typing import Any, TypeVar
from datetime import datetime
from sqlmodel import SQLModel, Field, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker



class accountModel(SQLModel, table=True):
    __tablename__       : str               = 'account' # type: ignore
    accountId           : str               = Field(primary_key=True, max_length=30)
    email               : str               = Field(max_length=255, unique=True)
    pw                  : str               = Field(max_length=255)
    name                : str               = Field(max_length=255)
    atCreated           : datetime
    admin               : int               = Field(default=0)
    beInGroupId         : str | None        = Field(default=None, foreign_key='groups.groupId')
    applicationGroupId  : str | None        = Field(default=None, foreign_key='groups.groupId')


class fileModel(SQLModel, table=True):
    __tablename__       : str               = 'files' # type: ignore
    fileId              : str               = Field(primary_key=True, max_length=30)
    name                : str               = Field(max_length=255)
    label               : str               = Field(max_length=255)
    atDeleted           : datetime | None   = Field(default=None)
    groupId             : str | None        = Field(default=None, foreign_key='groups.groupId')
    atCreated           : datetime
    size                : int
    uploader            : str | None        = Field(default=None, foreign_key='account.accountId')


class groupModel(SQLModel, table=True):
    __tablename__       : str               = 'groups' # type: ignore
    groupId             : str               = Field(primary_key=True, max_length=30)
    name                : str               = Field(max_length=255)
    storageFieldKey     : str               = Field(max_length=30)
    publicPageId        : str               = Field(max_length=30, unique=True)
    publicPageAnnouncement : str            = Field(max_length=255)


class groupAndSpecificModel(SQLModel, table=True):
    __tablename__       : str               = 'groupAndSpecific' # type: ignore
    specificPageId      : str               = Field(primary_key=True, foreign_key='specificPage.specificPageId')
    provideToGroupId    : str               = Field(primary_key=True, foreign_key='groups.groupId')


class publicPageAndFileModel(SQLModel, table=True):
    __tablename__       : str               = 'publicPageAndFile' # type: ignore
    publicPageId        : str               = Field(primary_key=True, foreign_key='groups.publicPageId')
    fileId              : str               = Field(primary_key=True, foreign_key='files.fileId')


class specificPageModel(SQLModel, table=True):
    __tablename__       : str               = 'specificPage' # type: ignore
    specificPageId      : str               = Field(primary_key=True, max_length=30)
    ownerGroupId        : str               = Field(foreign_key='groups.groupId')
    announcement        : str               = Field(max_length=255)


class specificPageAndFileModel(SQLModel, table=True):
    __tablename__       : str               = 'specificPageAndFile' # type: ignore
    specificPageId      : str               = Field(primary_key=True, foreign_key='specificPage.specificPageId')
    fileId              : str               = Field(primary_key=True, foreign_key='files.fileId')


class sysAccountModel(SQLModel, table=True):
    __tablename__       : str               = 'sysAccount' # type: ignore
    id                  : str               = Field(primary_key=True, max_length=30)
    pw                  : str               = Field(max_length=255)



T = TypeVar('T', bound=SQLModel)



class MySqlInteraction:
    '''
    MySQL 异步交互类，封装连接初始化、销毁
    ~~~
    仅提供基础操作能力，生命周期管理由上层调用对应方法（__init__ 为实例， close 为销毁）
    '''

    def __init__(self, mysqlUser:str, mysqlPassword:str, mysqlHost:str, mysqlPort:int, database:str) -> None:
        self.databaseUrl        = (f'mysql+aiomysql://{mysqlUser}:{mysqlPassword}@{mysqlHost}:{mysqlPort}/{database}')
        self.engine             = create_async_engine(self.databaseUrl, echo=False)
        self.asyncSessionMaker  = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)


    async def initDb(self) -> None:
        '''
        初始化数据库表结构

        如果表尚不存在，则根据已定义的 SQLModel 元数据自动创建所有表
        该方法应在应用启动时调用，且仅执行一次

        Raises:
            SQLAlchemyError: 数据库连接或表创建失败时抛出
        '''
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)


    async def close(self) -> None:
        '''
        释放数据库引擎及所有活动连接
    
        关闭引擎并清理连接池，通常在应用关闭或注销时调用
        调用后所有数据库操作将不可用
        
        Raises:
            SQLAlchemyError: 释放资源过程中发生错误时抛出
        '''
        await self.engine.dispose()


    async def createRecord(self, record:T, session_:AsyncSession|None=None) -> T:
        '''
        插入一条新记录到数据库，并返回刷新后的对象

        Args:
            record      : 要插入的模型实例（SQLModel 对象）
            session_    : 可选的外部数据库会话若提供，则使用该会话操作，否则自动创建临时会话

        Returns:
            刷新后的记录对象，包含数据库生成的字段（如自增主键、默认值等）
        
        Raises:
            SQLAlchemyError: 插入或刷新操作失败时抛出
        '''
        if session_ is None:
            async with self.asyncSessionMaker() as session:
                session.add(record)
                await session.commit()
                await session.refresh(record)
                return record
        else:
            session_.add(record)
            await session_.commit()
            await session_.refresh(record)
            return record


    async def getRecord(self, model:type[T], session_:AsyncSession|None=None, **pkValues:Any) -> T | None:
        '''
        根据主键查询单条记录，支持复合主键

        Args:
            model: 要查询的模型类（如 `User`）
            session_: 可选的外部数据库会话若提供，则使用该会话操作；
                    否则自动创建临时会话
            **pkValues: 主键字段名与值的键值对
                        对于单主键，例如 `id=1`；
                        对于复合主键，例如 `user_id=1, group_id=2`

        Returns:
            若找到记录则返回该模型实例，否则返回 `None`
        '''
        statement = select(model)
        for key, value in pkValues.items():
            statement = statement.where(getattr(model, key) == value)
        
        if session_ is None:
            async with self.asyncSessionMaker() as session:
                result = await session.execute(statement)
                return result.scalar_one_or_none()
        else:
            result = await session_.execute(statement)
            return result.scalar_one_or_none()


    async def updateRecord(self,model:type[T], updateData:dict[str, Any], session_:AsyncSession|None=None, **pkValues:Any) -> T | None:
        '''
        根据主键更新记录，并返回更新后的对象

        Args:
            model: 要更新的模型类
            updateData: 需要更新的字段及其新值字典，如 `{"name": "新名", "age": 30}`
            session_: 可选的外部数据库会话若提供，则使用该会话操作；
                    否则自动创建临时会话
            **pkValues: 主键字段名与值的键值对，用于定位要更新的记录

        Returns:
            更新成功时返回刷新后的模型实例；
            若未找到对应主键的记录，则返回 `None`

        Raises:
            SQLAlchemyError: 更新或刷新操作失败时抛出
        '''
        if session_ is None:
            async with self.asyncSessionMaker() as session:
                record = await self.getRecord(model, session, **pkValues)
                if record is None:
                    return None
                for key, value in updateData.items():
                    setattr(record, key, value)
                await session.commit()
                await session.refresh(record)
                return record
        else:
            record = await self.getRecord(model, session_, **pkValues)
            if record is None:
                return None
            for key, value in updateData.items():
                setattr(record, key, value)
            await session_.commit()
            await session_.refresh(record)
            return record


    async def deleteRecord(self, model:type[T], session_:AsyncSession|None=None, **pkValues:Any) -> bool:
        '''
        根据主键删除记录

        Args:
            model: 要删除的模型类
            session_: 可选的外部数据库会话若提供，则使用该会话操作；
                    否则自动创建临时会话
            **pkValues: 主键字段名与值的键值对，用于定位要删除的记录

        Returns:
            若记录存在且成功删除，返回 `True`；
            若未找到对应主键的记录，返回 `False`

        Raises:
            SQLAlchemyError: 删除操作失败时抛出
        '''
        if session_ is None:
            async with self.asyncSessionMaker() as session:
                record = await self.getRecord(model, session, **pkValues)
                if record is None:
                    return False
                await session.delete(record)
                await session.commit()
                return True
        else:
            record = await self.getRecord(model, session_, **pkValues)
            if record is None:
                return False
            await session_.delete(record)
            await session_.commit()
            return True


    async def listRecords(self, model:type[T], session_:AsyncSession|None=None, **filters:Any) -> list[T]:
        '''
        根据条件查询记录列表，不传条件时返回该模型的所有记录

        Args:
            model: 要查询的模型类
            session_: 可选的外部数据库会话若提供，则使用该会话操作；
                    否则自动创建临时会话
            **filters: 字段名与值的键值对，所有条件均为等值匹配（`==`）
                        例如 `name="张三", age=25` 将筛选出同时满足这两个条件的记录
                        若不提供任何过滤条件，则返回全部记录

        Returns:
            满足条件的模型实例列表，若无匹配结果则返回空列表
        '''
        statement = select(model)
        for key, value in filters.items():
            statement = statement.where(getattr(model, key) == value)
        if session_ is None:
            async with self.asyncSessionMaker() as session:
                result = await session.execute(statement)
                return list(result.scalars().all())
        else:
            result = await session_.execute(statement)
            return list(result.scalars().all())







# 使用示例
'''
async def exampleUsage() -> None:
    db: MySqlInteraction = MySqlInteraction('root', '123456', '192.168.178.10', 3306, 'fs')
    # 创建一个分组
    newGroup: groupModel = groupModel(
        groupId='grp_demo',
        name='演示分组',
        storageFieldKey='storage_key',
        publicPageId='pub_demo',
        publicPageAnnouncement='公告内容',
    )
    await db.createRecord(newGroup)

    # 查询
    fetched: groupModel | None = await db.getRecord(groupModel, groupId='grp_demo')
    print(fetched)

    # 更新
    updated: groupModel | None = await db.updateRecord(
        groupModel, {'publicPageAnnouncement': '新公告'}, groupId='grp_demo'
    )
    print(updated)

    # 删除
    deleted: bool = await db.deleteRecord(groupModel, groupId='grp_demo')
    print(deleted)

    await db.close()



if __name__ == '__main__':
    import asyncio
    asyncio.run(exampleUsage())
'''




