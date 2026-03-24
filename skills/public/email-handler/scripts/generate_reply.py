#!/usr/bin/env python3
"""
生成邮件回复的Python脚本
可以根据原始邮件内容生成合适的回复
"""

import re
from datetime import datetime

class EmailReplyGenerator:
    """邮件回复生成器"""
    
    def __init__(self, original_email=None):
        """
        初始化回复生成器
        
        参数:
            original_email: 原始邮件信息（可选）
        """
        self.original_email = original_email or {}
    
    def generate_subject(self, original_subject=None):
        """
        生成回复主题
        
        参数:
            original_subject: 原始邮件主题
            
        返回:
            str: 回复主题
        """
        if not original_subject:
            original_subject = self.original_email.get('subject', '')
        
        if not original_subject:
            return "回复"
        
        # 检查是否已经有Re:前缀
        if original_subject.lower().startswith('re:'):
            return original_subject
        
        # 检查是否有其他语言的回复前缀
        prefixes = ['回复:', '答复:', 'aw:', 'sv:', 'vs:']
        for prefix in prefixes:
            if original_subject.lower().startswith(prefix.lower()):
                return original_subject
        
        return f"Re: {original_subject}"
    
    def generate_greeting(self, original_sender=None, use_chinese=True):
        """
        生成问候语
        
        参数:
            original_sender: 原始发件人信息
            use_chinese: 是否使用中文
            
        返回:
            str: 问候语
        """
        if not original_sender:
            original_sender = self.original_email.get('from', '')
        
        # 提取姓名
        name = self._extract_name(original_sender)
        
        if use_chinese:
            if name:
                hour = datetime.now().hour
                if hour < 12:
                    return f"{name}您好：\n\n早上好！"
                elif hour < 18:
                    return f"{name}您好：\n\n下午好！"
                else:
                    return f"{name}您好：\n\n晚上好！"
            else:
                return "您好：\n\n"
        else:
            if name:
                return f"Dear {name},\n\n"
            else:
                return "Hello,\n\n"
    
    def _extract_name(self, sender_info):
        """
        从发件人信息中提取姓名
        
        参数:
            sender_info: 发件人信息字符串
            
        返回:
            str: 姓名
        """
        if not sender_info:
            return None
        
        # 匹配 "姓名 <邮箱>" 格式
        match = re.search(r'"?([^"]+)"?\s*<[^>]+>', sender_info)
        if match:
            return match.group(1)
        
        # 匹配纯姓名（不含邮箱）
        match = re.search(r'^[\u4e00-\u9fa5a-zA-Z\s]+', sender_info)
        if match:
            return match.group(0).strip()
        
        # 提取邮箱前缀
        match = re.search(r'^([^@]+)@', sender_info)
        if match:
            return match.group(1)
        
        return None
    
    def generate_acknowledgment(self, original_subject=None, use_chinese=True):
        """
        生成收到邮件的确认语
        
        参数:
            original_subject: 原始邮件主题
            use_chinese: 是否使用中文
            
        返回:
            str: 确认语
        """
        if not original_subject:
            original_subject = self.original_email.get('subject', '')
        
        if use_chinese:
            if original_subject:
                return f"已收到您关于'{original_subject}'的邮件，感谢您的来信。\n\n"
            else:
                return "已收到您的邮件，感谢您的来信。\n\n"
        else:
            if original_subject:
                return f"Thank you for your email regarding '{original_subject}'.\n\n"
            else:
                return "Thank you for your email.\n\n"
    
    def generate_reply_body(self, response_content, original_body=None, 
                          include_quote=True, use_chinese=True):
        """
        生成回复正文
        
        参数:
            response_content: 回复内容
            original_body: 原始邮件正文
            include_quote: 是否引用原始邮件
            use_chinese: 是否使用中文
            
        返回:
            str: 完整的回复正文
        """
        body_parts = []
        
        # 添加问候语
        body_parts.append(self.generate_greeting(use_chinese=use_chinese))
        
        # 添加确认语
        body_parts.append(self.generate_acknowledgment(use_chinese=use_chinese))
        
        # 添加回复内容
        body_parts.append(response_content)
        body_parts.append("\n\n")
        
        # 添加引用
        if include_quote and original_body:
            if use_chinese:
                body_parts.append("--- 原始邮件 ---\n")
            else:
                body_parts.append("--- Original Message ---\n")
            
            # 引用原始邮件
            quoted_body = self._quote_email(original_body, use_chinese=use_chinese)
            body_parts.append(quoted_body)
        
        # 添加结束语
        if use_chinese:
            body_parts.append("\n\n此致敬礼\n")
        else:
            body_parts.append("\n\nBest regards,\n")
        
        return ''.join(body_parts)
    
    def _quote_email(self, body, use_chinese=True, quote_char="> "):
        """
        引用邮件内容
        
        参数:
            body: 原始邮件正文
            use_chinese: 是否使用中文
            quote_char: 引用符号
            
        返回:
            str: 引用后的邮件内容
        """
        if not body:
            return ""
        
        # 清理正文
        lines = body.strip().split('\n')
        
        # 跳过空行
        while lines and not lines[0].strip():
            lines.pop(0)
        
        # 引用每一行
        quoted_lines = []
        for line in lines:
            if line.strip():
                quoted_lines.append(f"{quote_char}{line}")
            else:
                quoted_lines.append(quote_char.rstrip())
        
        return '\n'.join(quoted_lines)
    
    def generate_full_reply(self, response_content, original_email=None, 
                           include_quote=True, use_chinese=True):
        """
        生成完整的邮件回复
        
        参数:
            response_content: 回复内容
            original_email: 原始邮件信息
            include_quote: 是否引用原始邮件
            use_chinese: 是否使用中文
            
        返回:
            dict: 完整的回复信息
        """
        if original_email:
            self.original_email = original_email
        
        original_subject = self.original_email.get('subject', '')
        original_body = self.original_email.get('body', '')
        
        return {
            'subject': self.generate_subject(original_subject),
            'body': self.generate_reply_body(
                response_content,
                original_body,
                include_quote,
                use_chinese
            ),
            'to': self.original_email.get('from', ''),
            'cc': self.original_email.get('cc', ''),
            'in_reply_to': self.original_email.get('message_id', ''),
            'references': self.original_email.get('references', '') or 
                         self.original_email.get('message_id', '')
        }
    
    def generate_template(self, template_type, use_chinese=True):
        """
        生成特定类型的回复模板
        
        参数:
            template_type: 模板类型（'acknowledge', 'follow_up', 'decline', 'accept'）
            use_chinese: 是否使用中文
            
        返回:
            str: 回复模板内容
        """
        templates = {
            'acknowledge': {
                'chinese': "您好：\n\n已收到您的邮件，我们正在处理中，将尽快给您回复。\n\n感谢您的耐心等待！\n",
                'english': "Hello,\n\nThank you for your email. We are currently processing your request and will get back to you as soon as possible.\n\nThank you for your patience!\n"
            },
            'follow_up': {
                'chinese': "您好：\n\n关于之前我们讨论的事项，想跟进一下进展情况。\n\n如果有任何需要我协助的地方，请随时告诉我。\n\n谢谢！\n",
                'english': "Hello,\n\nI'm following up regarding our previous discussion. I would like to check on the progress.\n\nPlease let me know if there's anything I can assist with.\n\nThank you!\n"
            },
            'decline': {
                'chinese': "您好：\n\n感谢您的邀请/提议，经过仔细考虑，我很遗憾地表示无法接受。\n\n感谢您的理解！\n",
                'english': "Hello,\n\nThank you for your invitation/proposal. After careful consideration, I regret to inform you that I am unable to accept.\n\nThank you for your understanding!\n"
            },
            'accept': {
                'chinese': "您好：\n\n感谢您的邀请/提议，我很高兴地接受。\n\n期待与您合作！\n",
                'english': "Hello,\n\nThank you for your invitation/proposal. I'm pleased to accept.\n\nLooking forward to working with you!\n"
            },
            'information_request': {
                'chinese': "您好：\n\n感谢您的邮件，为了更好地处理您的请求，我需要了解以下信息：\n\n请提供相关信息，谢谢！\n",
                'english': "Hello,\n\nThank you for your email. To better assist you, I would need the following information:\n\nPlease provide the relevant information. Thank you!\n"
            }
        }
        
        template = templates.get(template_type, {})
        if use_chinese:
            return template.get('chinese', template.get('english', ''))
        else:
            return template.get('english', template.get('chinese', ''))

if __name__ == "__main__":
    # 示例用法
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='生成邮件回复脚本')
    parser.add_argument('--content', required=True, help='回复内容')
    parser.add_argument('--original-email', help='原始邮件信息JSON文件')
    parser.add_argument('--no-quote', action='store_true', help='不引用原始邮件')
    parser.add_argument('--english', action='store_true', help='使用英文回复')
    parser.add_argument('--template', help='使用回复模板（acknowledge/follow_up/decline/accept）')
    parser.add_argument('--output', help='输出回复文件路径')
    
    args = parser.parse_args()
    
    try:
        # 读取原始邮件信息
        original_email = {}
        if args.original_email:
            with open(args.original_email, 'r', encoding='utf-8') as f:
                original_email = json.load(f)
        
        generator = EmailReplyGenerator(original_email)
        
        if args.template:
            # 使用模板
            reply_content = generator.generate_template(args.template, use_chinese=not args.english)
            result = generator.generate_full_reply(
                reply_content,
                include_quote=not args.no_quote,
                use_chinese=not args.english
            )
        else:
            # 生成自定义回复
            result = generator.generate_full_reply(
                args.content,
                include_quote=not args.no_quote,
                use_chinese=not args.english
            )
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"回复已保存到 {args.output}")
        else:
            print("主题:", result['subject'])
            print("\n正文:")
            print(result['body'])
            
    except Exception as e:
        print(f"生成回复出错: {e}")
        exit(1)