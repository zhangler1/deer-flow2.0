#!/usr/bin/env python3
"""
邮件处理技能的测试用例
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# 添加脚本路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../scripts'))

from send_email import send_email
from read_email import read_email
from parse_email import EmailParser
from generate_reply import EmailReplyGenerator

class TestEmailHandler(unittest.TestCase):
    """邮件处理技能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_email_data = {
            'from': 'sender@example.com',
            'to': 'recipient@example.com',
            'subject': 'Test Email',
            'body': 'This is a test email\n\nThank you for your attention!',
            'message_id': '<123456@example.com>'
        }
        
        # 创建测试用的原始邮件数据
        self.raw_email = """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 23 Mar 2026 10:00:00 +0800
Message-ID: <123456@example.com>

This is a test email

Thank you for your attention!"""
    
    def test_generate_subject(self):
        """测试生成回复主题"""
        generator = EmailReplyGenerator(self.test_email_data)
        
        # 测试正常情况
        subject = generator.generate_subject('Test Email')
        self.assertEqual(subject, 'Re: Test Email')
        
        # 测试已经有Re:前缀的情况
        subject = generator.generate_subject('Re: Test Email')
        self.assertEqual(subject, 'Re: Test Email')
        
        # 测试中文回复前缀
        subject = generator.generate_subject('回复: Test Email')
        self.assertEqual(subject, '回复: Test Email')
        
        # 测试空主题
        subject = generator.generate_subject('')
        self.assertEqual(subject, '回复')
    
    def test_generate_greeting(self):
        """测试生成问候语"""
        generator = EmailReplyGenerator(self.test_email_data)
        
        # 测试中文问候
        greeting = generator.generate_greeting('张三 <zhangsan@example.com>')
        self.assertIn('张三您好', greeting)
        
        # 测试英文问候
        greeting = generator.generate_greeting('John Doe <john@example.com>', use_chinese=False)
        self.assertIn('Dear John Doe', greeting)
        
        # 测试纯邮箱地址
        greeting = generator.generate_greeting('test@example.com')
        self.assertIn('您好', greeting)
    
    @patch('smtplib.SMTP_SSL')
    def test_send_email_success(self, mock_smtp):
        """测试成功发送邮件"""
        # 设置mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # 测试发送邮件
        success, message = send_email(
            sender_email='sender@example.com',
            sender_password='password123',
            receiver_email='recipient@example.com',
            subject='Test Email',
            body='This is a test email body',
            smtp_server='smtp.example.com',
            smtp_port=465
        )
        
        self.assertTrue(success)
        self.assertEqual(message, '邮件发送成功')
        mock_server.login.assert_called_once_with('sender@example.com', 'password123')
        mock_server.send_message.assert_called_once()
    
    @patch('smtplib.SMTP_SSL')
    def test_send_email_with_attachment(self, mock_smtp):
        """测试发送带附件的邮件"""
        # 设置mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # 创建临时测试文件
        test_file = '/tmp/test_attachment.txt'
        with open(test_file, 'w') as f:
            f.write('Test attachment content')
        
        try:
            # 测试发送带附件的邮件
            success, message = send_email(
                sender_email='sender@example.com',
                sender_password='password123',
                receiver_email='recipient@example.com',
                subject='Test Email (with attachment)',
                body='This is a test email with attachment',
                smtp_server='smtp.example.com',
                smtp_port=465,
                attachment_path=test_file
            )
            
            self.assertTrue(success)
            self.assertEqual(message, '邮件发送成功')
            mock_server.send_message.assert_called_once()
            
        finally:
            # 清理临时文件
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_parse_email_basic_info(self):
        """测试解析邮件基本信息"""
        parser = EmailParser(self.raw_email.encode())
        basic_info = parser.get_basic_info()
        
        self.assertEqual(basic_info['from'], 'sender@example.com')
        self.assertEqual(basic_info['to'], 'recipient@example.com')
        self.assertEqual(basic_info['subject'], 'Test Email')
        self.assertEqual(basic_info['message_id'], '<123456@example.com>')
        self.assertIn('Mon, 23 Mar 2026', basic_info['date'])
    
    def test_parse_email_body(self):
        """测试解析邮件正文"""
        parser = EmailParser(self.raw_email.encode())
        body, content_type = parser.get_body()
        
        self.assertEqual(content_type, 'plain')
        self.assertIn('This is a test email', body)
        self.assertIn('Thank you for your attention!', body)
    
    def test_extract_entities(self):
        """测试提取邮件中的实体"""
        # 创建包含实体的测试邮件
        email_with_entities = """From: sender@example.com
To: recipient@example.com
Subject: Contact Information

Contact us:
Email: contact@example.com
Phone: +86 123 4567 8901
Website: https://www.example.com
"""
        
        parser = EmailParser(email_with_entities.encode())
        entities = parser.extract_entities()
        
        self.assertIn('contact@example.com', entities['emails'])
        self.assertIn('+86 123 4567 8901', entities['phone_numbers'])
        self.assertIn('https://www.example.com', entities['urls'])
    
    def test_extract_links(self):
        """测试提取邮件中的链接"""
        # 创建包含链接的HTML邮件
        html_email = """From: sender@example.com
To: recipient@example.com
Subject: Email with links
Content-Type: text/html; charset=utf-8

<p>Please visit our website: <a href="https://www.example.com">Example Website</a></p>
<p>Or go directly to: https://www.example.com/docs</p>
"""
        
        parser = EmailParser(html_email.encode())
        links = parser.extract_links()
        
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]['url'], 'https://www.example.com')
        self.assertEqual(links[0]['text'], 'Example Website')
        self.assertEqual(links[1]['url'], 'https://www.example.com/docs')
        self.assertEqual(links[1]['text'], 'https://www.example.com/docs')
    
    def test_generate_reply(self):
        """测试生成完整邮件回复"""
        generator = EmailReplyGenerator(self.test_email_data)
        
        reply = generator.generate_full_reply(
            'This is my reply content.\n\nThank you!',
            include_quote=True,
            use_chinese=False
        )
        
        # 验证回复主题
        self.assertEqual(reply['subject'], 'Re: Test Email')
        
        # 验证回复正文包含必要内容
        self.assertIn('sender@example.com', reply['to'])
        self.assertIn('This is my reply content', reply['body'])
        self.assertIn('--- Original Message ---', reply['body'])
        self.assertIn('This is a test email', reply['body'])
        
        # 验证引用原始邮件
        self.assertIn('> This is a test email', reply['body'])
    
    def test_reply_templates(self):
        """测试回复模板"""
        generator = EmailReplyGenerator()
        
        # 测试确认收到模板
        template = generator.generate_template('acknowledge')
        self.assertIn('已收到您的邮件，我们正在处理中', template)
        
        # 测试跟进模板
        template = generator.generate_template('follow_up')
        self.assertIn('关于之前我们讨论的事项，想跟进一下进展情况', template)
        
        # 测试英文模板
        template = generator.generate_template('acknowledge', use_chinese=False)
        self.assertIn('Thank you for your email', template)
    
    @patch('imaplib.IMAP4_SSL')
    def test_read_email(self, mock_imap):
        """测试读取邮件"""
        # 设置mock
        mock_server = MagicMock()
        mock_imap.return_value = mock_server
        
        # 设置返回值
        mock_server.select.return_value = ('OK', [])
        mock_server.search.return_value = ('OK', [b'1 2 3'])
        
        # 模拟邮件数据
        mock_email_data = b'From: sender@example.com\r\nSubject: Test Email\r\n\r\nEmail body'
        response = b'1 (RFC822 %d)\r\n' % len(mock_email_data)
        mock_server.fetch.return_value = ('OK', [(response, mock_email_data, b')']) 
        
        # 测试读取邮件
        success, result = read_email(
            imap_server='imap.example.com',
            imap_port=993,
            email_address='user@example.com',
            password='password123',
            limit=1
        )
        
        self.assertTrue(success)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['subject'], 'Test Email')
        mock_server.login.assert_called_once_with('user@example.com', 'password123')
        mock_server.select.assert_called_once_with('INBOX')

if __name__ == '__main__':
    # 创建测试报告目录
    os.makedirs('test_reports', exist_ok=True)
    
    # 运行测试
    unittest.main(
        testRunner=unittest.TextTestRunner(verbosity=2),
        exit=False
    )
    
    # 生成HTML测试报告（如果安装了html-testRunner）
    try:
        from html_testRunner import HTMLTestRunner
        
        with open('test_reports/email_handler_test_report.html', 'w') as f:
            runner = HTMLTestRunner(
                stream=f,
                title='Email Handler Skill Test Report',
                description='Automated test results for email handler skill'
            )
            unittest.main(testRunner=runner, exit=False)
        print("\nHTML test report generated: test_reports/email_handler_test_report.html")
        
    except ImportError:
        print("\nNote: Install html-testRunner to generate beautiful HTML test reports:")
        print("pip install html-testRunner")