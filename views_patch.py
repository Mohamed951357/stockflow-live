# views_patch.py - إصلاح مشكلة حذف المستخدم
# هذا الملف يحتوي على الكود المطلوب إضافته لملف views.py

# 1. تحديث import statement (استبدال السطور 23-27 في views.py):
UPDATED_IMPORTS = """
from models import (
    db, Admin, Company, ProductFile, ProductItem, ProductStockHistory,
    Appointment, Notification, NotificationRead, SearchLog, FavoriteProduct, SystemSetting,
    AdImage, CommunityMessage, AppDownloadLog, TobyRequestReport,
    CommunityPost, PostLike, PostComment, PostView, CommunityNotification, PostReport
)
"""

# 2. الكود المطلوب إضافته في delete_user function (بعد السطر 2649):
DELETE_USER_COMMUNITY_CLEANUP = """
            # حذف منشورات المجتمع والبيانات المرتبطة
            # حذف الإبلاغات المرتبطة بمنشورات الشركة
            PostReport.query.filter(PostReport.post_id.in_(
                db.session.query(CommunityPost.id).filter_by(company_id=user_id)
            )).delete(synchronize_session=False)

            # حذف الإشعارات المرتبطة بمنشورات الشركة
            CommunityNotification.query.filter(CommunityNotification.post_id.in_(
                db.session.query(CommunityPost.id).filter_by(company_id=user_id)
            )).delete(synchronize_session=False)

            # حذف المشاهدات والتعليقات والإعجابات
            PostView.query.filter(PostView.post_id.in_(
                db.session.query(CommunityPost.id).filter_by(company_id=user_id)
            )).delete(synchronize_session=False)

            PostComment.query.filter(PostComment.post_id.in_(
                db.session.query(CommunityPost.id).filter_by(company_id=user_id)
            )).delete(synchronize_session=False)

            PostLike.query.filter(PostLike.post_id.in_(
                db.session.query(CommunityPost.id).filter_by(company_id=user_id)
            )).delete(synchronize_session=False)

            # حذف منشورات الشركة
            CommunityPost.query.filter_by(company_id=user_id).delete()

            # حذف إعجابات وتعليقات الشركة على منشورات أخرى
            PostLike.query.filter_by(company_id=user_id).delete()
            PostComment.query.filter_by(company_id=user_id).delete()
            PostView.query.filter_by(company_id=user_id).delete()
            CommunityNotification.query.filter_by(company_id=user_id).delete()
            PostReport.query.filter_by(reporter_id=user_id).delete()
"""

# 3. إضافة عداد المنشورات الجديدة لكارت مجتمع بونص فارما
# هذا الكود يجب إضافته في دالة company_dashboard في views.py

# إضافة هذا الكود بعد السطر 665 (بعد حساب average_results_per_search)
# وقبل السطر 667 (return render_template)

# حساب عدد المنشورات الجديدة منذ آخر زيارة للمجتمع
NEW_POSTS_COUNTER = """
unread_community_posts_count = 0
if current_user.last_community_visit:
    # حساب المنشورات التي تم إنشاؤها بعد آخر زيارة للمجتمع
    unread_community_posts_count = CommunityPost.query.filter(
        CommunityPost.created_at > current_user.last_community_visit,
        CommunityPost.is_active == True
    ).count()
else:
    # إذا لم تكن هناك زيارة سابقة، احسب جميع المنشورات النشطة
    unread_community_posts_count = CommunityPost.query.filter(
        CommunityPost.is_active == True
    ).count()

# إضافة المتغير الجديد لـ render_template
# في السطر 694، غير:
# average_results_per_search=average_results_per_search)
# إلى:
# average_results_per_search=average_results_per_search,
# unread_community_posts_count=unread_community_posts_count)
"""

# 4. إضافة عداد إشعارات التفاعل مع المنشورات
# هذا الكود يجب إضافته في دالة company_dashboard في views.py

# إضافة هذا الكود بعد حساب unread_community_posts_count (السطر 679):
NEW_INTERACTIONS_COUNTER = """
# حساب إشعارات التفاعل مع منشورات الشركة (الإعجابات والتعليقات)
unread_community_interactions_count = CommunityNotification.query.filter(
    CommunityNotification.company_id == current_user.id,
    CommunityNotification.is_read == False
).count()
"""

# إضافة المتغير في render_template بعد السطر 695:
NEW_INTERACTIONS_RENDER_TEMPLATE = """
                               unread_community_interactions_count=unread_community_interactions_count,
"""

# تعليمات التطبيق:
INSTRUCTIONS = """
تعليمات تطبيق الإصلاح على ملف views.py:

1. افتح ملف views.py
2. ابحث عن السطور 23-27 واستبدلها بـ UPDATED_IMPORTS
3. ابحث عن function delete_user (حوالي السطر 2636)
4. أضف DELETE_USER_COMMUNITY_CLEANUP بعد السطر:
   CommunityMessage.query.filter_by(chat_room_id=chat_room_id_to_clear).delete()
   وقبل السطر:
   db.session.delete(company)

5. ابحث عن دالة company_dashboard (حوالي السطر 665)
6. أضف NEW_POSTS_COUNTER بعد حساب average_results_per_search
   وقبل السطر return render_template

7. في السطر 694، غير:
   average_results_per_search=average_results_per_search)
   إلى:
   average_results_per_search=average_results_per_search,
   unread_community_posts_count=unread_community_posts_count)

8. أضف NEW_INTERACTIONS_COUNTER بعد حساب unread_community_posts_count (السطر 679)
9. في render_template، بعد السطر 695 (بعد unread_community_posts_count=unread_community_posts_count):
   
                               unread_community_interactions_count=unread_community_interactions_count,

هذا سيحل مشكلة خطأ NOT NULL constraint عند حذف المستخدمين.
"""

if __name__ == "__main__":
    print("=== إصلاح مشكلة حذف المستخدم ===")
    print("\n1. تحديث imports:")
    print(UPDATED_IMPORTS)
    print("\n2. كود حذف منشورات المجتمع:")
    print(DELETE_USER_COMMUNITY_CLEANUP)
    print("\n3. إضافة عداد المنشورات الجديدة:")
    print(NEW_POSTS_COUNTER)
    print("\n4. إضافة عداد إشعارات التفاعل:")
    print(NEW_INTERACTIONS_COUNTER)
    print("\n5. تعليمات التطبيق:")
    print(INSTRUCTIONS)
