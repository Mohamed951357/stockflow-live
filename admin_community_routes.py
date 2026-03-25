from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime
from models import db, CommunityPost, PostComment, Company
import json

admin_community_bp = Blueprint('admin_community', __name__)

@admin_community_bp.route('/admin/community')
@login_required
def admin_community():
    """Admin panel for managing community posts"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    posts = CommunityPost.query.order_by(CommunityPost.created_at.desc()).all()
    return render_template('admin_community.html', posts=posts)

@admin_community_bp.route('/admin/community/toggle_post/<int:post_id>')
@login_required
def toggle_post(post_id):
    """Toggle community post active status"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    try:
        post = CommunityPost.query.get_or_404(post_id)
        post.is_active = not post.is_active
        db.session.commit()
        
        status = 'مفعل' if post.is_active else 'معطل'
        flash(f'تم تغيير حالة المنشور إلى {status}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء تغيير حالة المنشور', 'error')
    
    return redirect(url_for('admin_community.admin_community'))

@admin_community_bp.route('/admin/community/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    """Delete community post"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    try:
        post = CommunityPost.query.get_or_404(post_id)
        
        # Delete all comments for this post
        PostComment.query.filter_by(post_id=post_id).delete()
        
        # Delete the post
        db.session.delete(post)
        db.session.commit()
        
        flash('تم حذف المنشور بنجاح', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء حذف المنشور', 'error')
    
    return redirect(url_for('admin_community.admin_community'))

@admin_community_bp.route('/admin/community/comments/<int:post_id>')
@login_required
def admin_post_comments(post_id):
    """Admin panel for managing comments on a specific post"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    post = CommunityPost.query.get_or_404(post_id)
    comments = PostComment.query.filter_by(post_id=post_id).order_by(PostComment.created_at.desc()).all()
    
    return render_template('admin_comments.html', post=post, comments=comments)

@admin_community_bp.route('/admin/community/toggle_comment/<int:comment_id>')
@login_required
def toggle_comment(comment_id):
    """Toggle comment active status"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    try:
        comment = PostComment.query.get_or_404(comment_id)
        comment.is_active = not comment.is_active
        db.session.commit()
        
        status = 'مفعل' if comment.is_active else 'معطل'
        flash(f'تم تغيير حالة التعليق إلى {status}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء تغيير حالة التعليق', 'error')
    
    return redirect(url_for('admin_community.admin_post_comments', post_id=comment.post_id))

@admin_community_bp.route('/admin/community/delete_comment/<int:comment_id>')
@login_required
def delete_comment(comment_id):
    """Delete comment"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    try:
        comment = PostComment.query.get_or_404(comment_id)
        post_id = comment.post_id
        
        db.session.delete(comment)
        db.session.commit()
        
        flash('تم حذف التعليق بنجاح', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء حذف التعليق', 'error')
    
    return redirect(url_for('admin_community.admin_post_comments', post_id=post_id))
