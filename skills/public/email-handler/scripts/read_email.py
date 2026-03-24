#!/usr/bin/env python3
"""
读取邮件的Python脚本
支持IMAP协议读取收件箱邮件
"""

import imaplib
import email
from email.header import decode_header
import json
import os

def read_email(imap_server, imap_port, email_address, password, folder="INBOX", search_criteria="ALL", limit=10):
    """
    读取邮件
    
    参数:
        imap_server: IMAP服务器地址
        imap_port: IMAP服务器端口
        email_address: 邮箱地址
        password: 邮箱密码或授权码
        folder: 邮箱文件夹（默认INBOX）
        search_criteria: 搜索条件（默认ALL）
        limit: 最大读取邮件数量（默认10）
    
    返回:
        tuple: (是否成功, 结果数据/错误信息)
    """
    try:
        # 连接到IMAP服务器
        imap = imaplib.IMAP4_SSL(imap_server, imap_port)
        imap.login(email_address, password)
        
        # 选择邮箱文件夹
        imap.select(folder)
        
        # 搜索邮件
        status, messages = imap.search(None, search_criteria)
        if status != 'OK':
            return (False, "未找到邮件")
        
        # 获取邮件ID列表
        email_ids = messages[0].split()
        email_ids = email_ids[-limit:]  # 只获取最新的limit封邮件
        
        emails = []
        
        for email_id in email_ids:
            # 获取邮件内容
            status, msg_data = imap.fetch(email_id, "(RFC822)")
            if status != 'OK':
                print(f"无法获取邮件 {email_id}")
                continue
            
            # 解析邮件
            msg = email.message_from_bytes(msg_data[0][1])
            
            # 解码主题
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')
            
            # 解码发件人
            from_, encoding = decode_header(msg.get("From"))[0]
            if isinstance(from_, bytes):
                from_ = from_.decode(encoding if encoding else 'utf-8')
            
            # 获取收件人
            to_ = msg.get("To")
            if to_:
                to_, encoding = decode_header(to_)[0]
                if isinstance(to_, bytes):
                    to_ = to_.decode(encoding if encoding else 'utf-8')
            
            # 获取日期
            date_ = msg.get("Date")
            
            # 获取邮件正文
            body = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    try:
                        # 获取邮件正文
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                        
                        # 处理附件
                        elif "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                filename = decode_header(filename)[0][0]
                                if isinstance(filename, bytes):
                                    filename = filename.decode('utf-8', errors='ignore')
                                attachments.append(filename)
                                
                    except Exception as e:
                        print(f"解析邮件部分出错: {e}")
                        continue
            else:
                # 非多部分邮件
                content_type = msg.get_content_type()
                if content_type == "text/plain":
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
            
            # 添加邮件信息到列表
            emails.append({
                "id": email_id.decode(),
                "subject": subject,
                "from": from_,
                "to": to_,
                "date": date_,
                "body": body[:500] + "..." if len(body) > 500 else body,  # 截断长正文
                "attachments": attachments,
                "has_attachments": len(attachments) > 0
            })
        
        # 关闭连接
        imap.close()
        imap.logout()
        
        return (True, emails)
        
    except Exception as e:
        return (False, f"读取邮件失败: {str(e)}")

if __name__ == "__main__":
    # 示例用法
    import argparse
    
    parser = argparse.ArgumentParser(description='读取邮件脚本')
    parser.add_argument('--imap-server', required=True, help='IMAP服务器地址')
    parser.add_argument('--imap-port', type=int, required=True, help='IMAP服务器端口')
    parser.add_argument('--email', required=True, help='邮箱地址')
    parser.add_argument('--password', required=True, help='邮箱密码或授权码')
    parser.add_argument('--folder', default='INBOX', help='邮箱文件夹（默认INBOX）')
    parser.add_argument('--search', default='ALL', help='搜索条件（默认ALL）')
    parser.add_argument('--limit', type=int, default=10, help='最大读取邮件数量（默认10）')
    parser.add_argument('--output', help='输出JSON文件路径')
    
    args = parser.parse_args()
    
    success, result = read_email(
        args.imap_server,
        args.imap_port,
        args.email,
        args.password,
        args.folder,
        args.search,
        args.limit
    )
    
    if success:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"邮件数据已保存到 {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"错误: {result}")
        exit(1)