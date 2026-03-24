---
name: email-handler
description: 全面处理邮件相关任务，支持SMTP发送邮件（含附件）、IMAP读取邮件、解析邮件内容/实体/链接、AI智能生成回复（主题/问候语/正文模板）。触发关键词包括："邮件"、"email"、"发邮件"、"查邮件"、"读邮件"、"回复邮件"、"发送邮件"、"读取邮件"、"解析邮件"、"邮件生成"、"写信"、"邮件模板"。
---

# 邮件处理技能

## 功能说明
这个技能可以帮助你处理各种邮件相关任务：
1. 发送邮件
2. 读取和解析邮件内容
3. 生成专业的邮件回复
4. 搜索和筛选邮件
5. 管理邮件文件夹

## 发送邮件
### 步骤：
1. 确认收件人邮箱地址
2. 确认邮件主题
3. 确认邮件正文内容
4. 确认是否有附件
5. 使用合适的工具发送邮件

### 示例命令：
```bash
# 使用sendmail发送邮件
echo "邮件正文" | sendmail -s "邮件主题" recipient@example.com

# 使用Python发送邮件（带附件）
python3 - << 'EOF'
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# 配置
sender_email = "your_email@example.com"
receiver_email = "recipient@example.com"
password = "your_password"
subject = "邮件主题"
body = "邮件正文"

# 创建邮件
msg = MIMEMultipart()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = subject
msg.attach(MIMEText(body, 'plain'))

# 添加附件
filename = "document.pdf"
attachment = open(filename, "rb")
part = MIMEBase('application', 'octet-stream')
part.set_payload((attachment).read())
encoders.encode_base64(part)
part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
msg.attach(part)

# 发送邮件
with smtplib.SMTP_SSL('smtp.example.com', 465) as server:
    server.login(sender_email, password)
    server.send_message(msg)
EOF
```

## 读取邮件
### 步骤：
1. 确认邮箱类型（IMAP/POP3）
2. 配置邮箱服务器信息
3. 连接到邮箱服务器
4. 读取邮件内容
5. 解析邮件主题、发件人、正文等信息

### 示例命令：
```bash
# 使用Python读取IMAP邮件
python3 - << 'EOF'
import imaplib
import email
from email.header import decode_header

# 配置
username = "your_email@example.com"
password = "your_password"
imap_server = "imap.example.com"

# 连接到IMAP服务器
imap = imaplib.IMAP4_SSL(imap_server)
imap.login(username, password)

# 选择邮箱
imap.select("INBOX")

# 搜索邮件
status, messages = imap.search(None, "ALL")

# 处理邮件
for num in messages[0].split():
    status, msg_data = imap.fetch(num, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding)
            from_ = msg.get("From")
            print(f"Subject: {subject}")
            print(f"From: {from_}")
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        pass
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        print(f"Body: {body}")
            else:
                content_type = msg.get_content_type()
                body = msg.get_payload(decode=True).decode()
                if content_type == "text/plain":
                    print(f"Body: {body}")

# 关闭连接
imap.close()
imap.logout()
EOF
```

## 生成邮件回复
### 步骤：
1. 分析原始邮件内容
2. 确定回复要点
3. 生成专业、礼貌的回复内容
4. 根据需要添加个性化元素

### 示例：
原始邮件：
```
主题：会议延期通知
您好，原定于明天下午2点的项目会议将延期至本周四下午3点举行，望知悉。
谢谢！
张三
```

生成的回复：
```
主题：回复：会议延期通知
张三您好：

已收到会议延期通知，我会按时参加本周四下午3点的会议。

感谢告知！
李四
```

## 注意事项
1. 发送邮件前请确认收件人地址正确
2. 处理敏感信息时请注意安全
3. 遵守公司邮件使用政策
4. 大型附件建议使用云存储链接分享