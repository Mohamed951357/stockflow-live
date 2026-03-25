from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime
from models import db, CommunityPost, PostComment, Company
import json

community_bp = Blueprint('community', __name__)

@community_bp.route('/community')
@login_required
def community():
    """Display community posts"""
    try:
        if session.get('user_type') != 'company':
            flash('غير مصرح لك بالوصول', 'error')
            return redirect(url_for('logout'))
        
        posts = CommunityPost.query.filter_by(is_active=True).order_by(CommunityPost.created_at.desc()).all()
        return render_template('community.html', posts=posts)
    except Exception as e:
        flash('حدث خطأ أثناء تحميل المجتمع', 'error')
        return redirect(url_for('company_dashboard'))

@community_bp.route('/community/post/<int:post_id>')
@login_required
def view_post(post_id):
    """View community post details"""
    try:
        if session.get('user_type') != 'company':
            flash('غير مصرح لك بالوصول', 'error')
            return redirect(url_for('logout'))
        
        post = CommunityPost.query.get_or_404(post_id)
        comments = PostComment.query.filter_by(post_id=post_id, is_active=True).order_by(PostComment.created_at.asc()).all()
        
        return render_template('community_post.html', post=post, comments=comments)
    except Exception as e:
        flash('حدث خطأ أثناء تحميل المنشور', 'error')
        return redirect(url_for('community.community'))

@community_bp.route('/community/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    """Add comment to community post"""
    try:
        if session.get('user_type') != 'company':
            flash('غير مصرح لك بالوصول', 'error')
            return redirect(url_for('logout'))
        
        content = request.form.get('content', '').strip()
        if not content:
            flash('محتوى التعليق مطلوب', 'error')
            return redirect(url_for('community.view_post', post_id=post_id))
        
        post = CommunityPost.query.get_or_404(post_id)
        
        comment = PostComment(
            post_id=post_id,
            company_id=current_user.id,
            content=content,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        db.session.add(comment)
        db.session.commit()
        
        flash('تم إضافة التعليق بنجاح', 'success')
        return redirect(url_for('community.view_post', post_id=post_id))
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء إضافة التعليق', 'error')
        return redirect(url_for('community.view_post', post_id=post_id))