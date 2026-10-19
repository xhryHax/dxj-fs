### BaseURL 范式：
	域名/api版本/服务名/接口名/...
	预期规划为：
		http://xyhraics.top/v1/account-service/{interface}
		http://xyhraics.top/v1/file-logic-service/{interface}
		http://xyhraics.top/v1/file-io-service/{interface}
		http://xyhraics.top/v1/system-service/{interface}

---
### 接口内容范式 
- RESTful 风格
- 字符集为：‘UTF-8’
- 时间格式：‘UTC时区’如‘（2026-08-18T07:30:00Z）’
- 布尔值：'true' 或 'false'
- 幂等性：是
- 请求
	- URL 资源命名为名词加复数，用请求方法表示动词
	- 请求参数：
		- GET/DELETE 使用查询参数
		- POST/PUT/PATCH 使用 Request Body 的 json 格式
	- 请求头：
		- Content-Type 必须为 application/json （文件数据传输例外）
		- 使用 HttpOnly Cookie 携带 Token ，故不得在 Header 中使用 Authorization 字段
- 响应
	- HTTP 响应状态码必须为 200 （重定向除外）
	- 响应的数据体必须为 json ，结构如下：
		```json
{
	"code" : 0,
	"msg" : "人类可读的错误信息（不得包含敏感信息）",
	"content" : any
}
		```
	- 响应数据体中的 code 字段的值：
		- 0 表示请求成功，否则都为请求异常
		- 1xxx 表示参数类错误
			- 1001 实际的参数与预期的参数映射不符，如字段不对应、字段过多、字段过少
			- 1002 参数值范围不正确
			- 1003 参数类型不正确
		- 2xxx 表示权限类错误
			- 2001 表示未登录
			- 2002 表示当前用户不具备足够的权限，可能不是系统管理员、组管理员，或跨组操作
			- 2003 
		- 3xxx 表示请求对应的操作在业务层面产生错误
			- 3001 注册账户所使用的邮箱已有对应的账户
			- 3002 登录账户时校验错误
			- 3003 修改账户名时产生错误，可能时账户不存在、账户名不合法
			- 3004 修改账户密码时产生错误，可能时账户不存在、账户密码不合法
			- 3005 发起组加入请求时产生错误，对应的组不存在
			- 3006 没有对应的加入组的请求
			- 3007 请求中的组和实际所在的组不符
			- 3008 请求的范围超出实际的范围
			- 3009 所请求的指定页不存在
			- 3010 尝试操作的文件不存在
			- 3011 文件名不合法
			- 3012 文件标签不合法
			- 3013 尝试操作的文件不存在于回收站中
			- 3014 不接受此文件，可能是过大、或服务端不足以容纳
			- 3015 此文件已在组中，文件名冲突
			- 3016 上传文件时，分片标头异常
			- 3017 上传文件时，此片段已完成，但任收到了上传请求
			- 3018 上传文件时，微服务在合并文件并传输到 RustFS 时合并异常
			- 3019 没有对应的上传记录，无法完成上传
			- 3020 网络域不合法
			- 3021 对应的账户不存在
			- 3022 对应的页（公开页、指定页）不存在
			- 3023 归属检查不通过
		- 4xxx 表示请求对应的操作在代码层面产生错误
			- ...
		- 5xxx 表示已被风控
			- ...

---
### 用户识别
	用户标识使用 HttpOnly Cookie 方案
	服务端必须配置 Access-Control-Allow-Credentials: true ，且 Origin 不能为 * 

---
### API 详细
- #### account-service 类
	- ##### 用户板块 account
		1. 注册并登录账户
			- head:
				```HTTP
				POST BaseURL/accounts
				```
			- body (Content-Type: application/json):
				```json
				{
					"email" : "...",
					"password" : "password",
					"userName" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 3001,
					"msg" : "注册成功" | "已有对应的账户",
					"content" : {
						"userId" : "...",
						"userName" : "...",
						"email" : "...",
						"groupId" : "..."
					} | null
				}
				```
			- 注：会设置 Cookie
		2. 登录账户
			- head:
				```HTTP
				POST BaseURL/sessions
				```
			- body (Content-Type: application/json):
				```json
				{
					"email" : "...",
					"password" : "password"
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 3002,
					"msg" : "登录成功" | "登录失败",
					"content" : {
						"userId" : "...",
						"userName" : "...",
						"email" : "...",
						"groupId" : "..."
					} | null
				}
				```
			- 注：会设置 Cookie
		3. 修改账户名
			- head:
				```HTTP
				PATCH BaseURL/accounts/me/name
				```
			- body (Content-Type: application/json):
				```json
				{
					"userName" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 3003,
					"msg" : "修改成功" | "未登录" | "修改失败",
					"content" : {
						"userId" : "...",
						"userName" : "...",
						"email" : "..."
					} | null
				}
				```
			- 注：无
		4. 修改账户密码
			- head:
				```HTTP
				PATCH BaseURL/accounts/me/password
				```
			- body (Content-Type: application/json):
				```json
				{
					"oldPassword" : "...",
					"newPassword" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 3004,
					"msg" : "修改成功" | "未登录" | "修改失败",
					"content" : {
						"userId" : "...",
						"userName" : "...",
						"email" : "..."
					} | null
				}
				```
			- 注：会设置新的 Cookie
		5. 获取是否为组管理员
			- head:
				```HTTP
				GET BaseURL/accounts/me/admin
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 3004,
					"msg" : "获取成功" | "未登录" | "获取失败",
					"content" : bool | null
				}
				```
			- 注：无
	- ##### 组板块
		1. 获取本组中所有成员的信息
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/members
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "未登录" | "不具备获取权限",
					"content" : [
						{ "userId" : "...", "userName" : "...", "email" : "..." }
					] | null
				}
				```
			- 注：获取用户所在组的所有成员的信息
		2. 获取所有的组信息
			- head:
				```HTTP
				GET BaseURL/groups
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "获取失败",
					"content" : [
						{"groupId" : "...", "groupName" : "..."},
						...
					] | null
				}
				```
			- 注：无
		3. 发起加入组的请求
			- head:
				```HTTP
				POST BaseURL/groups/{groupId}/join-requests
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 3005,
					"msg" : "发起加入请求成功" | "未登录" | "对应的组不存在",
					"content" : null
				}
				```
			- 注：加入的请求不可被查询，故不需要返回任何数据
		4. 获取加入组请求
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/join-requests
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "未登录",
					"content" : [
						{"userId" : "...", "email" : "...", "userName" : "..."},
						...
					] | null
				}
				```
			- 注：按照系统设计期望，实际记录不会超过千数，故不做分页处理
		5. 审批加入组请求
			- head:
				```HTTP
				PATCH BaseURL/groups/{groupId}/join-requests/{userId}
				```
			- body (Content-Type: application/json):
				```json
				{
					"status": "APPROVED" | "REJECTED"
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3006 |,
					"msg" : "加入请求已批准" | "加入请求已拒绝" | "未登录",
					        "不具备此权限" | "申请已失效"
					"content" : null
				}
				```
			- 注：无
		6. 退出所在的组
			- head:
				```HTTP
				DELETE BaseURL/groups/{groupId}/members/me
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 3007,
					"msg" : "已退出组" | "未登录" | "实际所在的组与请求的组不符",
					"content" : null
				}
				```
			- 注：无
- #### file-logic-service 类
	- ##### 获取信息类
		1. 获取当前所在组下的对应范围的文件信息
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/files?page={窗口位置}&size={窗口大小}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3008,
					"msg" : "获取成功" | "未登录" | "不具备获取权限" | "超出实际可用的范围",
					"content" : {
						"total" : 总记录数,
						"page" : 当前的窗口位置,
						"info" : [
							{"fileId" : "...", "label" : "...", "fileame" : "...",
							"atCreated" : "...", "size" : ..., "uploader" : "..."},
							...
						]
					} | null
				}
				```
			- 注：index 表示当前窗口的位置
		2. 获取指定组的公开页下的对应范围的文件信息
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/public-pages/files?page={窗口位置}&size={窗口大小}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3008,
					"msg" : "获取成功" | "未登录" | "不具备获取权限" | "超出实际可用的范围",
					"content" : {
						"total" : 总记录数,
						"page" : 当前的窗口位置,
						"info" : [
							{"fileId" : "...", "label" : "...", "fileName" : "...",
							"atCreated" : "...", "size" : ..., "uploader" : "..."},
							...
						]
					} | null
				}
				```
			- 注：index 表示当前窗口的位置
		3. 获取对应的指定页下的对应范围的文件信息
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/specific-pages/{specificPagesId}/files?page={窗口位置}&size={窗口大小}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3008 | 3009,
					"msg" : "获取成功" | "未登录" | "不具备获取权限" | "超出实际可用的范围" |
					        "不存在对应的页面",
					"content" : {
						"total" : 总记录数,
						"page" : 当前的窗口位置,
						"info" : [
							{"fileId" : "...", "label" : "...", "fileName" : "...",
							"atCreated" : "...", "size" : ..., "uploader" : "..."},
							...
						]
					} | null
				}
				```
			- 注：index 表示当前窗口的位置
		4. 获取当前所在组下的已软删除的对应范围的文件信息
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/deleted/files?page={窗口位置}&size={窗口大小}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3008,
					"msg" : "获取成功" | "未登录" | "不具备获取权限" | "超出实际可用的范围",
					"content" : {
						"total" : 总记录数,
						"page" : 当前的窗口位置,
						"info" : [
							{"fileId" : "...", "label" : "...", "fileName" : "...",
							"atCreated" : "...", "size" : ..., "uploader" : "...",
							"atDeleted" : "..."},
							...
						]
					} | null
				}
				```
			- 注：index 表示当前窗口的位置
		5. 获取当前组的存储使用情况
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/storage-quota
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "获取失败",
					"content" : {
						"groupId" : "...", "groupName" : "...",
						"size" : 组的总可用字节数, "occupied" : 组的总已用字节数
					} | null
				}
				```
			- 注：size 字段的值为 -1 表示未做限制
	- ##### 文件操作类
		1. 文件更名
			- head:
				```HTTP
				PATCH BaseURL/groups/{groupId}/files/{fileId}/name
				```
			- body (Content-Type: application/json):
				```json
				{
					"fileName" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010 | 3011,
					"msg" : "文件更名成功" | "未登录" | "无权限进行操作" |
					        "不存在此文件" | "文件名不合法",
					"content" : {
						"fileId" : "...", "label" : "...", "fileName" : "...",
						"atCreated" : "...", "size" : ..., "uploader" : "..."
					} | null
				}
				```
			- 注：无
		2. 文件标签修改
			- head:
				```HTTP
				PATCH BaseURL/groups/{groupId}/files/{fileId}/label
				```
			- body (Content-Type: application/json):
				```json
				{
					"label" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010 | 3012,
					"msg" : "文件标签修改成功" | "未登录" | "无权限进行操作" |
					        "不存在此文件" | "标签不合法",
					"content" : {
						"fileId" : "...", "label" : "...", "fileName" : "...",
						"atCreated" : "...", "size" : ..., "uploader" : "..."
					} | null
				}
				```
			- 注：无
		3. 软删除文件
			- head:
				```HTTP
				DELETE BaseURL/groups/{groupId}/files/{fileId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010,
					"msg" : "文件软删除成功" | "未登录" | "无权限进行操作" |
					        "不存在此文件",
					"content" : null
				}
				```
			- 注：无
		4. 恢复已软删除文件
			- head:
				```HTTP
				POST BaseURL/groups/{groupId}/files/{fileId}/restore
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010,
					"msg" : "文件恢复成功" | "未登录" | "无权限进行操作" |
					        "不存在此文件",
					"content" : null
				}
				```
			- 注：无
		5. 实删除文件
			- head:
				```HTTP
				DELETE BaseURL/groups/{groupId}/deleted/files/{fileId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3013,
					"msg" : "文件已被删除成功" | "未登录" | "无权限进行操作" |
					        "文件未处于软删除状态",
					"content" : null
				}
				```
			- 注：无
	- ##### 页类
		1. 获取全局的公开页
			- head:
				```HTTP
				GET BaseURL/arbitrary-groups/public-pages
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "未登录",
					"content" : [
						{
						"groupId" : "...", "groupName" : "...", "publicPageId" : "...",
						"announcement" : "..."
						}
					] | null
				}
				```
			- 注：无
		2. 获取可见的指定页
			- head:
				```HTTP
				GET BaseURL/accounts/me/visible-pages
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "未登录",
					"content" : [
						{
						"groupId" : "...", "groupName" : "...", "specificPageId" : "...",
						"announcement" : "..."
						}
					] | null
				}
				```
			- 注：获取此用户可见的所有指定页
		3. 获取当前所在组的所有指定页信息
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/specific-pages
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "未登录" | "无权限获取",
					"content" : [
						{
						"specificPageId" : "...", "visibleGroups" : ["groupId", ...],
						"announcement" : "..."
						}
					] | null
				}
				```
			- 注：无
		4. 创建指定页
			- head:
				```HTTP
				POST BaseURL/groups/{groupId}/specific-pages
				```
			- body (Content-Type: application/json):
				```json
				{
					"announcement" : "...",
					"visibleGroups" : ["groupId", ...]
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "创建成功" | "未登录" | "无权限创建",
					"content" : {
						"specificPageId" : "...", "visibleGroups" : ["groupId", ...],
						"announcement" : "..."
					} | null
				}
				```
			- 注：无
		5. 删除指定页
			- head:
				```HTTP
				DELETE BaseURL/groups/{groupId}/specific-pages/{specificPageId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "删除成功" | "未登录" | "无权限删除",
					"content" : null
				}
				```
			- 注：无
		6. 修改公开页的公告
			- head:
				```HTTP
				PATCH BaseURL/groups/{groupId}/public-pages/{publicPageId}
				```
			- body (Content-Type: application/json):
				```json
				{
					"announcement" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3022 | 3023,
					"msg" : "修改成功" | "未登录" | "无权限修改" |
					        "此页面已不存在" | "归属检查失败",
					"content" : {
						"publicPageId" : "...",
						"announcement" : "..."
					} | null
				}
				```
			- 注：无
		7. 修改指定页的公告
			- head:
				```HTTP
				PATCH BaseURL/groups/{groupId}/specific-pages/{specificPageId}
				```
			- body (Content-Type: application/json):
				```json
				{
					"announcement" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3022,
					"msg" : "修改成功" | "未登录" | "无权限修改" | "此页面已不存在",
					"content" : {
						"specificPageId" : "...", "visibleGroups" : ["groupId", ...],
						"announcement" : "..."
					} | null
				}
				```
			- 注：无
		8. 修改指定页的可见组
			- head:
				```HTTP
				PATCH BaseURL/groups/{groupId}/specific-pages/{specificPageId}
				```
			- body (Content-Type: application/json):
				```json
				{
					"visibleGroups" : ["groupId", ...]
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3022,
					"msg" : "修改成功" | "未登录" | "无权限修改" | "此页面已不存在",
					"content" : {
						"specificPageId" : "...", "visibleGroups" : ["groupId", ...],
						"announcement" : "..."
					} | null
				}
				```
			- 注：无
	- ##### 页文件操作
		1. 将指定的文件添加到公开页中
			- head:
				```HTTP
				POST BaseURL/groups/{groupId}/public-pages/files
				```
			- body (Content-Type: application/json):
				```json
				{
					"fileId" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010,
					"msg" : "文件添加成功" | "未登录" | "无权限进行操作" |
					        "文件已被删除",
					"content" : null
				}
				```
			- 注：无
		2. 将指定的文件从公开页中移除
			- head:
				```HTTP
				DELETE BaseURL/groups/{groupId}/public-pages/files/{fileId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "文件已被从页面中移除" | "未登录" | "无权限进行操作",
					"content" : null
				}
				```
			- 注：无
		3. 将指定的文件添加到指定页中
			- head:
				```HTTP
				POST BaseURL/groups/{groupId}/specific-pages/{specificPagesId}/files
				```
			- body (Content-Type: application/json):
				```json
				{
					"fileId" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3009 | 3010,
					"msg" : "文件添加成功" | "未登录" | "无权限进行操作" |
					        "对应的指定页不存在" | "文件已被删除",
					"content" : null
				}
				```
			- 注：无
		4. 将指定的文件从指定页中移除
			- head:
				```HTTP
				DELETE BaseURL/groups/{groupId}/specific-pages/{specificPagesId}/files/{fileId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "文件已被从页面中移除" | "未登录" | "无权限进行操作",
					"content" : null
				}
				```
			- 注：无
- #### file-io-service 类
	- ##### 文件上下载
		1. 获取已有的上传进度
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/files/upload-info
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "未登录" | "无权限进行操作",
					"content" : [
						{ "uploadInfoId" : "...", 
						  "size" : 实际文件总字节数, "progress" : 已收到的字节数
						},
						...
					] | null
				}
				```
			- 注：无
		2. 删除上传记录
			- head:
				```HTTP
				DELETE BaseURL/groups/{groupId}/files/upload-info/{uploadInfoId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "删除成功" | "未登录" | "无权限进行操作",
					"content" : null
				}
				```
			- 注：无
		3. 就绪文件上传环境
			- head:
				```HTTP
				POST BaseURL/groups/{groupId}/files/upload-info
				```
			- body (Content-Type: application/json):
				```json
				{
					"size" : 实际文件总字节数,
					"fileName" : "文件名",
					"label" : "标签内容文本"
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3014 | 3015,
					"msg" : "就绪成功" | "未登录" | "无权限进行操作" |
					        "服务端无法处理此文件" | "文件已在组中",
					"content" : {
						"uploadInfoId" : "...",
						"size" : 实际文件总字节数,
						"fileName" : "文件名",
						"label" : "标签内容文本",
						"progress" : 0
					} | null
				}
				```
			- 注：无
		4. 上传文件数据
			- head:
				```HTTP
				PUT BaseURL/groups/{groupId}/files/upload-info/{uploadInfoId}/data
				```
			- body (Content-Type: application/octet-stream):
				实际的文件二进制数据
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010 | 3016 | 3017,
					"msg" : "数据上传成功" | "未登录" | "无权限进行操作" |
					        "不存在此文件" | "分片范围不合法" | "已完成上传，无需再传",
					"content" : {
						"size" : 实际文件总字节数, 
						"progress" : 已收到的字节数
					} | null
				}
				```
			- 注：请求必须携带标头 Content-Range 以声明当前上传的文件数据的片段位置
		5. 完成文件上传
			- head:
				```HTTP
				POST BaseURL/groups/{groupId}/files/upload-info/{uploadInfoId}/complete
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010 | 3017 | 3018,
					"msg" : "文件上传完成" | "未登录" | "上传记录不存在" |
					        "上传未完成" | "服务端的文件分片异常",
					"content" :  {
						"fileId" : "...", "label" : "...", "fileName" : "...",
						"atCreated" : "...", "size" : ..., "uploader" : "..."
					}| null
				}
				```
			- 注：将同步文件元数据、文件到全局，此服务不再维护对应的信息
		6. 获取下载文件链接
			- head:
				```HTTP
				GET BaseURL/groups/{groupId}/files/{fileId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3010,
					"msg" : "未登录" | "无权限进行操作" | "对应的文件不存在",
					"content" : {
						"fileURL" : "...",
						"fileName" : "..."
					}
				}
				```
			- 注：返回实际的下载链接和文件名，由客户端收到响应后手动进行实际的文件下载操作
- #### system-service 类
	- ##### 系统状态类
		1. 获取当前活跃的用户信息
			- head:
				```HTTP
				GET BaseURL/system/users/online
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "未登录" | "无权限进行操作",
					"content" : [
						{
							"userId" : "...", "email" : "...", "userName" : "...",
							 "groupId" : "...", "groupName" : "..."
						},
						...
					] | null
				}
				```
			- 注：已登录的用户，即服务端存在对应的 Sessions ，系统预期设计在线用户不超过 1 千，故不做分页处理
		2. 获取存储系统使用情况
			- head:
				```HTTP
				GET BaseURL/system/storage/info
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "未登录" | "无权限进行操作",
					"content" : {
						"size" : 可用的总字节数,
						"occupied" : 已用字节数,
						"groupInfo" : [
							{
								"groupId" : "...", "groupName" : "...",
								"size" : 组的总可用字节数, "occupied" : 组的总已用字节数
							},
							...
						]
					} | null
				}
				```
			- 注：groupInfo 字段中， size 字段的值为 -1 表示不做限制
	- ##### 可访问域类
		1. 获取当前可访问域
			- head:
				```HTTP
				GET BaseURL/system/network/accessible
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "未登录" | "无权限进行操作",
					"content" : [
						"...",
						...
					] | null
				}
				```
			- 注：无
		2. 添加可访问域
			- head:
				```HTTP
				POST BaseURL/system/network/accessible
				```
			- body (Content-Type: application/json):
				```json
				{
					"value" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3020,
					"msg" : "添加成功" | "未登录" | "无权限进行操作" | "网络域不合法",
					"content" : [
						"...",
						...
					] | null
				}
				```
			- 注：无
		3. 删除可访问域
			- head:
				```HTTP
				DELETE BaseURL/system/network/accessible?value="..."
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "删除成功" | "未登录" | "无权限进行操作",
					"content" : [
						"...",
						...
					] | null
				}
				```
			- 注：无
	- ##### 组类
		1. 获取所有的组的信息和对应的成员信息
			- head:
				```HTTP
				GET BaseURL/system/groups
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "获取失败" | "无权限进行操作",
					"content" : [
						{
							"groupId" : "...", "groupName" : "...",
							"members" : [
								{
									"userId" : "...", "userName" : "...", "email" : "...",
									"isAdmin" : bool
								},
								...
							]
						},
						...
					] | null
				}
				```
			- 注：isAdmin 字段为 true 表示为组管理员
		2. 获取所有组的存储空间配额信息
			- head:
				```HTTP
				GET BaseURL/system/groups/storage-quota
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "获取失败",
					"content" : [
						{
							"groupId" : "...", "groupName" : "...",
							"size" : 组的总可用字节数, "occupied" : 组的总已用字节数
						},
						...
					] | null
				}
				```
			- 注：size 字段的值为 -1 表示不做限制
		3. 对指定组进行存储空间配额
			- head:
				```HTTP
				PATCH BaseURL/system/groups/{groupId}/storage-quota
				```
			- body (Content-Type: application/json):
				```json
					{
						"groupId" : "...",
						"size" : 组的总可用字节数
					}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "获取失败",
					"content" :  {
							"groupId" : "...", "groupName" : "...",
							"size" : 组的总可用字节数, "occupied" : 组的总已用字节数
					} | null
				}
				```
			- 注：size 字段的值为 -1 表示不做限制
		4. 获取组中的成员信息
			- head:
				```HTTP
				GET BaseURL/system/groups/{groupId}/members
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "获取成功" | "未登录" | "不具备获取权限",
					"content" : [
						{ "userId" : "...", "userName" : "...", "email" : "..." }
					] | null
				}
				```
			- 注：无
		5. 将指定成员任命为组管理员
			- head:
				```HTTP
				PUT BaseURL/system/groups/{groupId}/administrator?userId="..."
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3021,
					"msg" : "任命成功" | "未登录" | "不具备操作权限" | "对应的账户不存在",
					"content" : null
				}
				```
			- 注：无
		6. 将指定成员免除组管理员
			- head:
				```HTTP
				DELETE BaseURL/system/groups/{groupId}/administrator?userId="..."
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "免除成功" | "未登录" | "不具备操作权限",
					"content" : null
				}
				```
			- 注：无
		7. 创建组
			- head:
				```HTTP
				POST BaseURL/system/groups
				```
			- body (Content-Type: application/json):
				```json
				{
					"groupName" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "创建成功" | "未登录" | "不具备操作权限",
					"content" : {
						"groupId" : "...",
						"groupName" : "..."
					} | null
				}
				```
			- 注：无
		8. 删除组
			- head:
				```HTTP
				DELETE BaseURL/system/groups/{groupId}
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "删除成功" | "未登录" | "不具备操作权限",
					"content" : null
				}
				```
			- 注：无
		9. 修改组名
			- head:
				```HTTP
				PATCH BaseURL/system/groups/{groupId}
				```
			- body (Content-Type: application/json):
				```json
				{
					"groupName" : "..."
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002,
					"msg" : "修改成功" | "未登录" | "不具备操作权限",
					"content" : null
				}
				```
			- 注：无
		10. 获取加入组请求
			- head:
				```HTTP
				GET BaseURL/system/groups/{groupId}/join-requests
				```
			- body (Content-Type: application/json):
				无
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001,
					"msg" : "获取成功" | "未登录",
					"content" : [
						{"userId" : "...", "email" : "...", "userName" : "..."},
						...
					] | null
				}
				```
			- 注：按照系统设计期望，实际记录不会超过千数，故不做分页处理
		11. 审批加入组请求
			- head:
				```HTTP
				PATCH BaseURL/system/groups/{groupId}/join-requests/{userId}
				```
			- body (Content-Type: application/json):
				```json
				{
					"status": "APPROVED" | "REJECTED"
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 2001 | 2002 | 3006 |,
					"msg" : "加入请求已批准" | "加入请求已拒绝" | "未登录",
					        "不具备此权限" | "申请已失效"
					"content" : null
				}
				```
			- 注：无
	- 管理员登录类 
		1. 登录账户
			- head:
				```HTTP
				POST BaseURL/sessions
				```
			- body (Content-Type: application/json):
				```json
				{
					"id" : "...",
					"password" : "password"
				}
				```
			- response body (Content-Type: application/json):
				```json
				{
					"code" : 0 | 3002,
					"msg" : "登录成功" | "登录失败",
					"content" : {
						"userId" : "...",
						"userName" : "...",
						"email" : "...",
						"groupId" : "..."
					} | null
				}
				```
			- 注：会设置 Cookie



















