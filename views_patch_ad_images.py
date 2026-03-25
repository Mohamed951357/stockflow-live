# Patch for views.py - Update manage_ad_images route to handle image_type field
# Replace lines 494-502 in views.py with the following code:

                description = request.form.get('description', '').strip()
                image_type = request.form.get('image_type', 'free')  # Get image type from form, default to 'free'
                
                # Validate image_type
                if image_type not in ['free', 'premium', 'all']:
                    image_type = 'free'  # Default to 'free' if invalid value
                
                new_ad_image = AdImage(
                    filename=unique_filename,
                    original_filename=file.filename,
                    description=description if description else None,
                    image_type=image_type,  # Add the image_type field
                    uploaded_by=current_user.id,
                    is_active=True,
                    upload_date=datetime.utcnow()
                )
