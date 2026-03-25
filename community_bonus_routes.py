from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Company, CommunityPost, PostComment, CommunityNotification, PostView
from datetime import datetime
import json

# Create blueprint
community_bonus_bp = Blueprint('community_bonus', __name__)

@community_bonus_bp.route('/community_bonus')
@login_required
def community_bonus():
    """Main community bonus page"""
    if session.get('user_type') != 'company':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    return render_template('community_bonus.html')

@community_bonus_bp.route('/community_bonus/get_posts')
@login_required
def get_posts():
    """Get community posts with filtering"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    filter_type = request.args.get('filter', 'all')
    
    try:
        query = CommunityPost.query.filter_by(is_active=True)
        
        if filter_type == 'my_posts':
            query = query.filter_by(company_id=current_user.id)
        elif filter_type == 'liked':
            # This would require a join with likes table - simplified for now
            pass
        
        posts = query.order_by(CommunityPost.created_at.desc()).all()
        
        posts_data = []
        for post in posts:
            company = post.company
            # Check if current user liked this post
            user_liked = False
            if company:
                user_liked = any(like.company_id == current_user.id for like in post.likes)
            
            posts_data.append({
                'id': post.id,
                'company_name': company.company_name if company else 'Unknown',
                'content': post.content,
                'image_url': post.image_url if hasattr(post, 'image_url') else None,
                'created_at': post.created_at.strftime('%Y-%m-%d %H:%M'),
                'likes': post.likes_count,  # Frontend expects 'likes' not 'likes_count'
                'likes_count': post.likes_count,
                'comments_count': len(post.comments),
                'views': post.views_count,  # Frontend expects 'views' not 'views_count'
                'views_count': post.views_count,
                'user_liked': user_liked,  # Frontend expects 'user_liked' not 'is_liked'
                'is_liked': user_liked,
                'company_id': post.company_id,
                'is_pinned': post.is_pinned if hasattr(post, 'is_pinned') else False,
                'is_anonymous': post.is_anonymous if hasattr(post, 'is_anonymous') else False,
                'is_premium': company.is_premium if company and hasattr(company, 'is_premium') else False,
                'avatar': company.avatar if company and hasattr(company, 'avatar') else 'male-1'
            })
        
        return jsonify({'posts': posts_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/create_post', methods=['POST'])
@login_required
def create_post():
    """Create a new community post"""
    if not hasattr(current_user, 'company_name'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        content = (request.form.get('content') or '').strip()
        is_anonymous_raw = request.form.get('is_anonymous')
        is_anonymous = False
        if isinstance(is_anonymous_raw, str):
            is_anonymous = is_anonymous_raw.lower() in {'1', 'true', 'yes', 'on'}
        elif isinstance(is_anonymous_raw, bool):
            is_anonymous = is_anonymous_raw
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        if len(content) > 500:
            return jsonify({'error': 'Content too long'}), 400
        
        new_post = CommunityPost(
            company_id=current_user.id,
            content=content,
            created_at=datetime.utcnow(),
            is_active=True,
            likes_count=0,
            views_count=0,
            is_anonymous=is_anonymous
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        return jsonify({'success': True, 'post_id': new_post.id})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/get_companies')
@login_required
def get_companies():
    """Get list of companies for admin"""
    if session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        companies = Company.query.filter_by(is_active=True).all()
        companies_data = [{
            'id': company.id,
            'company_name': company.company_name
        } for company in companies]
        
        return jsonify({'companies': companies_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/get_company_count')
@login_required
def get_company_count():
    """Get count of active companies"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        count = Company.query.filter_by(is_active=True).count()
        return jsonify({'success': True, 'count': count})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/record_view/<int:post_id>', methods=['POST'])
@login_required
def record_view(post_id):
    """Record a view for a post"""
    if not hasattr(current_user, 'company_name'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        post = CommunityPost.query.get_or_404(post_id)
        exists = PostView.query.filter_by(post_id=post_id, company_id=current_user.id).first()
        if not exists:
            view = PostView(post_id=post_id, company_id=current_user.id)
            db.session.add(view)
            post.views_count = (post.views_count or 0) + 1
            db.session.commit()
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/toggle_like', methods=['POST'])
@login_required
def toggle_like():
    """Toggle like for a post"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        post_id = request.json.get('post_id')
        post = CommunityPost.query.get_or_404(post_id)
        
        # Check if user already liked the post
        from models import PostLike
        existing_like = PostLike.query.filter_by(
            post_id=post_id,
            company_id=current_user.id
        ).first()
        
        liked = False
        if existing_like:
            # Unlike
            db.session.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
            liked = False
        else:
            # Like
            new_like = PostLike(
                post_id=post_id,
                company_id=current_user.id
            )
            db.session.add(new_like)
            post.likes_count = (post.likes_count or 0) + 1
            liked = True
            
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'likes_count': post.likes_count,
            'liked': liked
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/get_comments/<int:post_id>')
@login_required
def get_comments(post_id):
    """Get comments for a post"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        post = CommunityPost.query.get_or_404(post_id)
        comments = PostComment.query.filter_by(post_id=post_id, is_active=True).order_by(PostComment.created_at.desc()).all()
        
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'company_name': comment.company.company_name if comment.company else 'Unknown',
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                'company_id': comment.company_id,
                'can_delete': comment.company_id == current_user.id
            })
        
        return jsonify({'comments': comments_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/add_comment', methods=['POST'])
@login_required
def add_comment():
    """Add a comment to a post"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        post_id = request.json.get('post_id')
        content = request.json.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        post = CommunityPost.query.get_or_404(post_id)
        
        new_comment = PostComment(
            post_id=post_id,
            company_id=current_user.id,
            content=content,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        db.session.add(new_comment)
        db.session.commit()
        
        return jsonify({'success': True, 'comment_id': new_comment.id})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/delete_comment/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        comment = PostComment.query.get_or_404(comment_id)
        
        # Check if user owns the comment
        if comment.company_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        comment.is_active = False
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/delete_post/<int:post_id>', methods=['DELETE', 'POST'])
@login_required
def delete_post(post_id):
    """Delete a post (soft delete)"""
    is_admin = (session.get('user_type') == 'admin')
    if not is_admin and not hasattr(current_user, 'company_name'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        post = CommunityPost.query.get_or_404(post_id)
        
        # Check if the user owns the post or is admin
        if post.company_id != getattr(current_user, 'id', None) and not is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        post.is_active = False
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/report_post/<int:post_id>', methods=['POST'])
@login_required
def report_post(post_id):
    """Report a post"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        post = CommunityPost.query.get_or_404(post_id)
        
        # In a real implementation, you would create a report record
        # For now, we'll just return success
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bonus_bp.route('/community_bonus/get_notification_count')
@login_required
def get_notification_count():
    """Get notification count for the current user"""
    if session.get('user_type') != 'company':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Count unread notifications
        count = CommunityNotification.query.filter_by(
            company_id=current_user.id,
            is_read=False
        ).count()
        
        return jsonify({'count': count})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
