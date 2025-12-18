# 邮件回复链设计方案

## 1. 邮件头部信息

每封邮件包含以下关键头部：

```python
# 当前邮件的唯一标识
Message-ID: <abc123@qq.com>

# 这封邮件回复的邮件ID（如果是回复邮件）
In-Reply-To: <xyz789@qq.com>

# 完整的对话链（从最早到最近的所有 Message-ID）
References: <msg1@qq.com> <msg2@qq.com> <msg3@qq.com>
```

## 2. 回复链构建策略

### 方案 A: 基于 References（推荐）

**优点**：
- References 包含完整的对话历史
- 一次性获得所有相关邮件 ID
- 最准确、最全面

**实现**：
```python
def get_conversation_thread(mailbox, current_email):
    """
    获取邮件的完整对话链

    返回格式：[最早邮件, ..., 当前邮件]
    """
    # 1. 从 References 获取所有相关邮件 ID
    references = current_email.headers.get('references', [])
    if isinstance(references, list):
        references = references[0] if references else ''

    # 2. 解析 References（空格分隔的多个 Message-ID）
    message_ids = references.split() if references else []

    # 3. 添加当前邮件的 Message-ID
    current_id = current_email.headers.get('message-id', [''])[0]
    if current_id:
        message_ids.append(current_id)

    # 4. 从邮箱中获取这些邮件
    thread_emails = []
    for msg_id in message_ids:
        # 搜索 Message-ID 匹配的邮件
        for msg in mailbox.fetch(header={'message-id': msg_id}):
            thread_emails.append({
                'message_id': msg_id,
                'subject': msg.subject,
                'from': msg.from_,
                'date': msg.date,
                'text': msg.text,
                'html': msg.html
            })
            break

    return thread_emails
```

### 方案 B: 递归追溯 In-Reply-To

**优点**：
- 逻辑清晰
- 不依赖 References

**缺点**：
- 需要多次查询
- 如果原始邮件被删除，链条断裂

**实现**：
```python
def get_conversation_thread_recursive(mailbox, current_email):
    """
    递归追溯邮件对话链
    """
    thread = []

    def trace_back(email):
        # 获取这封邮件回复的邮件 ID
        in_reply_to = email.headers.get('in-reply-to', [''])[0]

        if in_reply_to:
            # 查找原始邮件
            for msg in mailbox.fetch(header={'message-id': in_reply_to}):
                thread.insert(0, msg)  # 插入到开头
                trace_back(msg)  # 递归追溯
                break

    trace_back(current_email)
    thread.append(current_email)  # 添加当前邮件

    return thread
```

## 3. 推荐方案：混合策略

结合两种方案的优点：

```python
def get_conversation_thread(mailbox, current_email):
    """
    获取完整对话链（混合策略）

    1. 优先使用 References（快速、完整）
    2. 如果 References 为空，使用 In-Reply-To 递归追溯
    3. 返回按时间排序的邮件列表
    """
    # 策略 1: 尝试从 References 获取
    references = current_email.headers.get('references', [])
    if isinstance(references, list):
        references = references[0] if references else ''

    message_ids = []

    if references:
        # References 存在，解析所有 Message-ID
        message_ids = references.split()
    else:
        # References 为空，使用 In-Reply-To 递归追溯
        in_reply_to = current_email.headers.get('in-reply-to', [''])[0]
        if in_reply_to:
            message_ids = trace_back_chain(mailbox, in_reply_to)

    # 添加当前邮件的 Message-ID
    current_id = current_email.headers.get('message-id', [''])[0]
    if current_id:
        message_ids.append(current_id)

    # 从邮箱获取所有相关邮件
    thread = fetch_emails_by_ids(mailbox, message_ids)

    # 按时间排序
    thread.sort(key=lambda x: x['date'])

    return thread
```

## 4. 返回格式

```python
[
    {
        'message_id': '<msg1@qq.com>',
        'subject': '主题1',
        'from': 'user@example.com',
        'date': datetime(...),
        'text': '邮件内容...',
        'role': 'user'  # user 或 agent
    },
    {
        'message_id': '<msg2@qq.com>',
        'subject': 'Re: 主题1',
        'from': 'agent@company.com',
        'date': datetime(...),
        'text': '回复内容...',
        'role': 'agent'
    },
    # ... 更多邮件
]
```

## 5. 智能体使用示例

```python
def agent_callback(email_context):
    """智能体处理函数"""

    # 获取完整对话历史
    conversation = email_context['conversation_thread']

    # 构建提示词
    prompt = "对话历史：\n"
    for msg in conversation:
        role = "用户" if msg['role'] == 'user' else "智能体"
        prompt += f"{role}: {msg['text']}\n"

    prompt += f"\n用户最新消息: {email_context['current_email']['text']}"
    prompt += "\n请回复用户："

    # 调用 LLM
    reply = llm.generate(prompt)

    return reply
```

## 6. 边界情况处理

### 情况 1: 首次邮件（无回复链）
```python
if not references and not in_reply_to:
    # 这是对话的第一封邮件
    return [current_email]
```

### 情况 2: 原始邮件已删除
```python
# 尽力获取能找到的邮件，缺失的用占位符标识
for msg_id in message_ids:
    msg = fetch_email_by_id(mailbox, msg_id)
    if msg:
        thread.append(msg)
    else:
        thread.append({
            'message_id': msg_id,
            'subject': '[邮件已删除]',
            'text': '[此邮件不在邮箱中]',
            'deleted': True
        })
```

### 情况 3: 多个用户同时对话
```python
# 只保留与监控发件人相关的邮件
watched_senders = ['user1@example.com', 'user2@example.com']
agent_email = 'agent@company.com'

filtered_thread = [
    msg for msg in thread
    if msg['from'] in watched_senders or msg['from'] == agent_email
]
```

## 7. 性能优化

### 缓存策略
```python
# 缓存已获取的邮件，避免重复查询
email_cache = {}  # {message_id: email_data}

def fetch_email_by_id(mailbox, message_id):
    if message_id in email_cache:
        return email_cache[message_id]

    for msg in mailbox.fetch(header={'message-id': message_id}):
        email_cache[message_id] = msg
        return msg

    return None
```

### 批量查询
```python
# 一次性查询多个 Message-ID（如果 IMAP 支持）
def fetch_emails_by_ids(mailbox, message_ids):
    # 构建 OR 查询
    # 注意：imap-tools 可能不支持复杂的 OR 查询
    # 需要逐个查询或使用原始 IMAP 命令
    pass
```

## 8. 测试计划

需要创建测试验证：

1. **首次邮件**：无 References/In-Reply-To
2. **单次回复**：A → B
3. **多次回复**：A → B → A → B
4. **原始邮件缺失**：References 指向不存在的邮件
5. **References 格式异常**：空格、换行等

## 9. 实现优先级

1. ✅ **基础实现**：References 解析 + 邮件获取
2. ⚠️ **递归回退**：In-Reply-To 追溯（如果 References 为空）
3. 📝 **缓存优化**：避免重复查询
4. 📝 **错误处理**：缺失邮件、格式异常

## 10. 关键问题

### Q1: imap-tools 是否支持按 Message-ID 搜索？
需要测试：
```python
mailbox.fetch(header={'message-id': '<abc@example.com>'})
```

### Q2: References 的格式是什么？
- 单个字符串，空格分隔多个 Message-ID
- 还是列表？
- 需要实际测试确认

### Q3: QQ 邮箱是否保留完整的 References？
- 不同邮件服务商可能处理不同
- 需要实际测试
