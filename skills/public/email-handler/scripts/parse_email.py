#!/usr/bin/env python3
"""
解析邮件内容的Python脚本
可以从原始邮件数据中提取关键信息
"""

import email
from email.header import decode_header
import re
from bs4 import BeautifulSoup

class EmailParser:
    """邮件解析器"""
    
    def __init__(self, email_data):
        """
        初始化解析器
        
        参数:
            email_data: 原始邮件数据（字节流或字符串）
        """
        if isinstance(email_data, bytes):
            self.msg = email.message_from_bytes(email_data)
        else:
            self.msg = email.message_from_string(email_data)
    
    def decode_header_value(self, header_value):
        """解码邮件头"""
        if not header_value:
            return None
            
        decoded = []
        for part, encoding in decode_header(header_value):
            if isinstance(part, bytes):
                try:
                    decoded.append(part.decode(encoding or 'utf-8'))
                except:
                    decoded.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded.append(str(part))
        return ''.join(decoded)
    
    def get_basic_info(self):
        """获取基本信息"""
        return {
            "from": self.decode_header_value(self.msg.get("From")),
            "to": self.decode_header_value(self.msg.get("To")),
            "cc": self.decode_header_value(self.msg.get("Cc")),
            "bcc": self.decode_header_value(self.msg.get("Bcc")),
            "subject": self.decode_header_value(self.msg.get("Subject")),
            "date": self.msg.get("Date"),
            "message_id": self.msg.get("Message-ID"),
            "in_reply_to": self.msg.get("In-Reply-To"),
            "references": self.msg.get("References")
        }
    
    def get_body(self, prefer_html=False):
        """
        获取邮件正文
        
        参数:
            prefer_html: 是否优先返回HTML格式（默认False，优先返回纯文本）
            
        返回:
            tuple: (正文内容, 内容类型)
        """
        text_body = ""
        html_body = ""
        
        if self.msg.is_multipart():
            for part in self.msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # 跳过附件
                if "attachment" in content_disposition:
                    continue
                
                # 获取纯文本内容
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            text_body = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
                
                # 获取HTML内容
                elif content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_body = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            # 非多部分邮件
            content_type = self.msg.get_content_type()
            try:
                payload = self.msg.get_payload(decode=True)
                if payload:
                    if content_type == "text/plain":
                        text_body = payload.decode('utf-8', errors='ignore')
                    elif content_type == "text/html":
                        html_body = payload.decode('utf-8', errors='ignore')
            except:
                pass
        
        # 返回合适的内容
        if prefer_html and html_body:
            return html_body, "html"
        elif text_body:
            return text_body, "plain"
        elif html_body:
            return html_body, "html"
        else:
            return "", "plain"
    
    def get_attachments(self, save_dir=None):
        """
        获取附件信息
        
        参数:
            save_dir: 保存附件的目录（可选，如果提供则保存附件）
            
        返回:
            list: 附件信息列表
        """
        attachments = []
        
        if self.msg.is_multipart():
            for part in self.msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" in content_disposition:
                    filename = self.decode_header_value(part.get_filename())
                    content_type = part.get_content_type()
                    size = len(part.get_payload(decode=True) or b"")
                    
                    attachment_info = {
                        "filename": filename,
                        "content_type": content_type,
                        "size": size
                    }
                    
                    # 保存附件
                    if save_dir:
                        import os
                        os.makedirs(save_dir, exist_ok=True)
                        file_path = os.path.join(save_dir, filename)
                        try:
                            with open(file_path, 'wb') as f:
                                f.write(part.get_payload(decode=True))
                            attachment_info["saved_path"] = file_path
                        except Exception as e:
                            attachment_info["error"] = str(e)
                    
                    attachments.append(attachment_info)
        
        return attachments
    
    def extract_links(self, html_content=None):
        """
        从邮件中提取链接
        
        参数:
            html_content: HTML内容（可选，若不提供则从邮件中获取）
            
        返回:
            list: 链接列表
        """
        links = []
        
        if not html_content:
            html_content, _ = self.get_body(prefer_html=True)
        
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)
                links.append({
                    "url": href,
                    "text": text
                })
        else:
            # 从纯文本中提取链接
            text_content, _ = self.get_body()
            url_pattern = re.compile(r'https?://\S+|www\.\S+')
            matches = url_pattern.findall(text_content)
            for match in matches:
                links.append({
                    "url": match,
                    "text": match
                })
        
        return links
    
    def extract_entities(self):
        """
        提取邮件中的实体信息
        
        返回:
            dict: 实体信息
        """
        text_content, _ = self.get_body()
        entities = {
            "emails": [],
            "phone_numbers": [],
            "urls": []
        }
        
        # 提取邮箱地址
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        entities["emails"] = list(set(email_pattern.findall(text_content)))
        
        # 提取电话号码（简单匹配）
        phone_pattern = re.compile(r'\b(\+?[0-9]{1,3}[- .]?)?[0-9]{3}[- .]?[0-9]{3}[- .]?[0-9]{4}\b')
        entities["phone_numbers"] = list(set(phone_pattern.findall(text_content)))
        
        # 提取URL
        url_pattern = re.compile(r'https?://\S+|www\.\S+')
        entities["urls"] = list(set(url_pattern.findall(text_content)))
        
        return entities
    
    def parse_all(self, save_attachments=False, attachments_dir="./attachments"):
        """
        解析所有信息
        
        参数:
            save_attachments: 是否保存附件
            attachments_dir: 附件保存目录
            
        返回:
            dict: 完整的解析结果
        """
        result = {}
        result["basic_info"] = self.get_basic_info()
        result["body"], result["content_type"] = self.get_body()
        result["html_body"], _ = self.get_body(prefer_html=True)
        
        if save_attachments:
            result["attachments"] = self.get_attachments(attachments_dir)
        else:
            result["attachments"] = self.get_attachments()
        
        result["links"] = self.extract_links()
        result["entities"] = self.extract_entities()
        
        return result

if __name__ == "__main__":
    # 示例用法
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='解析邮件内容脚本')
    parser.add_argument('--file', help='邮件文件路径')
    parser.add_argument('--data', help='原始邮件数据（字符串）')
    parser.add_argument('--save-attachments', action='store_true', help='是否保存附件')
    parser.add_argument('--attachments-dir', default='./attachments', help='附件保存目录')
    parser.add_argument('--output', help='输出JSON文件路径')
    
    args = parser.parse_args()
    
    try:
        if args.file:
            with open(args.file, 'rb') as f:
                email_data = f.read()
        elif args.data:
            email_data = args.data
        else:
            print("请提供邮件文件或原始数据")
            exit(1)
        
        parser = EmailParser(email_data)
        result = parser.parse_all(args.save_attachments, args.attachments_dir)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"解析结果已保存到 {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"解析出错: {e}")
        exit(1)