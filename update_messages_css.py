#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to update company_messages.html with modern WhatsApp-style design
while preserving all existing functionality
"""

import re

def update_messages_html():
    file_path = r"e:\موقع المخزن\company_messages.html"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update 1: Messages container with glassmorphism
    content = re.sub(
        r'(\.messages-container \{[^}]+max-width: 800px;[^}]+margin: 20px auto;[^}]+background:)[^;]+(;[^}]+border-radius:)[^;]+(;[^}]+box-shadow:)[^;]+(;[^}]+overflow: hidden;[^}]+position: relative;[^}]+display: flex;[^}]+flex-direction: column;)',
        r'\1 var(--card-bg)\2 24px\3 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 1px rgba(102, 126, 234, 0.3)\4\n            backdrop-filter: blur(20px);\n            border: 1px solid rgba(255, 255, 255, 0.1);',
        content,
        flags=re.DOTALL
    )
    
    # Update 2: Messages header with primary gradient
    content = re.sub(
        r'(\.messages-header \{[^}]+background:)[^;]+(;)',
        r'\1 var(--primary-gradient)\2\n            border-bottom: 1px solid rgba(255, 255, 255, 0.1);\n            backdrop-filter: blur(10px);',
        content
    )
    
    # Update 3: Conversation items with modern hover
    content = re.sub(
        r'(\.conversation-item:hover \{[^}]+background-color:)[^;]+(;[^}]*\})',
        r'\1 linear-gradient(90deg, rgba(102, 126, 234, 0.08) 0%, transparent 100%)\2\n            transform: translateX(-3px);',
        content
    )
    
    # Update 4: Active conversation with gradient
    content = re.sub(
        r'(\.conversation-item\.active \{[^}]+background-color:)[^;]+(;[^}]+border-right:)[^;]+(;[^}]*\})',
        r'\1 var(--active-bg)\2 4px solid var(--accent-color)\3',
        content
    )
    
    # Update 5: Avatar with primary gradient and shadow
    content = re.sub(
        r'(\.avatar \{[^}]+width: 46px;[^}]+height: 46px;[^}]+border-radius: 50%;[^}]+background:)[^;]+(;[^}]+display: flex;[^}]+align-items: center;[^}]+justify-content: center;[^}]+color: white;[^}]+font-weight: bold;[^}]+font-size: 18px;[^}]+overflow: hidden;[^}]*\})',
        r'\1 var(--primary-gradient)\2\n            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);\n            transition: transform 0.3s ease;\n            flex-shrink: 0;',
        content,
        flags=re.DOTALL
    )
    
    # Update 6: Message sent with custom gradient
    content = re.sub(
        r'(\.message\.sent \.message-content \{[^}]+background:)[^;]+(;[^}]+color:)[^;]+(;[^}]*\})',
        r'\1 var(--message-sent-gradient)\2 white\3\n            box-shadow: 0 4px 15px rgba(37, 211, 102, 0.3);\n            animation: messageSlideIn 0.3s ease-out;',
        content
    )
    
    # Update 7: Message received with border
    content = re.sub(
        r'(\.message\.received \.message-content \{[^}]+background:)[^;]+(;[^}]+border:)[^;]+(;[^}]+color:)[^;]+(;[^}]*\})',
        r'\1 var(--card-bg)\2 1px solid var(--border-color)\3 var(--text-primary)\4\n            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);',
        content
    )
    
    # Update 8: Send button with gradient and effects
    content = re.sub(
        r'(\.send-btn \{[^}]+background:)[^;]+(;[^}]+)',
        r'\1 var(--message-sent-gradient)\2\n            box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);\n            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);',
        content,
        flags=re.DOTALL
    )
    
    # Update  9: Send button hover
    content = re.sub(
        r'(\.send-btn:hover \{[^}]*transform:)[^;]+(;[^}]+box-shadow:)[^;]+(;[^}]*\})',
        r'\1 scale(1.1) rotate(5deg)\2 0 8px 25px rgba(37, 211, 102, 0.6)\3',
        content
    )
    
    # Update 10: Chat messages background
    content = re.sub(
        r'(\.chat-messages \{[^}]+flex: 1;[^}]+padding: 20px;[^}]+overflow-y: auto;[^}]+background:)[^;]+(;[^}]*\})',
        r'\1 var(--chat-bg)\2',
        content,
        flags=re.DOTALL
    )
    
    # Update 11: Add animations at the end of style section
    animations = """
        /* Animations */
        @keyframes messageSlideIn {
            from {
                opacity: 0;
                transform: translateY(10px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        @keyframes sendPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(0.95); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .send-btn:active {
            animation: sendPulse 0.3s ease-out;
        }
        
        .avatar:hover {
            transform: scale(1.05);
        }
        
        .conversation-item {
            animation: fadeIn 0.3s ease-out;
        }"""
    
    # Insert animations before closing </style> tag
    content = re.sub(r'(\s*</style>)', animations + r'\n\1', content)
    
    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully updated company_messages.html")
    print("🎨 Applied modern WhatsApp-style design with site colors")
    print("✨ All existing features preserved")

if __name__ == "__main__":
    update_messages_html()
