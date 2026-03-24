#!/usr/bin/env python3
"""
邮件处理技能的简化测试用例
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# 添加脚本路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../scripts'))

from send_email import send_email
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
        self.assertEqual(subject, 'Re: Test Email')
    
    def test_generate_greeting(self):
        """测试生成问候语"""
        generator = EmailReplyGenerator(self.test_email_data)
        
        # 测试中文问候
        greeting = generator.generate_greeting('张三 <zhangsan@example.com>')
        self.assertIn('张三 您好', greeting)
        
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

if __name__ == '__main__':
    # 创建测试报告目录
    os.makedirs('test_reports', exist_ok=True)
    
    # 运行测试
    unittest.main(
        testRunner=unittest.TextTestRunner(verbosity=2),
        exit=False
    )