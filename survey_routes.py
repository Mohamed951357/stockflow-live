from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Survey, SurveyResponse, Company
import json

survey_bp = Blueprint('survey', __name__)

@survey_bp.route('/surveys')
@login_required
def surveys():
    """Display available surveys"""
    try:
        if session.get('user_type') != 'company':
            flash('غير مصرح لك بالوصول', 'error')
            return redirect(url_for('logout'))
        
        available_surveys = Survey.query.filter_by(is_active=True).all()
        return render_template('surveys.html', surveys=available_surveys)
    except Exception as e:
        flash('حدث خطأ أثناء تحميل الاستبيانات', 'error')
        return redirect(url_for('company_dashboard'))

@survey_bp.route('/survey/<int:survey_id>')
@login_required
def survey_detail(survey_id):
    """Display survey details and questions"""
    try:
        if session.get('user_type') != 'company':
            flash('غير مصرح لك بالوصول', 'error')
            return redirect(url_for('logout'))
        
        survey = Survey.query.get_or_404(survey_id)
        if not survey.is_active:
            flash('هذا الاستبيان غير متاح حالياً', 'error')
            return redirect(url_for('surveys'))
        
        # Check if user already responded
        existing_response = SurveyResponse.query.filter_by(
            survey_id=survey_id,
            company_id=current_user.id
        ).first()
        
        if existing_response:
            flash('لقد قمت بالرد على هذا الاستبيان مسبقاً', 'info')
            return redirect(url_for('surveys'))
        
        return render_template('survey.html', survey=survey)
    except Exception as e:
        flash('حدث خطأ أثناء تحميل الاستبيان', 'error')
        return redirect(url_for('surveys'))

@survey_bp.route('/submit_survey/<int:survey_id>', methods=['POST'])
@login_required
def submit_survey(survey_id):
    """Submit survey response"""
    try:
        if session.get('user_type') != 'company':
            flash('غير مصرح لك بالوصول', 'error')
            return redirect(url_for('logout'))
        
        survey = Survey.query.get_or_404(survey_id)
        
        # Check if user already responded
        existing_response = SurveyResponse.query.filter_by(
            survey_id=survey_id,
            company_id=current_user.id
        ).first()
        
        if existing_response:
            flash('لقد قمت بالرد على هذا الاستبيان مسبقاً', 'info')
            return redirect(url_for('surveys'))
        
        # Create new response
        response = SurveyResponse(
            survey_id=survey_id,
            company_id=current_user.id,
            responses=json.dumps(request.form.to_dict()),
            submitted_at=datetime.utcnow()
        )
        
        db.session.add(response)
        db.session.commit()
        
        flash('شكراً لك على مشاركتك في الاستبيان', 'success')
        return redirect(url_for('survey.survey_thank_you'))
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء إرسال الرد', 'error')
        return redirect(url_for('survey.survey_detail', survey_id=survey_id))

@survey_bp.route('/survey_thank_you')
@login_required
def survey_thank_you():
    """Thank you page after survey submission"""
    return render_template('survey_thank_you.html')

@survey_bp.route('/create_survey')
@login_required
def create_survey():
    """Create new survey (admin only)"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    return render_template('create_survey.html')

@survey_bp.route('/save_survey', methods=['POST'])
@login_required
def save_survey():
    """Save new survey (admin only)"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        questions_json = request.form.get('questions')
        
        if not all([title, description, questions_json]):
            flash('جميع الحقول مطلوبة', 'error')
            return redirect(url_for('survey.create_survey'))
        
        survey = Survey(
            title=title,
            description=description,
            questions=questions_json,
            created_by=current_user.id,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        db.session.add(survey)
        db.session.commit()
        
        flash('تم إنشاء الاستبيان بنجاح', 'success')
        return redirect(url_for('survey.admin_surveys'))
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء إنشاء الاستبيان', 'error')
        return redirect(url_for('survey.create_survey'))

@survey_bp.route('/admin/surveys')
@login_required
def admin_surveys():
    """Admin panel for managing surveys"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    surveys = Survey.query.all()
    return render_template('surveys.html', surveys=surveys, is_admin=True)

@survey_bp.route('/survey/responses/<int:survey_id>')
@login_required
def survey_responses(survey_id):
    """View survey responses (admin only)"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    survey = Survey.query.get_or_404(survey_id)
    responses = SurveyResponse.query.filter_by(survey_id=survey_id).all()
    
    # Parse responses for display
    parsed_responses = []
    for response in responses:
        company = Company.query.get(response.company_id)
        responses_data = json.loads(response.responses)
        parsed_responses.append({
            'company': company,
            'responses': responses_data,
            'submitted_at': response.submitted_at
        })
    
    return render_template('survey_responses.html', survey=survey, responses=parsed_responses)

@survey_bp.route('/toggle_survey/<int:survey_id>')
@login_required
def toggle_survey(survey_id):
    """Toggle survey active status (admin only)"""
    if session.get('user_type') != 'admin' or current_user.role != 'super':
        flash('غير مصرح لك بالوصول', 'error')
        return redirect(url_for('logout'))
    
    try:
        survey = Survey.query.get_or_404(survey_id)
        survey.is_active = not survey.is_active
        db.session.commit()
        
        status = 'مفعل' if survey.is_active else 'معطل'
        flash(f'تم تغيير حالة الاستبيان إلى {status}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء تغيير حالة الاستبيان', 'error')
    
    return redirect(url_for('survey.admin_surveys'))