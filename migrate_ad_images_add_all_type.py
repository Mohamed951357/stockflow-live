# Migration script to update existing AdImage records to support the new 'all' image type
# This script should be run after updating the models.py file

from app import app, db
from models import AdImage

def migrate_ad_images():
    """
    Migration to ensure all existing AdImage records have valid image_type values
    and optionally set some images to 'all' type for demonstration
    """
    with app.app_context():
        try:
            print("Starting AdImage migration...")
            
            # Get all AdImage records
            all_images = AdImage.query.all()
            print(f"Found {len(all_images)} ad images to check")
            
            updated_count = 0
            
            for image in all_images:
                # Check if image_type is None or invalid
                if not hasattr(image, 'image_type') or image.image_type is None:
                    image.image_type = 'free'  # Default to 'free' for existing images
                    updated_count += 1
                    print(f"Updated image {image.original_filename} to 'free' type")
                elif image.image_type not in ['free', 'premium', 'all']:
                    image.image_type = 'free'  # Reset invalid values to 'free'
                    updated_count += 1
                    print(f"Reset invalid image_type for {image.original_filename} to 'free'")
            
            # Commit changes
            if updated_count > 0:
                db.session.commit()
                print(f"Migration completed successfully! Updated {updated_count} images.")
            else:
                print("No images needed updating. Migration completed.")
                
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {str(e)}")
            raise e

if __name__ == '__main__':
    migrate_ad_images()
