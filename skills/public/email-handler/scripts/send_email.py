#!/usr/bin/env python3
"""
发送邮件的Python脚本
支持纯文本邮件和带附件的邮件
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

def send_email(sender_email, sender_password, receiver_email, subject, body, smtp_server, smtp_port, attachment_path=None):
    """
    发送邮件
    
    参数:
        sender_email: 发件人邮箱地址
        sender_password: 发件人邮箱密码或授权码
        receiver_email: 收件人邮箱地址
        subject: 邮件主题
        body: 邮件正文
        smtp_server: SMTP服务器地址
        smtp_port: SMTP服务器端口
        attachment_path: 附件路径（可选）
    
    返回:
        tuple: (是否成功, 错误信息)
    """
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        
        # 添加邮件正文
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添加附件
        if attachment_path and os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            part = MIMEBase('application', 'octet-stream')
            with open(attachment_path, 'rb') as file:
                part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {filename}')
            msg.attach(part)
        
        # 发送邮件
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return (True, "邮件发送成功")
        
    except Exception as e:
        return (False, f"邮件发送失败: {str(e)}")

if __name__ == "__main__":
    # 示例用法
    import argparse
    
    parser = argparse.ArgumentParser(description='发送邮件脚本')
    parser.add_argument('--sender', required=True, help='发件人邮箱')
    parser.add_argument('--password', required=True, help='发件人邮箱密码或授权码')
    parser.add_argument('--receiver', required=True, help='收件人邮箱')
    parser.add_argument('--subject', required=True, help='邮件主题')
    parser.add_argument('--body', required=True, help='邮件正文')
    parser.add_argument('--smtp-server', required=True, help='SMTP服务器地址')
    parser.add_argument('--smtp-port', type=int, required=True, help='SMTP服务器端口')
    parser.add_argument('--attachment', help='附件路径（可选）')
    
    args = parser.parse_args()
    
    success, message = send_email(
        args.sender,
        args.password,
        args.receiver,
        args.subject,
        args.body,
        args.smtp_server,
        args.smtp_port,
        args.attachment
    )
    
    print(message)
    exit(0 if success else 1)