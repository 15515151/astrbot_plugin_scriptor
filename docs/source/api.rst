API Documentation
=====================

Web API
-------

.. toctree::
   :maxdepth: 2

Scriptor 提供 RESTful API 用于与外部系统集成。

认证
~~~~

API 密钥认证
^^^^^^^^^^^^

所有 API 端点都需要通过 `X-API-Key` 请求头进行认证：

.. code-block:: bash

    curl -H "X-API-Key: your_api_key" https://your-server/api/status

CSRF 保护
^^^^^^^^^^

对于修改操作 (POST, PUT, DELETE)，需要额外的 CSRF 保护：

.. code-block:: bash

    # 1. 获取 CSRF Token
    curl -H "X-API-Key: your_api_key" https://your-server/api/csrf/token

    # 2. 使用 Token
    curl -X POST \
      -H "X-API-Key: your_api_key" \
      -H "X-CSRF-Token: your_csrf_token" \
      -H "Content-Type: application/json" \
      -d '{"title": "New Knowledge", "content": "..."}' \
      https://your-server/api/knowledge

速率限制
~~~~~~~~

- 重新索引: 5次/分钟
- 导出: 10次/分钟
- 性能统计: 30次/分钟

状态端点
--------

GET /api/status
~~~~~~~~~~~~~~~

获取系统运行状态

.. code-block:: json

    {
        "status": "running",
        "initialized": true,
        "data_dir": "/path/to/data",
        "profiles_count": 10,
        "groups_count": 5,
        "total_memory_files": 100,
        "timestamp": "2026-03-18T12:00:00"
    }

用户端点
--------

GET /api/profiles
~~~~~~~~~~~~~~~~~

获取所有用户画像列表

**响应:**

.. code-block:: json

    [
        {"uid": "user1", "name": "张三"},
        {"uid": "user2", "name": "李四"}
    ]

GET /api/profiles/{uid}
~~~~~~~~~~~~~~~~~~~~~~~

获取指定用户的详细信息

**响应:**

.. code-block:: json

    {
        "uid": "user1",
        "files": {
            "PROFILE.md": "# 用户资料\n...",
            "MEMORY.md": "### [2026-01-01] (fact) ...",
            "SOUL.md": "..."
        }
    }

群体端点
--------

GET /api/groups
~~~~~~~~~~~~~~~~

获取所有群体列表

**响应:**

.. code-block:: json

    [
        {"group_id": "group1", "name": "家庭群"},
        {"group_id": "group2", "name": "工作群"}
    ]

知识库端点
----------

GET /api/knowledge
~~~~~~~~~~~~~~~~~~

获取知识库所有条目

**响应:**

.. code-block:: json

    [
        {
            "id": "kb_001",
            "title": "重要日期",
            "content": "用户的生日是...",
            "knowledge_type": "fact",
            "tags": ["重要", "日期"],
            "category": "个人信息",
            "is_active": true,
            "useful_count": 5,
            "useful_score": 8.5
        }
    ]

POST /api/knowledge
~~~~~~~~~~~~~~~~~~~

创建新的知识库条目

**请求体:**

.. code-block:: json

    {
        "title": "新知识",
        "content": "知识内容...",
        "knowledge_type": "fact",
        "tags": ["标签1", "标签2"],
        "category": "分类",
        "is_active": true
    }

DELETE /api/knowledge/{item_id}
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

删除知识库条目

维护端点
--------

POST /api/maintenance/reindex
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

手动触发重新索引

**需要权限:** Admin

导出端点
--------

POST /api/export
~~~~~~~~~~~~~~~

导出系统数据

**请求体:**

.. code-block:: json

    {
        "type": "all",
        "format": "json"
    }

配置端点
--------

GET /api/config
~~~~~~~~~~~~~~~

获取当前配置（敏感信息已脱敏）

错误响应
--------

所有错误响应都遵循以下格式：

.. code-block:: json

    {
        "detail": "错误描述信息"
    }

常见错误码：

- 400: 请求参数错误
- 401: 缺少 API Key
- 403: API Key 无效或权限不足
- 404: 资源不存在
- 413: 请求体过大
- 429: 请求过于频繁
- 500: 服务器内部错误
