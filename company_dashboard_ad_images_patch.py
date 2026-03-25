# Patch for views.py - Update company_dashboard route to filter ad images by type
# Replace line 655 in views.py with the following code:

        # Get ad images based on company premium status and image type
        if current_user.is_premium:
            # Premium companies see: premium images, all images, and free images
            ad_images = AdImage.query.filter(
                AdImage.is_active == True,
                AdImage.image_type.in_(['premium', 'all', 'free'])
            ).order_by(AdImage.upload_date.desc()).all()
        else:
            # Free companies see: free images and all images only
            ad_images = AdImage.query.filter(
                AdImage.is_active == True,
                AdImage.image_type.in_(['free', 'all'])
            ).order_by(AdImage.upload_date.desc()).all()
