#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت لتحديث تصميم صفحة المراسلات لتطابق WhatsApp Web
"""

import re
from pathlib import Path

def update_messages_whatsapp_style():
    file_path = r"e:\موقع المخزن\company_messages.html"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the style section
    style_start = content.find('<style>') + 7
    style_end = content.find('</style>')
    
    # New WhatsApp CSS
    new_css = """
        /* ========== WhatsApp Web Design System ========== */
        
        /* Color Variables */
        :root {
            /* Brand Colors */
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --wa-green: #00a884;
            --wa-green-dark: #008069;
            --wa-teal: #06cf9c;
            
            /* Backgrounds */
            --wa-bg: #f0f2f5;
            --wa-panel-bg: #ffffff;
            --wa-chat-bg: #efeae2;
            --wa-sidebar-bg: #ffffff;
            
            /* Messages */
            --wa-msg-sent: #d9fdd3;
            --wa-msg-received: #ffffff;
            
            /* Text */
            --wa-text-primary: #111b21;
            --wa-text-secondary: #667781;
            --wa-text-tertiary: #8696a0;
            
            /* Borders */
            --wa-border: #e9edef;
            --wa-divider: rgba(134, 150, 160, 0.15);
            
            /* States */
            --wa-hover: #f5f6f6;
            --wa-active: #ebebeb;
            --wa-selected: #d1d7db;
            
            /* Shadows */
            --wa-shadow-sm: 0 1px 0.5px rgba(11, 20, 26, 0.13);
            --wa-shadow-md: 0 1px 3px rgba(11, 20, 26, 0.08);
            --wa-shadow-lg: 0 2px 12px rgba(11, 20, 26, 0.12);
        }

        body.dark-mode {
            --wa-bg: #111b21;
            --wa-panel-bg: #222e35;
            --wa-chat-bg: #0b141a;
            --wa-sidebar-bg: #111b21;
            --wa-msg-sent: #005c4b;
            --wa-msg-received: #202c33;
            --wa-text-primary: #e9edef;
            --wa-text-secondary: #8696a0;
            --wa-text-tertiary: #667781;
            --wa-border: #2a3942;
            --wa-hover: #2a3942;
            --wa-active: #202c33;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html, body {
            height: 100%;
            overflow: hidden;
        }

        body {
            font-family: 'Cairo', 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--wa-bg);
            padding-top: 76px;
            color: var(--wa-text-primary);
            -webkit-font-smoothing:antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* ========== Navbar ========== */
        .navbar {
            background: var(--primary-gradient);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            position: fixed;
            top: 0;
            width: 100%;
            z-index: 1000;
            height: 76px;
        }

        .navbar-brand {
            font-weight: 600;
            display: flex;
            align-items: center;
            color: white !important;
        }

        .navbar-logo {
            height: 35px;
            width: auto;
            margin-left: 10px;
        }

        .navbar-brand .full-text { display: inline; }
        @media (max-width: 767.98px) {
            .navbar-brand .full-text,
            .navbar-brand .short-text { display: none; }
        }
        @media (min-width: 768px) {
            .navbar-brand .short-text { display: none; }
            .navbar-brand .full-text { display: inline; }
        }

        .navbar-nav-notification-wrapper {
            display: flex;
            align-items: center;
            margin-left: auto;
            margin-right: 15px;
            gap: 10px;
        }

        .navbar-nav-notification-wrapper .nav-link {
            padding: 0.5rem;
            color: rgba(255, 255, 255, 0.9);
            transition: all 0.3s ease;
        }

        .navbar-nav-notification-wrapper .nav-link:hover {
            color: #ffffff;
            transform: translateY(-2px);
        }

        @media (max-width: 991.98px) {
            .navbar-nav-user-info { display: none; }
            .navbar-collapse .navbar-nav {
                width: 100%;
                margin-top: 10px;
            }
            .navbar-collapse .nav-item {
                text-align: center;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .navbar-collapse .nav-link {
                padding: 12px 15px;
                color: rgba(255, 255, 255, 0.9);
            }
        }

        /* ========== Messages Container (WhatsApp Layout) ========== */
        .messages-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 76px);
            max-width: 100%;
            background: var(--wa-bg);
            overflow: hidden;
        }

        .messages-header {
            background: var(--primary-gradient);
            color: white;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
            flex-shrink: 0;
        }

        .messages-header h3 {
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
        }

        .messages-header i {
            margin-left: 8px;
        }

        /* ========== Search Bar ========== */
        #mainSearchBar {
            background: var(--wa-panel-bg);
            padding: 10px 16px;
            border-bottom: 1px solid var(--wa-border);
            flex-shrink: 0;
        }

        #mainSearchBar .messages-search-group {
            background: var(--wa-bg);
            border-radius: 8px;
            border: none;
            display: flex;
            align-items: center;
            padding: 8px 12px;
        }

        #mainSearchBar .input-group-text {
            background: transparent;
            border: none;
            color: var(--wa-text-tertiary);
            padding: 0 8px 0 0;
        }

        #mainSearchBar .form-control {
            background: transparent;
            border: none;
            outline: none;
            box-shadow: none;
            color: var(--wa-text-primary);
            padding: 0;
        }

        #mainSearchBar .form-control::placeholder {
            color: var(--wa-text-tertiary);
        }

        /* ========== Conversations List ========== */
        .conversations-list {
            flex: 1;
            background: var(--wa-panel-bg);
            overflow-y: auto;
            overflow-x: hidden;
        }

        .conversation-item {
            height: 72px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--wa-border);
            cursor: pointer;
            transition: background-color 0.15s ease;
            position: relative;
        }

        .conversation-item:hover {
            background: var(--wa-hover);
        }

        .conversation-item.active {
            background: var(--wa-active);
        }

        .avatar {
            width: 49px;
            height: 49px;
            border-radius: 50%;
            background: var(--wa-green);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 500;
            font-size: 18px;
            flex-shrink: 0;
            overflow: hidden;
        }

        .avatar-image {
            width: 49px;
            height: 49px;
            border-radius: 50%;
            overflow: hidden;
            background: #dfe5e7;
            flex-shrink: 0;
        }

        .avatar-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .conversation-info {
            flex: 1;
            min-width: 0;
        }

        .company-name {
            font-size: 16px;
            font-weight: 400;
            color: var(--wa-text-primary);
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .last-message {
            font-size: 14px;
            color: var(--wa-text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .unread-badge {
            background: var(--wa-green);
            color: white;
            border-radius: 50%;
            min-width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 500;
            padding: 0 6px;
        }

        /* ========== Chat Section ========== */
        .chat-section {
            display: flex;
            flex-direction: column;
            flex: 1;
            background: var(--wa-chat-bg);
            position: relative;
        }

        .chat-messages {
            flex: 1;
            padding: 20px 8%;
            overflow-y: auto;
            background: var(--wa-chat-bg);
            position: relative;
        }

        /* WhatsApp Background Pattern */
        .chat-messages::before {
            content: "";
            position: absolute;
            inset: 0;
            opacity: 0.06;
            background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="1" fill="%23000"/></svg>');
            background-size: 20px 20px;
            pointer-events: none;
        }

        .message {
            display: flex;
            margin-bottom: 8px;
            position: relative;
            z-index: 1;
        }

        .message.sent {
            justify-content: flex-end;
        }

        .message.received {
            justify-content: flex-start;
        }

        .message-content {
            max-width: 65%;
            padding: 6px 7px 8px 9px;
            border-radius: 7.5px;
            position: relative;
            word-wrap: break-word;
            line-height: 19px;
        }

        .message.sent .message-content {
            background: var(--wa-msg-sent);
            color: var(--wa-text-primary);
            box-shadow:var(--wa-shadow-sm);
        }

        .message.received .message-content {
            background: var(--wa-msg-received);
            color: var(--wa-text-primary);
            box-shadow: var(--wa-shadow-sm);
        }

        .message-time {
            font-size: 11px;
            color: var(--wa-text-tertiary);
            margin-top: 2px;
            display: block;
            text-align: left;
        }

        .message.sent .message-time {
            text-align: right;
        }

        .message-meta {
            display: flex;
            align-items: center;
            gap: 3px;
            font-size: 11px;
            color: var(--wa-text-tertiary);
        }

        .message-status {
            font-size: 16px;
        }

        .message-status.read {
            color: #53bdeb;
        }

        /* ========== Chat Input ========== */
        .chat-input-container {
            background: var(--wa-panel-bg);
            padding: 10px 16px;
            border-top: 1px solid var(--wa-border);
            flex-shrink: 0;
        }

        .input-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .message-input {
            flex: 1;
            background: var(--wa-bg);
            border: none;
            border-radius: 21px;
            padding: 9px 12px;
            font-size: 15px;
            color: var(--wa-text-primary);
            outline: none;
            resize: none;
        }

        .message-input::placeholder {
            color: var(--wa-text-tertiary);
        }

        .send-btn {
            width: 42px;
            height: 42px;
            background: var(--wa-green);
            border: none;
            border-radius: 50%;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 18px;
        }

        .send-btn:hover {
            background: var(--wa-green-dark);
            transform: scale(1.05);
        }

        .send-btn:active {
            transform: scale(0.95);
        }

        /* ========== Back Button ========== */
        .back-btn {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            padding: 8px 15px;
            border-radius: 18px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
        }

        .back-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }

        /* ========== Loading & Errors ========== */
        .loading, .error-message {
            padding: 40px;
            text-align: center;
        }

        .loading {
            color: var(--wa-text-secondary);
        }

        .error-message {
            color: #ea4335;
        }

        /* ========== FAB Button ========== */
        .fab-all-companies {
            position: fixed;
            bottom: 24px;
            left: 24px;
            width: 56px;
            height: 56px;
            background: var(--wa-green);
            border: none;
            border-radius: 50%;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: var(--wa-shadow-lg);
            cursor: pointer;
            z-index: 100;
            transition: all 0.2s ease;
        }

        .fab-all-companies:hover {
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 4px 16px rgba(11, 20, 26, 0.2);
        }

        /* ========== Chat Header ========== */
        .chat-header-text {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        #chatTitle {
            font-size: 16px;
            font-weight: 400;
            margin: 0;
        }

        #chatSubtitle,
        #typingIndicator {
            font-size: 13px;
            color: rgba(255, 255, 255, 0.8);
        }

        /* ========== Responsive Design ========== */
        
        /* Desktop: Side-by-side layout */
        @media (min-width: 768px) {
            .messages-container {
                flex-direction: row;
            }

            #conversationsPanel {
                width: 350px;
                border-left: 1px solid var(--wa-border);
                display: flex !important;
                flex-direction: column;
                flex-shrink: 0;
            }

            .chat-section {
                flex: 1;
            }

            .conversations-list {
                flex: 1;
            }

            .fab-all-companies {
                display: none;
            }
        }

        /* Tablet */
        @media (min-width: 768px) and (max-width: 1024px) {
            #conversationsPanel {
                width: 300px;
            }

            .chat-messages {
                padding: 20px 5%;
            }
        }

        /* Mobile */
        @media (max-width: 767.98px) {
            body {
                padding-top: 76px;
            }

            .messages-container {
                height: calc(100vh - 76px);
            }

            .message-content {
                max-width: 80%;
            }

            .chat-messages {
                padding: 12px 8px;
            }

            #conversationsPanel {
                display: flex;
                flex-direction: column;
                height: 100%;
            }

            .chat-section {
                position: fixed;
                inset: 76px 0 0 0;
                z-index: 10;
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }

            .chat-section.active {
                transform: translateX(0);
            }
        }

        /* ========== Scrollbar Styling ========== */
        .conversations-list::-webkit-scrollbar,
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }

        .conversations-list::-webkit-scrollbar-thumb,
        .chat-messages::-webkit-scrollbar-thumb {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 3px;
        }

        .conversations-list::-webkit-scrollbar-track,
        .chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }

        /* ========== Modal Styles ========== */
        #messageActionModal .modal-dialog {
            margin: 0;
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
        }

        #messageActionModal .modal-content {
            border-radius: 16px 16px 0 0;
            border: none;
            box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.15);
        }

        .message-action-btn {
            border-radius: 20px;
            padding: 10px 16px;
            margin-bottom: 8px;
        }

        @media (min-width: 768px) {
            #messageActionModal .modal-dialog {
                position: static;
                margin: 1.75rem auto;
            }
        }

        /* ========== Animations ========== */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .conversation-item,
        .message {
            animation: fadeIn 0.2s ease;
        }
    """
    
    # Replace CSS
    new_content = content[:style_start] + new_css + '\n    ' + content[style_end:]
    
    # Fix HTML structure to have conversations panel wrapper
    # Add wrapper around conversations list
    new_content = new_content.replace(
        '    <div class="messages-container">',
        '''    <div class="messages-container">
        <div id="conversationsPanel">'''
    )
    
    new_content = new_content.replace(
        '        </div>\n\n        <!-- قسم الدردشة -->',
        '''        </div>
        </div>

        <!-- قسم الدردشة -->'''
    )
    
    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("تم تحديث التصميم بنجاح!")
    print("تم تطبيق تصميم WhatsApp Web")
    print("التصميم متجاوب مع جميع الشاشات")

if __name__ == "__main__":
    update_messages_whatsapp_style()
