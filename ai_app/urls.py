# ai_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView
from .views import (
    GLM4View, 
    GLM4VView, 
    GLMCogView, 
    CogVideoXView, 
    GLM4Voice,
    CozeChatView,
    api_docs,
    QwenChat,
    QwenChatFile,
    QwenChatToke,
    QwenOCR,
    Qwenomni,
    QwenAudio,
    FileUploadView,
    Qwenvl,
    deeskeep,
    JDDataUploadView,
    jd_data_view,
    rename_files_in_jd,
    auto_upload_files,
    save_analysis_to_file
)
from django.conf import settings
from django.conf.urls.static import static

# 移除未定义的ViewSet
# router = DefaultRouter()
# router.register(r'products', ProductViewSet)
# router.register(r'models', ModelViewSet)

urlpatterns = [
    # 将默认页面重定向到api_docs
    path('', RedirectView.as_view(pattern_name='api_docs'), name='index'),
    # 删除不存在的about视图
    # path('about/', views.about, name='about'),
    path('api-docs/', api_docs, name='api_docs'),#说明文档页面
    path('GLM-4/', GLM4View.as_view(), name='glm-4-api'),
    path('GLM-4V/', GLM4VView.as_view(), name='glm-4v-api'),
    path('GLM-Cog/', GLMCogView.as_view(), name='glm-cog-api'),
    path('GLM-CogVideo/', CogVideoXView.as_view(), name='glm-cogvideo-api'),
    path('GLM-4-Voice/', GLM4Voice.as_view(), name='glm-4-voice-api'),
    path('CozeChat/', CozeChatView.as_view(), name='coze-chat-api'),
    path('QwenChat/', QwenChat.as_view(), name='qwen-chat-api'),
    path('QwenChatFile/', QwenChatFile.as_view(), name='qwen-chat-file-api'),
    path('QwenChatToke/', QwenChatToke.as_view(), name='qwen-chat-toke-api'),
    path('QwenOCR/', QwenOCR.as_view(), name='qwen-ocr-api'),
    path('Qwenomni/', Qwenomni.as_view(), name='qwen-omni-api'),
    path('QwenAudio/', QwenAudio.as_view(), name='qwen-audio-api'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('Qwenvl/', Qwenvl.as_view(), name='qwen-vl-api'),
    path('deeskeep/', deeskeep.as_view(), name='qwen-deeskeep-api'),
    # 京东数据管理路由
    path('jd-data/', jd_data_view, name='jd_data_view'),
    path('jd-data/upload/', JDDataUploadView.as_view(), name='jd_data_upload'),
    path('rename-files/', rename_files_in_jd, name='rename-files'),
    path('auto-upload-files/', auto_upload_files, name='auto-upload-files'),
    # 添加保存分析结果到文件的路由
    path('save-analysis/', save_analysis_to_file, name='save-analysis'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 添加媒体文件服务