from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AiAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_app'
    verbose_name = '数据及接口管理'
    verbose_name_plural = '数据及接口管理'
    
    def ready(self):
        # 导入必要的模块
        from django.contrib import admin
        from django.contrib.admin.sites import AlreadyRegistered, NotRegistered
        
        
        # 尝试将自定义用户模型显示在"认证和授权"组下
        try:

            from django.contrib.admin.sites import site

        except Exception as e:
            # 如果出现错误，记录日志但不引发异常
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"无法将CustomUser移动到'认证和授权'组: {e}")


