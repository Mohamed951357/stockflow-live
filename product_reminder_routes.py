from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_required, current_user
from models import db, ProductReminder, Company
from datetime import datetime
from sqlalchemy import func

def register_product_reminder_routes(app):
    
    @app.route('/api/remember_product', methods=['POST'])
    @login_required
    def remember_product():
        try:
            if session.get('user_type') != 'company':
                return jsonify({'error': 'غير مصرح لك بالوصول'}), 403

            data = request.get_json()
            product_name = data.get('product_name')
            quantity = data.get('quantity')
            price = data.get('price')

            if not product_name:
                return jsonify({'error': 'اسم الصنف مطلوب'}), 400

            # Check existing reminder for this product
            existing_reminder = ProductReminder.query.filter_by(
                company_id=current_user.id,
                product_name=product_name
            ).first()

            if existing_reminder:
                # Update existing
                existing_reminder.last_quantity = quantity
                existing_reminder.last_price = price
                existing_reminder.last_search_date = datetime.utcnow()
                db.session.commit()
                return jsonify({'success': True, 'message': 'تم تحديث تذكير الصنف بنجاح'})

            # Dynamic limit: 1 for free users, 5 for premium
            is_premium = getattr(current_user, 'is_premium', False)
            max_limit = 5 if is_premium else 1
            count = ProductReminder.query.filter_by(company_id=current_user.id).count()
            if count >= max_limit:
                limit_message = (
                    'لقد وصلت للحد الأقصى (5 أصناف). هل تريد استبدال أقدم صنف؟'
                    if is_premium else
                    'لقد وصلت للحد الأقصى (صنف واحد للمشترك المجاني). هل تريد استبدال الصنف الحالي؟'
                )
                return jsonify({
                    'error': 'limit_reached',
                    'message': limit_message
                })

            # Create new reminder
            new_reminder = ProductReminder(
                company_id=current_user.id,
                product_name=product_name,
                last_quantity=quantity,
                last_price=price,
                last_search_date=datetime.utcnow()
            )
            db.session.add(new_reminder)
            db.session.commit()

            return jsonify({'success': True, 'message': 'تم حفظ تذكير الصنف بنجاح'})

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in remember_product: {str(e)}")
            return jsonify({'error': 'حدث خطأ في الخادم'}), 500

    @app.route('/api/check_remembered_products', methods=['POST'])
    @login_required
    def check_remembered_products():
        try:
            if session.get('user_type') != 'company':
                return jsonify({'error': 'Unauthorized'}), 403

            data = request.get_json()
            products_list = data.get('products', [])
            
            if not products_list:
                return jsonify({'remembered_products': []})

            product_names = [p.get('name') for p in products_list if p.get('name')]
            
            # Find matches
            reminders = ProductReminder.query.filter(
                ProductReminder.company_id == current_user.id,
                ProductReminder.product_name.in_(product_names)
            ).all()

            results = []
            for r in reminders:
                results.append({
                    'name': r.product_name,
                    'quantity': r.last_quantity,
                    'price': r.last_price,
                    'id': r.id,
                    'last_search_date': r.last_search_date.isoformat() if r.last_search_date else None
                })

            return jsonify({'remembered_products': results})

        except Exception as e:
            current_app.logger.error(f"Error in check_remembered_products: {str(e)}")
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/replace_oldest_reminder', methods=['POST'])
    @login_required
    def replace_oldest_reminder():
        try:
            if session.get('user_type') != 'company':
                return jsonify({'error': 'Unauthorized'}), 403

            data = request.get_json()
            product_name = data.get('product_name')
            quantity = data.get('quantity')
            price = data.get('price')

            # Enforce limit strictly: delete oldest if at/over limit, then upsert new
            is_premium = getattr(current_user, 'is_premium', False)
            max_limit = 5 if is_premium else 1
            current_count = ProductReminder.query.filter_by(company_id=current_user.id).count()

            if current_count >= max_limit:
                oldest = ProductReminder.query.filter_by(company_id=current_user.id)\
                    .order_by(func.coalesce(ProductReminder.last_search_date, ProductReminder.created_at).asc()).first()
                if oldest:
                    db.session.delete(oldest)
                    db.session.commit()

            # If the product already has a reminder, update it instead of creating a duplicate
            existing = ProductReminder.query.filter_by(company_id=current_user.id, product_name=product_name).first()
            if existing:
                existing.last_quantity = quantity
                existing.last_price = price
                existing.last_search_date = datetime.utcnow()
                db.session.commit()
            else:
                new_reminder = ProductReminder(
                    company_id=current_user.id,
                    product_name=product_name,
                    last_quantity=quantity,
                    last_price=price,
                    last_search_date=datetime.utcnow()
                )
                db.session.add(new_reminder)
                db.session.commit()

            # Final guard: if due to race current_count exceeded, trim extras
            final_count = ProductReminder.query.filter_by(company_id=current_user.id).count()
            if final_count > max_limit:
                extra = final_count - max_limit
                to_delete = ProductReminder.query.filter_by(company_id=current_user.id)\
                    .order_by(func.coalesce(ProductReminder.last_search_date, ProductReminder.created_at).asc())\
                    .limit(extra).all()
                for r in to_delete:
                    db.session.delete(r)
                db.session.commit()

            return jsonify({'success': True, 'message': 'تم استبدال الصنف بنجاح'})

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in replace_oldest_reminder: {str(e)}")
            return jsonify({'error': 'Server error'}), 500

    @app.route('/api/delete_product_reminder', methods=['POST'])
    @login_required
    def delete_product_reminder():
        try:
            if session.get('user_type') != 'company':
                return jsonify({'error': 'Unauthorized'}), 403

            data = request.get_json()
            reminder_id = data.get('id')
            product_name = data.get('product_name') # Fallback if id not provided

            if reminder_id:
                reminder = ProductReminder.query.filter_by(id=reminder_id, company_id=current_user.id).first()
            elif product_name:
                reminder = ProductReminder.query.filter_by(product_name=product_name, company_id=current_user.id).first()
            else:
                return jsonify({'error': 'Missing identifier'}), 400

            if reminder:
                db.session.delete(reminder)
                db.session.commit()
                return jsonify({'success': True, 'message': 'تم حذف التذكير'})
            
            return jsonify({'error': 'Not found'}), 404

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in delete_product_reminder: {str(e)}")
            return jsonify({'error': 'Server error'}), 500
