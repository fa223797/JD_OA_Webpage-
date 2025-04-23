from django.contrib import admin
from .models import (
    ModelInfo, UploadedFile, JDData, JDDataDashboard,
    # 京麦商品搜索看板
    JDKeywordData, JDProductDiagnosis,
    # 京准通行业大盘
    JDOverallDashboard, JDRegionalAnalysis, JDBrandTraffic,
    JDRisingSearchWords, JDSurgingSearchWords, JDHotSearchWords,
    # 京准通其他数据
    JDCompetitionAnalysis, JDMarketingOverview, JDMatrixAnalysis,
    # 商智基本数据
    JDRealTimeData, JDTrafficData, JDTransactionData,
    # 商智内容数据
    JDContentTypeAnalysis, JDCoreContentData, JDInfluencerAnalysis,
    JDSourceAnalysis, JDContentAnalysis, JDProductAnalysis,
    # 商智产品数据
    JDProductOverview, JDInventoryData,
    # 八爪鱼和EasySpider
    JDOctopusJingmaiData, JDOctopusProductSearch, JDEasySpiderData,
    JDShopRanking
)
from constance.admin import ConstanceAdmin, Config, ConstanceForm
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponse, HttpResponseRedirect
import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.admin import UserAdmin
import logging
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .views import jd_data_view, JDDataUploadView

# 获取日志记录器
logger = logging.getLogger('ai_app')

# 自定义 Constance 的 Admin 配置
class CustomConstanceAdmin(ConstanceAdmin):
    # 定义不可编辑的配置项
    readonly_config_fields = {
        'WECHAT_APP_ID',
        'WECHAT_APP_SECRET',
        'WECHAT_MCH_ID',
        'WECHAT_MCH_KEY',
        'WECHAT_NOTIFY_URL',
    }

    def get_config_value(self, name, options, form, initial):
        config = super().get_config_value(name, options, form, initial)
        if isinstance(config, dict) and 'value' in config:
            # 移除默认值显示
            config.pop('default', None)
            # 如果是只读配置项，禁用输入
            if name in self.readonly_config_fields:
                if config.get('field'):
                    config['field'].widget.attrs['readonly'] = True
                    config['field'].widget.attrs['class'] = 'readonly-field'
            # 调整输入框宽度
            if config.get('field'):
                config['field'].widget.attrs['style'] = 'width: 50%;'
        return config

    def get_changelist_form(self, request, **kwargs):
        form = super().get_changelist_form(request, **kwargs)
        field_labels = {
            'WECHAT_APP_ID': "微信小程序 AppID",
            'API_TIMEOUT': "接口超时时间（秒）",
            'GLM_API_KEY': "智谱AI API密钥",
            'COZE_API_TOKEN': "COZE API令牌",
            'COZE_BOT_ID': "COZE 机器人ID",
            'QWEN_API_KEY': "通义千问 API密钥",
            'DEFAULT_VOICE': "默认语音角色",
            'DEFAULT_VIDEO_SIZE': "默认视频尺寸",
            'DEFAULT_VIDEO_FPS': "默认视频帧率",
            'MAX_TOKENS': "最大Token数量",
        }
        
        for field_name, label in field_labels.items():
            if field_name in form.base_fields:
                form.base_fields[field_name].label = label
        return form

    class Media:
        css = {
            'all': ('admin/css/custom_constance.css',)
        }

    def has_change_permission(self, request, obj=None):
        if obj and obj.key in self.readonly_config_fields:
            return False
        return super().has_change_permission(request, obj)

    change_list_template = 'admin/constance/change_list.html'
    change_list_form = ConstanceForm
    change_list_title = '所有接口配置'

# 重新注册 Constance Config
admin.site.unregister([Config])
admin.site.register([Config], CustomConstanceAdmin)

# 修改 admin 站点标题
admin.site.site_header = '玫云科技AI管理后台'
admin.site.site_title = '系统管理'
admin.site.index_title = '系统管理'
admin.site.empty_value_display = '无数据'#空数据显示内容

# 注册上传文件 - 重命名为"多媒体资料"
@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'file_type', 'file_size', 'mime_type', 'upload_time', 'uploader')
    list_filter = ('file_type', 'upload_time', 'uploader')
    search_fields = ('file_name', 'uploader')
    
    def file_size_display(self, obj):
        """显示文件大小，带单位"""
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.2f} KB"
        else:
            return f"{size/(1024*1024):.2f} MB"
    file_size_display.short_description = "文件大小"
    
    # 修改显示的模型名称
    class Meta:
        verbose_name = '多媒体资料'
        verbose_name_plural = '多媒体资料'

# 京东数据上传
@admin.register(JDData)
class JDDataAdmin(admin.ModelAdmin):
    """京东数据管理"""
    list_display = ('category', 'subcategory', 'upload_date')
    list_filter = ('category', 'subcategory', 'upload_date')
    search_fields = ('category', 'subcategory')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload/', self.admin_site.admin_view(JDDataUploadView.as_view()), name='jd-data-upload'),
            path('batch_upload/', self.admin_site.admin_view(JDDataUploadView.as_view()), name='jd-batch-upload'),
            path('confirm_upload/', self.admin_site.admin_view(JDDataUploadView.as_view()), name='jd-confirm-upload'),
            path('logs/', self.admin_site.admin_view(self.view_logs), name='jd-data-logs'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """重定向到自定义上传页面"""
        return redirect('admin:jd-data-upload')
    
    def view_logs(self, request):
        """查看上传日志"""
        from django.http import HttpResponse
        import os
        
        # 找到日志文件位置
        log_path = os.path.join(settings.BASE_DIR, 'logs', 'ai_app.log')
        if not os.path.exists(log_path):
            return HttpResponse("找不到日志文件，请检查日志配置。", content_type="text/plain; charset=utf-8")
        
        # 读取日志文件的最后500行
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                # 读取所有行，但只保留最后500行
                lines = f.readlines()
                tail_lines = lines[-500:] if len(lines) > 500 else lines
                # 筛选出与JD数据相关的日志
                jd_logs = [line for line in tail_lines if 'jd' in line.lower() or '京东' in line]
                log_content = ''.join(jd_logs)
        except Exception as e:
            log_content = f"读取日志文件时出错: {str(e)}"
        
        # 添加查看日志的按钮到管理员界面
        response = HttpResponse(log_content, content_type="text/plain; charset=utf-8")
        response['Content-Disposition'] = 'inline; filename=jd_data_logs.txt'
        return response

    class Meta:
        verbose_name = '京东数据'
        verbose_name_plural = '京东数据'

# 京麦数据看板
@admin.register(JDDataDashboard)
class JDDataDashboardAdmin(admin.ModelAdmin):
    """京麦数据看板管理"""
    list_display = ('category', 'subcategory', 'upload_date')
    list_filter = ('category', 'subcategory', 'upload_date')
    search_fields = ('category', 'subcategory', 'search_keyword', 'main_exposure_product')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='jd-data-dashboard'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """处理京麦数据看板视图"""
        return jd_data_view(request)
    
    def changelist_view(self, request, extra_context=None):
        """重定向到自定义看板页面"""
        return redirect('admin:jd-data-dashboard')

    class Meta:
        verbose_name = '京东数据看板'
        verbose_name_plural = '京东数据看板'

# 以下模型都不注册到admin中，实现隐藏效果
# 原有的注册代码被注释或删除

# 这些类保留但不注册
class JDInfluencerAnalysisAdmin(admin.ModelAdmin):
    list_display = ['date', 'influencer', 'guide_detail_visitors', 'guide_cart_users', 'daily_guide_order_amount', 'daily_guide_order_count', 'upload_date']
    list_filter = ['date', 'influencer']
    search_fields = ['date', 'influencer', 'influencer_name']

class JDSourceAnalysisAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'detail_visitors', 'guide_cart_users', 'upload_date')
    list_filter = ('upload_date',)
    search_fields = ('source',)

class JDContentAnalysisAdmin(admin.ModelAdmin):
    list_display = ('date', 'content_name', 'content_type', 'influencer_name', 'upload_date')
    list_filter = ('upload_date', 'content_type')
    search_fields = ('content_name', 'influencer_name')

class JDProductAnalysisAdmin(admin.ModelAdmin):
    list_display = ('time', 'dimension', 'upload_date')
    list_filter = ('upload_date',)
    search_fields = ('dimension',)

class JDProductOverviewAdmin(admin.ModelAdmin):
    list_display = ('upload_date',)
    list_filter = ('upload_date',)

class JDEasySpiderDataAdmin(admin.ModelAdmin):
    list_display = ('activity_name', 'activity_type', 'remaining_time', 'upload_date')
    list_filter = ('upload_date', 'activity_type')
    search_fields = ('activity_name',)

class JDOctopusProductSearchAdmin(admin.ModelAdmin):
    list_display = ('search_keyword', 'product_name', 'price', 'shop_name', 'upload_date')
    list_filter = ('upload_date',)
    search_fields = ('search_keyword', 'product_name', 'shop_name')

# 确保ModelInfo不在admin显示
"""
@admin.register(ModelInfo)
class ModelInfoAdmin(admin.ModelAdmin):
    list_display = ('model', 'name', 'type', 'context_summary', 'cost_summary', 'api_endpoint')
    list_filter = ('type',)
    search_fields = ('model', 'name', 'context')
    
    def context_summary(self, obj):
        return obj.context[:50] + '...' if len(obj.context) > 50 else obj.context
    context_summary.short_description = "模型描述"
    
    def cost_summary(self, obj):
        return obj.cost[:30] + '...' if len(obj.cost) > 30 else obj.cost
    cost_summary.short_description = "费用说明"
"""

# 这里删除JDShopRanking和JDOctopusJingmaiData的注册代码
# 保留导入但不注册，这样可以防止404错误同时不在admin中显示这些模型
