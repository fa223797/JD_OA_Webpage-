# views.py
from django.shortcuts import render, redirect
from rest_framework.views import APIView  # 导入DRF的APIView类，用于创建API视图
from rest_framework.response import Response  # 导入DRF的Response对象，用于构建HTTP响应
from rest_framework import status  # 导入DRF的状态码模块，便于返回标准HTTP状态码
import requests  # 导入requests库，用于发送HTTP请求
import json  # 导入json库，用于处理JSON数据
import base64  # 导入base64库，用于处理Base64编码
from zhipuai import ZhipuAI  # 导入ZhipuAI库，用于调用智谱AI的API
from cozepy import Coze, TokenAuth, Message, ChatEventType
from dashscope import Generation, Application 
from django.http  import StreamingHttpResponse, JsonResponse 
from openai import OpenAI
from pathlib import Path
import dashscope
import os
import logging
from rest_framework.decorators import action
import traceback
from constance import config
import mimetypes
from rest_framework.parsers import MultiPartParser
from ai_app.models import ModelInfo, UploadedFile, JDData, JDKeywordData, JDProductDiagnosis, JDOverallDashboard, JDRegionalAnalysis, JDBrandTraffic, JDRisingSearchWords, JDSurgingSearchWords, JDHotSearchWords, JDCompetitionAnalysis, JDMarketingOverview, JDMatrixAnalysis, JDRealTimeData, JDTrafficData, JDTransactionData, JDContentTypeAnalysis, JDCoreContentData, JDInfluencerAnalysis, JDSourceAnalysis, JDContentAnalysis, JDProductAnalysis, JDProductOverview, JDInventoryData, JDOctopusJingmaiData, JDOctopusProductSearch, JDEasySpiderData, JDShopRanking
from django.db.models import Q
import pandas as pd
import io
import chardet
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.generic import TemplateView
from django.db import models
from .models import (
    JDKeywordData, JDProductDiagnosis, JDOverallDashboard, JDRegionalAnalysis,
    JDBrandTraffic, JDRisingSearchWords, JDSurgingSearchWords, JDHotSearchWords,
    JDCompetitionAnalysis, JDMarketingOverview, JDMatrixAnalysis,
    JDRealTimeData, JDTrafficData, JDTransactionData,
    JDContentTypeAnalysis, JDCoreContentData, JDInfluencerAnalysis,
    JDSourceAnalysis, JDContentAnalysis, JDProductAnalysis,
    JDProductOverview, JDInventoryData,
    JDOctopusJingmaiData, JDOctopusProductSearch, JDEasySpiderData,
    JDDataDashboard, JDData
)
import uuid
import tempfile
from datetime import datetime, timedelta  # 添加这一行
from django.views.decorators.http import require_POST


logger = logging.getLogger(__name__)

# ===============后台功能类模块===============
# # 说明文档页面
def api_docs(request):
    """API文档页面"""
    models = ModelInfo.objects.all()
    return render(request, 'api_docs.html', {'models': models})

# 媒体资料管理
class FileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        # 获取上传的文件
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            logger.warning("文件上传失败：未提供文件", extra={'user': request.user.username})
            return Response({'error': '未提供文件'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 获取用户ID或用户名
            user_id = request.data.get('user_id')
            username = request.data.get('username')
            if user_id or username:
                # 通过API上传，使用传入的用户ID或用户名
                pass  # 删除的代码块
            else:
                # 通过网页上传，使用当前登录用户
                if not request.user.is_authenticated:
                    return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
                uploader = request.user

            # 创建UploadedFile实例
            uploaded_file_instance = UploadedFile(
                file=uploaded_file,
                uploader=uploader
            )
            
            # 自动填充其他字段
            uploaded_file_instance.file_name = os.path.basename(uploaded_file.name)
            uploaded_file_instance.file_size = uploaded_file.size
            
            # 自动判断MIME类型
            mime_type, _ = mimetypes.guess_type(uploaded_file.name)
            uploaded_file_instance.mime_type = mime_type or 'application/octet-stream'
            
            # 保存实例，save方法会自动处理文件类型分类
            uploaded_file_instance.save()
            
            # 添加成功日志
            logger.info(
                f"文件上传成功 | 用户:{uploader.username} | 文件名:{uploaded_file.name} "
                f"| 类型:{uploaded_file_instance.file_type} | 大小:{uploaded_file.size}字节",
                extra={
                    'user': uploader.username,
                    'file_name': uploaded_file.name,
                    'file_type': uploaded_file_instance.file_type,
                    'file_size': uploaded_file.size
                }
            )
            
            # 返回成功响应
            return Response({
                'id': uploaded_file_instance.id,
                'file_name': uploaded_file_instance.file_name,
                'file_type': uploaded_file_instance.file_type,
                'file_size': uploaded_file_instance.file_size,
                'mime_type': uploaded_file_instance.mime_type,
                'upload_time': uploaded_file_instance.upload_time,
                'file_url': uploaded_file_instance.file.url,
                'uploader_id': uploader.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # 添加错误日志（包含堆栈跟踪）
            logger.error(
                f"文件上传失败: {str(e)} | 用户:{getattr(uploader, 'username', '未知')}",
                exc_info=True,
                extra={
                    'user': getattr(uploader, 'username', '未知'),
                    'file_name': uploaded_file.name if uploaded_file else None,
                    'error': str(e)
                }
            )
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ==========================京东数据展示页面=======================
@login_required
def jd_data_view(request):
    """京东数据看板视图"""
    # 获取筛选参数
    category = request.GET.get('category', '')
    subcategory = request.GET.get('subcategory', '')
    
    # 获取所有类别和子类别
    categories = JDData.objects.values_list('category', flat=True).distinct()
    subcategories = JDData.objects.values_list('subcategory', flat=True).distinct()
    
    # 准备所有表格数据
    tables_data = {}
    tables_fields = {}
    tables_verbose_names = {}
    
    # 获取所有模型的数据
    from django.apps import apps
    from django.db import models
    
    # 模型与类别子类别的映射关系
    model_category_map = {
        'JDKeywordData': {'category': '京麦商品搜索看板', 'subcategory': '热搜词'},
        'JDProductDiagnosis': {'category': '京麦商品搜索看板', 'subcategory': '商品诊断'},
        'JDOverallDashboard': {'category': '京准通行业大盘', 'subcategory': '整体看板'},
        'JDRegionalAnalysis': {'category': '京准通行业大盘', 'subcategory': '地域分析'},
        'JDBrandTraffic': {'category': '京准通行业大盘', 'subcategory': '品牌流量'},
        'JDRisingSearchWords': {'category': '京准通行业大盘', 'subcategory': '新秀搜索词排行'},
        'JDSurgingSearchWords': {'category': '京准通行业大盘', 'subcategory': '飙升搜索词排行'},
        'JDHotSearchWords': {'category': '京准通行业大盘', 'subcategory': '热点搜索词排行'},
        'JDCompetitionAnalysis': {'category': '京准通其他数据', 'subcategory': '竞争分析'},
        'JDMarketingOverview': {'category': '京准通其他数据', 'subcategory': '营销概况'},
        'JDMatrixAnalysis': {'category': '京准通其他数据', 'subcategory': '矩阵分析'},
        'JDRealTimeData': {'category': '商智基本数据', 'subcategory': '实时'},
        'JDTrafficData': {'category': '商智基本数据', 'subcategory': '流量'},
        'JDTransactionData': {'category': '商智基本数据', 'subcategory': '交易'},
        'JDContentTypeAnalysis': {'category': '商智内容数据', 'subcategory': '类型分析'},
        'JDCoreContentData': {'category': '商智内容数据', 'subcategory': '核心数据'},
        'JDInfluencerAnalysis': {'category': '商智内容数据', 'subcategory': '达人分析'},
        'JDSourceAnalysis': {'category': '商智内容数据', 'subcategory': '来源分析'},
        'JDContentAnalysis': {'category': '商智内容数据', 'subcategory': '内容分析'},
        'JDProductAnalysis': {'category': '商智内容数据', 'subcategory': '商品分析'},
        'JDProductOverview': {'category': '商智产品数据', 'subcategory': '商品概况'},
        'JDInventoryData': {'category': '商智产品数据', 'subcategory': '库存'},
        'JDOctopusJingmaiData': {'category': '八爪鱼', 'subcategory': '京麦采集'},
        'JDOctopusProductSearch': {'category': '八爪鱼', 'subcategory': '京东商品搜索'},
        'JDShopRanking': {'category': '八爪鱼', 'subcategory': '京麦采集'},
        'JDEasySpiderData': {'category': 'EasySpider', 'subcategory': 'Easy京麦采集'},
        'JDData': {'category': '', 'subcategory': ''}  # 通用表，默认不归属于特定类别
    }
    
    # 直接指定所有需要显示的模型
    models_to_display = [
        'JDBrandTraffic', 'JDCompetitionAnalysis', 'JDContentTypeAnalysis', 
        'JDCoreContentData', 'JDHotSearchWords', 'JDInfluencerAnalysis',
        'JDKeywordData', 'JDMarketingOverview', 'JDMatrixAnalysis',
        'JDOctopusJingmaiData', 'JDOverallDashboard', 'JDProductDiagnosis',
        'JDRealTimeData', 'JDRegionalAnalysis', 'JDRisingSearchWords',
        'JDShopRanking', 'JDSurgingSearchWords', 'JDTrafficData',
        'JDTransactionData', 'JDContentAnalysis', 'JDData', 
        'JDEasySpiderData', 'JDInventoryData', 'JDOctopusProductSearch',
        'JDProductAnalysis', 'JDProductOverview', 'JDSourceAnalysis'
    ]
    
    for model_name in models_to_display:
        try:
            # 检查模型是否符合筛选条件
            model_info = model_category_map.get(model_name, {'category': '', 'subcategory': ''})
            model_category = model_info['category']
            model_subcategory = model_info['subcategory']
            
            # 如果设置了类别筛选，但不匹配当前模型，则跳过
            if category and model_category != category:
                continue
                
            # 如果设置了子类别筛选，但不匹配当前模型，则跳过
            if subcategory and model_subcategory != subcategory:
                continue
            
            model = apps.get_model('ai_app', model_name)
            # 对于每个模型，获取最多100条记录
            data = model.objects.all()[:100]
            
            # 添加额外调试日志
            if model_name == 'JDOctopusJingmaiData':
                record_count = model.objects.count()
                logging.info(f"JDOctopusJingmaiData表中有 {record_count} 条记录")
                if record_count > 0:
                    sample = model.objects.first()
                    logging.info(f"首条记录信息: id={sample.id}, 标题={sample.title}, 上传日期={sample.upload_date}")
            
            if data:
                # 使用数据库表名作为键
                db_table = model._meta.db_table
                tables_data[db_table] = data
                
                # 获取字段名和verbose_name
                fields = []
                verbose_names = {}
                for field in model._meta.fields:
                    if not field.name.startswith('_'):  # 忽略私有字段
                        fields.append(field.name)
                        verbose_names[field.name] = field.verbose_name
                
                tables_fields[db_table] = fields
                tables_verbose_names[db_table] = verbose_names
        except (LookupError, models.ObjectDoesNotExist):
            continue
    
    context = {
        'categories': categories,
        'subcategories': subcategories,
        'selected_category': category,
        'selected_subcategory': subcategory,
        'tables_data': tables_data,
        'tables_fields': tables_fields,
        'tables_verbose_names': tables_verbose_names
    }
    
    return render(request, 'jd/jd_data_view.html', context)

def get_field_mapping_for_model(model_class):
    """获取模型的字段映射（字段名->中文显示名称）"""
    field_mapping = {}
    
    # 获取所有非系统字段
    for field in model_class._meta.fields:
        if field.name not in ['id', 'upload_date', 'uploader']:
            field_mapping[field.name] = field.verbose_name
    
    return field_mapping

def get_field_mapping(subcategory):
    """获取子类别的字段映射（字段名->中文显示名称）"""
    mapping = {
        '热搜词': {
            'search_keyword': '搜索词',
            'traffic_contribution': '流量贡献占比',
            'keyword_rank': '词下排名',
            'product_info': '商品信息',
        },
        '商品诊断': {
            'main_exposure_product': '主曝光图商品',
            'search_performance': '搜索表现总分',
            'traffic_acquisition': '流量获取力',
            'traffic_conversion': '流量承接力',
        },
        '整体看板': {
            'click_time': '点击时间',
            'impression_index': '展现指数',
            'click_index': '点击指数',
            'click_rate': '点击率',
            'cart_index': '加购指数',
            'cart_rate': '加购率',
            'conversion_rate': '转化率',
        },
        '地域分析': {
            'region_name': '地域名称',
            'impression_index': '展现指数',
            'click_rate': '点击率',
            'conversion_rate': '转化率',
        },
        '品牌流量': {
            'main_brand_name': '主品牌名称',
            'traffic_rank': '流量排名',
            'click_rate': '点击率',
            'conversion_rate': '转化率',
        },
        '新秀搜索词排行': {
            'keyword': '关键词',
            'search_index': '搜索指数',
            'competition': '竞争力',
        },
        '飙升搜索词排行': {
            'keyword': '关键词',
            'search_index': '搜索指数',
            'competition': '竞争力',
        },
        '热点搜索词排行': {
            'keyword': '关键词',
            'search_index': '搜索指数',
            'competition': '竞争力',
        },
        # 添加其他子类别...
    }
    
    return mapping.get(subcategory, {})

def get_category_fields(category):
    """根据类别获取要显示的字段和中文名称"""
    # 每个类别显示的主要字段
    fields_map = {
        '京麦商品搜索看板': ['search_keyword', 'traffic_contribution'],
        '京准通行业大盘': ['click_time', 'impression_index', 'click_rate'],
        '京准通其他数据': ['data_content'],
        '商智基本数据': ['visitor_count', 'page_views'],
        '商智内容数据': ['content_type', 'content_data'],
        '商智产品数据': ['data_content'],
        '八爪鱼': ['search_keyword', 'product_name'],
        'EasySpider': ['activity_name', 'activity_type'],
    }
    
    # 字段对应的中文名称
    names_map = {
        '京麦商品搜索看板': {
            'search_keyword': '搜索词',
            'traffic_contribution': '流量贡献占比',
        },
        '京准通行业大盘': {
            'click_time': '点击时间',
            'impression_index': '展现指数',
            'click_rate': '点击率',
        },
        '京准通其他数据': {
            'data_content': '数据内容',
        },
        '商智基本数据': {
            'visitor_count': '访客数',
            'page_views': '浏览量',
        },
        '商智内容数据': {
            'content_type': '内容类型',
            'content_data': '内容数据',
        },
        '商智产品数据': {
            'data_content': '产品数据',
        },
        '八爪鱼': {
            'search_keyword': '搜索词',
            'product_name': '商品名称',
        },
        'EasySpider': {
            'activity_name': '活动名称',
            'activity_type': '活动类型',
        },
    }
    
    return fields_map.get(category, []), names_map.get(category, {})

# ===============JD 数据功能类模块===============
# 京东数据上传处理
class JDDataUploadView(APIView):
    parser_classes = [MultiPartParser]
    
    @method_decorator(login_required)
    def get(self, request):
        """显示上传页面"""
        return render(request, 'jd/jd_data_upload.html', {
            'title': '京东数据上传',
            'subtitle': '请选择并上传京东数据文件'
        })
    
    def post(self, request):
        action_type = request.data.get('action_type')
        
        if action_type == 'batch_upload':
            return self.handle_batch_upload(request)
        elif action_type == 'confirm_upload':
            return self.handle_confirm_upload(request)
        else:
            return self.handle_normal_upload(request)
    
    def handle_normal_upload(self, request):
        """处理上传的文件"""
        category = request.POST.get('category')
        subcategory = request.POST.get('subcategory')
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file or not category or not subcategory:
            return Response({
                'status': 'error',
                'message': '请选择文件、类别和子类别'
            }, status=400)
            
        try:
            # 处理并保存数据到对应的表
            result = self._process_and_save_file(uploaded_file, category, subcategory, request.user)
            
            # 添加成功日志
            logger.info(
                f"京东数据上传成功 | 用户:{request.user.username} | 类别:{category}-{subcategory} "
                f"| 文件:{uploaded_file.name} | 导入行数:{result}",
                extra={
                    'user': request.user.username,
                    'category': category,
                    'subcategory': subcategory,
                    'file_name': uploaded_file.name,
                    'rows_imported': result
                }
            )
            
            return Response({
                'status': 'success',
                'message': f'文件上传成功！已导入 {result} 条数据。'
            })
        except UnicodeDecodeError as e:
            logger.error(
                f"文件编码错误 | 用户:{request.user.username} | 文件:{uploaded_file.name}",
                extra={
                    'user': request.user.username,
                    'file_name': uploaded_file.name,
                    'error_type': 'UnicodeDecodeError'
                }
            )
            return Response({'status': 'error', 'message': '文件编码错误...'})
        
        except ValueError as e:
            logger.error(
                f"数据格式错误 | 用户:{request.user.username} | 文件:{uploaded_file.name} | 错误:{str(e)}",
                extra={
                    'user': request.user.username,
                    'file_name': uploaded_file.name,
                    'error_type': 'ValueError',
                    'error_msg': str(e)
                }
            )
            return Response({'status': 'error', 'message': f'数据格式错误: {str(e)}'})
        
        except Exception as e:
            logger.error(
                f"京东数据上传失败 | 用户:{request.user.username} | 文件:{uploaded_file.name} | 错误类型:{type(e).__name__}",
                exc_info=True,
                extra={
                    'user': request.user.username,
                    'file_name': uploaded_file.name,
                    'error_type': type(e).__name__,
                    'error_msg': str(e)
                }
            )
            return Response({'status': 'error', 'message': f'上传失败: {str(e)}'})
    
    def _process_and_save_file(self, uploaded_file, category, subcategory, user):
        """处理上传的文件并保存到对应的表格中"""
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        
        try:
            if file_ext == '.csv':
                # 使用tempfile模块创建临时文件，适用于Windows和Linux
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.csv")
                
                # 保存上传的文件到临时文件
                with open(temp_file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # 检测文件编码
                with open(temp_file_path, 'rb') as f:
                    result = chardet.detect(f.read())
                
                # 尝试使用检测到的编码读取文件
                detected_encoding = result['encoding'] or 'gbk'  # 默认使用GBK
                logger.info(f"检测到文件编码: {detected_encoding}")
                
                try:
                    df = pd.read_csv(temp_file_path, encoding=detected_encoding)
                except UnicodeDecodeError:
                    # 如果检测到的编码不正确，尝试其他常见编码
                    encodings_to_try = ['gbk', 'gb2312', 'utf-8-sig', 'utf-8', 'latin1']
                    for encoding in encodings_to_try:
                        try:
                            df = pd.read_csv(temp_file_path, encoding=encoding)
                            logger.info(f"成功使用 {encoding} 编码读取文件")
                            break
                        except UnicodeDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"使用 {encoding} 读取时发生错误: {str(e)}")
                            continue
                    else:
                        # 如果所有编码都失败
                        raise UnicodeDecodeError("无法检测到正确的文件编码")
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                # 在文件读取成功后添加日志
                logger.info(
                    f"文件解析成功 | 用户:{user.username} | 文件类型:{file_ext} "
                    f"| 原始列:{list(df.columns)} | 总行数:{df.shape[0]}",
                    extra={
                        'user': user.username,
                        'file_type': file_ext,
                        'columns': list(df.columns),
                        'total_rows': df.shape[0]
                    }
                )
                
            elif file_ext in ['.xlsx', '.xls']:
                # Excel文件通常不受编码问题影响
                df = pd.read_excel(uploaded_file)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            # 记录原始列名以便日志
            original_columns = list(df.columns)
            logger.info(f"读取到的原始列名: {original_columns}")
            
            # 2. 根据类别和子类别保存到对应的表格中
            count = 0
            
            if category == '京麦商品搜索看板':
                if subcategory == '热搜词':
                    count = self._save_to_jd_keyword_data(df, user)
                elif subcategory == '商品诊断':
                    count = self._save_to_jd_product_diagnosis(df, user)
            elif category == '京准通行业大盘':
                if subcategory == '整体看板':
                    count = self._save_to_jd_overall_dashboard(df, user)
                elif subcategory == '地域分析':
                    count = self._save_to_jd_regional_analysis(df, user)
                elif subcategory == '品牌流量':
                    count = self._save_to_jd_brand_traffic(df, user)
                elif subcategory == '新秀搜索词排行':
                    count = self._save_to_jd_rising_search_words(df, user)
                elif subcategory == '飙升搜索词排行':
                    count = self._save_to_jd_surging_search_words(df, user)
                elif subcategory == '热点搜索词排行':
                    count = self._save_to_jd_hot_search_words(df, user)
            elif category == '京准通其他数据':
                if subcategory == '竞争分析':
                    count = self._save_to_jd_competition_analysis(df, user)
                elif subcategory == '营销概况':
                    count = self._save_to_jd_marketing_overview(df, user)
                elif subcategory == '矩阵分析':
                    count = self._save_to_jd_matrix_analysis(df, user)
            elif category == '商智基本数据':
                if subcategory == '实时':
                    count = self._save_to_jd_real_time_data(df, user)
                elif subcategory == '流量':
                    count = self._save_to_jd_traffic_data(df, user)
                elif subcategory == '交易':
                    count = self._save_to_jd_transaction_data(df, user)
            elif category == '商智内容数据':
                if subcategory == '类型分析':
                    count = self._save_to_jd_content_type_analysis(df, user)
                elif subcategory == '核心数据':
                    count = self._save_to_jd_core_content_data(df, user)
                elif subcategory == '达人分析':
                    count = self._save_to_jd_influencer_analysis(df, user)
                elif subcategory == '来源分析':
                    count = self._save_to_jd_source_analysis(df, user)
                elif subcategory == '内容分析':
                    count = self._save_to_jd_content_analysis(df, user)
                elif subcategory == '商品分析':
                    count = self._save_to_jd_product_analysis(df, user)
            elif category == '商智产品数据':
                if subcategory == '商品概况':
                    count = self._save_to_jd_product_overview(df, user)
                elif subcategory == '库存':
                    count = self._save_to_jd_inventory_data(df, user)
            elif category == '八爪鱼':
                if subcategory == '京麦采集':
                    count = self._save_to_jd_octopus_jingmai_data(df, user)
                elif subcategory == '京东商品搜索':
                    count = self._save_to_jd_octopus_product_search(df, user)
            elif category == 'EasySpider':
                if subcategory in ['Easy京麦采集', 'Easy麦采集']:
                    count = self._save_to_jd_easy_spider_data(df, user)
            
            # 同时保存到JDData通用表
            self._save_to_jd_data(df, category, subcategory, user, uploaded_file)
            
            # 返回实际保存的记录数，而不是DataFrame的行数
            return count if isinstance(count, int) else (count[0] if isinstance(count, tuple) else df.shape[0])
        
        except Exception as e:
            logger.error(f"处理文件失败: {str(e)}", exc_info=True)
            raise
    
    def _save_to_jd_data(self, df, category, subcategory, user, uploaded_file):
        """保存到JDData通用表"""
        # 保存到通用JDData表，便于检索
        jd_data = JDData(
            category=category,
            subcategory=subcategory,
        )
        
        # 不保存文件到本地，而是直接将数据保存到数据库
        # 如果是热搜词类型，保存第一条数据的关键信息
        if category == '京麦商品搜索看板' and subcategory == '热搜词' and not df.empty:
            jd_data.search_keyword = str(df.iloc[0].get('搜索词', ''))[:255]
            jd_data.traffic_contribution = str(df.iloc[0].get('流量贡献占比', ''))[:50]
            jd_data.keyword_rank = str(df.iloc[0].get('词下排名', ''))[:50]
            jd_data.product_info = str(df.iloc[0].get('商品信息', ''))
        
        # 如果是商品诊断类型，保存第一条数据的关键信息
        if category == '京麦商品搜索看板' and subcategory == '商品诊断' and not df.empty:
            jd_data.main_exposure_product = str(df.iloc[0].get('主曝光图商品', ''))
            jd_data.search_performance = str(df.iloc[0].get('搜索表现总分', ''))[:50]
            jd_data.traffic_acquisition = str(df.iloc[0].get('流量获取力', ''))[:50]
            jd_data.traffic_conversion = str(df.iloc[0].get('流量承接力', ''))[:50]
        
        jd_data.save()
        return jd_data

    # 以下是各数据类型的保存方法
    def _save_to_jd_keyword_data(self, df, user):
        """保存词下表现"""
        try:
            for _, row in df.iterrows():
                # 尝试匹配列名
                search_keyword = self._get_column_value(row, ['搜索词', '关键词'])
                traffic_contribution = self._get_column_value(row, ['流量贡献占比'])
                keyword_rank = self._get_column_value(row, ['词下排名'])
                product_info = self._get_column_value(row, ['商品信息', '商品名称'])
                
                if search_keyword:  # 至少要有搜索词
                    JDKeywordData.objects.create(
                        search_keyword=search_keyword,
                        traffic_contribution=traffic_contribution,
                        keyword_rank=keyword_rank,
                        product_info=product_info,
                        upload_date=timezone.now(),
                        uploader=user
                    )
            logger.info(
                f"词下表现保存成功 | 用户:{user.username} | 记录数:{len(df)}",
                extra={
                    'user': user.username,
                    'data_type': 'JDKeywordData',
                    'rows_processed': len(df)
                }
            )
            return True
        except Exception as e:
            logger.error(
                f"词下表现保存失败 | 用户:{user.username} | 错误:{str(e)}",
                exc_info=True,
                extra={
                    'user': user.username,
                    'data_type': 'JDKeywordData',
                    'error_msg': str(e)
                }
            )
            return False
    
    def _save_to_jd_product_diagnosis(self, df, user):
        """保存商品诊断数据"""
        try:
            for _, row in df.iterrows():
                main_exposure_product = self._get_column_value(row, ['主曝光图商品', '主曝光图商品信息'])
                search_performance = self._get_column_value(row, ['搜索表现总分', '综合得分'])
                traffic_acquisition = self._get_column_value(row, ['流量获取力'])
                traffic_conversion = self._get_column_value(row, ['流量承接力'])
                
                if main_exposure_product:  # 至少要有主曝光图商品
                    JDProductDiagnosis.objects.create(
                        main_exposure_product=main_exposure_product,
                        search_performance=search_performance,
                        traffic_acquisition=traffic_acquisition,
                        traffic_conversion=traffic_conversion,
                        upload_date=timezone.now(),
                        uploader=user
                    )
            return True
        except Exception as e:
            logger.error(f"保存商品诊断数据失败: {str(e)}", exc_info=True)
            return False
    
    def _save_to_jd_overall_dashboard(self, df, user):
        """保存整体看板数据"""
        try:
            for _, row in df.iterrows():
                click_time = self._get_column_value(row, ['点击时间'])
                impression_index = self._get_column_value(row, ['展现指数'])
                click_index = self._get_column_value(row, ['点击指数'])
                click_rate = self._get_column_value(row, ['点击率', '点击率(%)'])
                cart_index = self._get_column_value(row, ['加购指数'])
                cart_rate = self._get_column_value(row, ['加购率', '加购率(%)'])
                conversion_rate = self._get_column_value(row, ['转化率', '转化率(%)'])
                
                JDOverallDashboard.objects.create(
                    click_time=click_time,
                    impression_index=impression_index,
                    click_index=click_index,
                    click_rate=click_rate,
                    cart_index=cart_index,
                    cart_rate=cart_rate,
                    conversion_rate=conversion_rate,
                    upload_date=timezone.now(),
                    uploader=user
                )
            return True  # 确保这一行的缩进与for循环对齐
        except Exception as e:
            logger.error(f"保存整体看板数据失败: {str(e)}", exc_info=True)
            return False
    
    def _save_to_jd_regional_analysis(self, df, user):
        """保存地域分析数据"""
        try:
            for _, row in df.iterrows():
                region_name = self._get_column_value(row, ['地域名称'])
                impression_index = self._get_column_value(row, ['展现指数'])
                click_rate = self._get_column_value(row, ['点击率', '点击率(%)'])
                conversion_rate = self._get_column_value(row, ['转化率', '转化率(%)'])
                
                if region_name:  # 至少要有地域名称
                    JDRegionalAnalysis.objects.create(
                        region_name=region_name,
                        impression_index=impression_index,
                        click_rate=click_rate,
                        conversion_rate=conversion_rate,
                        upload_date=timezone.now(),
                        uploader=user
                    )
            return True
        except Exception as e:
            logger.error(f"保存地域分析数据失败: {str(e)}", exc_info=True)
            return False

    def _save_to_jd_brand_traffic(self, df, user):
        """保存品牌流量总览"""
        try:
            for _, row in df.iterrows():
                main_brand_name = self._get_column_value(row, ['主品牌名称'])
                traffic_rank = self._get_column_value(row, ['流量排名'])
                click_rate = self._get_column_value(row, ['点击率', '点击率(%)'])
                conversion_rate = self._get_column_value(row, ['转化率', '转化率(%)'])
                
                if main_brand_name:  # 至少要有主品牌名称
                    JDBrandTraffic.objects.create(
                        main_brand_name=main_brand_name,
                        traffic_rank=traffic_rank,
                        click_rate=click_rate,
                        conversion_rate=conversion_rate,
                        upload_date=timezone.now(),
                        uploader=user
                    )
            return True
        except Exception as e:
            logger.error(f"保存品牌流量总览失败: {str(e)}", exc_info=True)
            return False

    def _save_to_jd_rising_search_words(self, df, user):
        """保存新秀搜索词排行数据"""
        try:
            for _, row in df.iterrows():
                keyword = self._get_column_value(row, ['关键词'])
                search_index = self._get_column_value(row, ['搜索指数'])
                competition = self._get_column_value(row, ['竞争力'])
                
                if keyword:  # 至少要有关键词
                    JDRisingSearchWords.objects.create(
                        keyword=keyword,
                        search_index=search_index,
                        competition=competition,
                        upload_date=timezone.now(),
                        uploader=user
                    )
            return True
        except Exception as e:
            logger.error(f"保存新秀搜索词排行数据失败: {str(e)}", exc_info=True)
            return False
            
    def _save_to_jd_surging_search_words(self, df, user):
        """保存飙升搜索词排行数据"""
        try:
            for _, row in df.iterrows():
                keyword = self._get_column_value(row, ['关键词'])
                search_index = self._get_column_value(row, ['搜索指数'])
                competition = self._get_column_value(row, ['竞争力'])
                
                if keyword:  # 至少要有关键词
                    JDSurgingSearchWords.objects.create(
                        keyword=keyword,
                        search_index=search_index,
                        competition=competition,
                        upload_date=timezone.now(),
                        uploader=user
                    )
            return True
        except Exception as e:
            logger.error(f"保存飙升搜索词排行数据失败: {str(e)}", exc_info=True)
            return False
            
    def _save_to_jd_hot_search_words(self, df, user):
        """保存热点搜索词排行数据"""
        try:
            for _, row in df.iterrows():
                keyword = self._get_column_value(row, ['关键词'])
                search_index = self._get_column_value(row, ['搜索指数'])
                competition = self._get_column_value(row, ['竞争力'])
                
                if keyword:  # 至少要有关键词
                    JDHotSearchWords.objects.create(
                        keyword=keyword,
                        search_index=search_index,
                        competition=competition,
                        upload_date=timezone.now(),
                        uploader=user
                    )
            return True
        except Exception as e:
            logger.error(f"保存热点搜索词排行数据失败: {str(e)}", exc_info=True)
            return False
    
    def _save_to_jd_competition_analysis(self, df, user):
        """保存竞争分析数据"""
        try:
            logger.info(f"开始处理竞争分析数据，数据形状: {df.shape}")
            logger.info(f"列名: {df.columns.tolist()}")
            
            saved_count = 0
            current_group = None
            
            for index, row in df.iterrows():
                try:
                    # 检查是否是分组标题行
                    first_cell = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ""
                    
                    # 如果是分组标题行，更新当前组
                    if "点击时间" in first_cell:
                        if "'竞品-品牌'" in row.iloc[1]:
                            current_group = "competitor"
                            logger.info(f"发现竞品品牌组标题行: {row.iloc[0:3].tolist()}")
                            continue
                        elif "'行业-品牌'" in row.iloc[1]:
                            current_group = "industry"
                            logger.info(f"发现行业品牌组标题行: {row.iloc[0:3].tolist()}")
                            continue
                        elif "'自身-品牌'" in row.iloc[1]:
                            current_group = "self"
                            logger.info(f"发现自身品牌组标题行: {row.iloc[0:3].tolist()}")
                            continue
                    
                    # 如果没有确定分组或是空行，跳过
                    if not current_group or pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == "":
                        continue
                    
                    # 提取数据
                    click_time = row.iloc[0]
                    brand = row.iloc[1]
                    impression_count = row.iloc[2]
                    
                    # 确保数据有效
                    if pd.isna(click_time) or pd.isna(brand):
                        continue
                    
                    # 转换展现量为数字
                    try:
                        impression_count = float(impression_count) if not pd.isna(impression_count) else 0
                    except (ValueError, TypeError):
                        impression_count = 0
                    
                    # 记录处理信息
                    logger.info(f"处理第 {index+1} 行: 分组={current_group}, 时间={click_time}, 品牌={brand}, 展现量={impression_count}")
                    
                    # 创建记录
                    JDCompetitionAnalysis.objects.create(
                        click_time=click_time,
                        brand_name=brand,
                        impression_count=impression_count,
                        brand_type=current_group,  # 'competitor', 'industry', 或 'self'
                        upload_date=timezone.now(),
                        uploader=user
                    )
                    saved_count += 1
                    
                except Exception as row_error:
                    logger.error(f"处理第 {index+1} 行数据时出错: {str(row_error)}", exc_info=True)
                    continue
            
            logger.info(f"竞争分析数据处理完成，共保存 {saved_count} 条记录")
            return saved_count > 0
            
        except Exception as e:
            logger.error(f"保存竞争分析数据失败: {str(e)}", exc_info=True)
            return False
    
    def _save_to_jd_marketing_overview(self, df, user):
        """保存营销概况数据"""
        try:
            for _, row in df.iterrows():
                campaign_time = self._get_column_value(row, ['点击时间', '投放时间', '当前时间'])
                cost = self._get_column_value(row, ['花费'])
                impressions = self._get_column_value(row, ['展现数'])
                clicks = self._get_column_value(row, ['点击数'])
                avg_click_cost = self._get_column_value(row, ['平均点击成本'])
                cpm = self._get_column_value(row, ['千次展现成本'])
                click_rate = self._get_column_value(row, ['点击率', '点击率(%)'])
                total_orders = self._get_column_value(row, ['总订单行'])
                total_order_amount = self._get_column_value(row, ['总订单金额'])
                total_cart_adds = self._get_column_value(row, ['总加购数'])
                conversion_rate = self._get_column_value(row, ['转化率', '转化率(%)'])
                avg_order_cost = self._get_column_value(row, ['平均订单成本'])
                roi = self._get_column_value(row, ['投产比'])
                
                JDMarketingOverview.objects.create(
                    campaign_time=campaign_time,
                    cost=cost,
                    impressions=impressions,
                    clicks=clicks,
                    avg_click_cost=avg_click_cost,
                    cpm=cpm,
                    click_rate=click_rate,
                    total_orders=total_orders,
                    total_order_amount=total_order_amount,
                    total_cart_adds=total_cart_adds,
                    conversion_rate=conversion_rate,
                    avg_order_cost=avg_order_cost,
                    roi=roi,
                    upload_date=timezone.now(),
                    uploader=user
                )
            return True
        except Exception as e:
            logger.error(f"保存营销概况数据失败: {str(e)}", exc_info=True)
            return False
            
    def _save_to_jd_matrix_analysis(self, df, user):
        """保存矩阵分析数据"""
        try:
            for _, row in df.iterrows():
                product_line = self._get_column_value(row, ['产品线'])
                click_time = self._get_column_value(row, ['点击时间', '当前时间'])
                cost = self._get_column_value(row, ['花费'])
                impressions = self._get_column_value(row, ['展现数'])
                clicks = self._get_column_value(row, ['点击数'])
                click_rate = self._get_column_value(row, ['点击率', '点击率(%)'])
                avg_click_cost = self._get_column_value(row, ['平均点击成本'])
                cpm = self._get_column_value(row, ['千次展现成本'])
                total_orders = self._get_column_value(row, ['总订单行'])
                total_order_amount = self._get_column_value(row, ['总订单金额'])
                total_cart_adds = self._get_column_value(row, ['总加购数'])
                conversion_rate = self._get_column_value(row, ['转化率', '转化率(%)'])
                cart_rate = self._get_column_value(row, ['加购率', '加购率(%)'])
                avg_order_cost = self._get_column_value(row, ['平均订单成本'])
                roi = self._get_column_value(row, ['投产比'])
                direct_orders = self._get_column_value(row, ['直接订单行'])
                direct_order_amount = self._get_column_value(row, ['直接订单金额'])
                direct_cart_adds = self._get_column_value(row, ['直接加购数'])
                indirect_orders = self._get_column_value(row, ['间接订单行'])
                indirect_order_amount = self._get_column_value(row, ['间接订单金额'])
                indirect_cart_adds = self._get_column_value(row, ['间接加购数'])
                
                JDMatrixAnalysis.objects.create(
                    product_line=product_line,
                    click_time=click_time,
                    cost=cost,
                    impressions=impressions,
                    clicks=clicks,
                    click_rate=click_rate,
                    avg_click_cost=avg_click_cost,
                    cpm=cpm,
                    total_orders=total_orders,
                    total_order_amount=total_order_amount,
                    total_cart_adds=total_cart_adds,
                    conversion_rate=conversion_rate,
                    cart_rate=cart_rate,
                    avg_order_cost=avg_order_cost,
                    roi=roi,
                    direct_orders=direct_orders,
                    direct_order_amount=direct_order_amount,
                    direct_cart_adds=direct_cart_adds,
                    indirect_orders=indirect_orders,
                    indirect_order_amount=indirect_order_amount,
                    indirect_cart_adds=indirect_cart_adds,
                    upload_date=timezone.now(),
                    uploader=user
                )
            return True
        except Exception as e:
            logger.error(f"保存矩阵分析数据失败: {str(e)}", exc_info=True)
            return False
            
    def _save_to_jd_real_time_data(self, df, user):
        """保存实时概况 - 按列位置直接处理"""
        try:
            logger.info(f"开始处理实时概况，数据形状: {df.shape}")
            
            # 显示原始数据的前几行
            for i in range(min(5, len(df))):
                logger.info(f"原始数据第{i+1}行: {df.iloc[i].tolist()}")
            
            saved_count = 0
            error_count = 0
            
            # 直接处理每一行数据，跳过标题行
            for index, row in df.iterrows():
                try:
                    # 检查是否是有效行（第一列必须有值）
                    if pd.isna(row.iloc[0]) or not str(row.iloc[0]).strip():
                        continue
                        
                    # 检查是否是表头行
                    if "时间" in str(row.iloc[0]):
                        logger.info(f"跳过表头行: {row.iloc[0]}")
                        continue
                    
                    # 获取时间范围
                    time_range = str(row.iloc[0]).strip()
                    
                    # 创建一个存储所有字段的字典
                    record = {'date': time_range}
                    
                    # 定义列索引到字段名的映射
                    # 这里的索引必须根据实际表格的列位置来设置
                    column_mapping = {
                        0: 'date',                   # 时间
                        1: 'visitor_count',          # 访客数
                        2: 'comp_visitor_count',     # 访客数(对比日)
                        3: 'visitor_compare',        # 较对比日
                        4: 'page_views',             # 浏览量  
                        5: 'comp_page_views',        # 浏览量(对比日)
                        6: 'page_views_compare',     # 较对比日
                        
                        # 其他列映射 - 根据实际表格结构调整
                        7: 'paid_count',             # 成交人数
                        8: 'comp_paid_count',        # 成交人数(对比日)
                        9: 'paid_compare',           # 较对比日
                        
                        10: 'conversion_rate',       # 成交转化率
                        11: 'comp_conversion_rate',  # 成交转化率(对比日)
                        12: 'conversion_rate_compare', # 较对比日
                        
                        13: 'paid_items',            # 成交商品件数
                        14: 'comp_paid_items',       # 成交商品件数(对比日)
                        15: 'paid_items_compare',    # 较对比日
                        
                        16: 'order_count',           # 成交单量
                        17: 'comp_order_count',      # 成交单量(对比日)
                        18: 'order_count_compare',   # 较对比日
                        
                        19: 'order_amount',          # 成交金额
                        20: 'comp_order_amount',     # 成交金额(对比日)
                        21: 'order_amount_compare',  # 较对比日
                        
                        22: 'customer_price',        # 成交客单价
                        23: 'comp_customer_price',   # 成交客单价(对比日)
                        24: 'customer_price_compare', # 较对比日
                        
                        25: 'cart_user_count',       # 加购客户数
                        26: 'comp_cart_user_count',  # 加购客户数(对比日)
                        27: 'cart_user_compare',     # 较对比日
                        
                        28: 'cart_items',            # 加购商品件数
                        29: 'comp_cart_items',       # 加购商品件数(对比日)
                        30: 'cart_items_compare',    # 较对比日
                        
                        31: 'pos_cart_items',        # 加购商品件数(正向)
                        32: 'comp_pos_cart_items',   # 加购商品件数(正向)(对比日)
                        33: 'pos_cart_items_compare', # 较对比日
                        
                        34: 'neg_cart_items',        # 加购商品件数(负向)
                        35: 'comp_neg_cart_items',   # 加购商品件数(负向)(对比日)
                        36: 'neg_cart_items_compare', # 较对比日
                        
                        37: 'uv_value',              # UV价值
                        38: 'comp_uv_value',         # UV价值(对比日)
                        39: 'uv_value_compare'       # 较对比日
                    }
                    
                    # 获取每个列的值
                    for col_idx, field_name in column_mapping.items():
                        if col_idx == 0:  # 时间列已处理
                            continue
                            
                        if col_idx < len(row):
                            value = row.iloc[col_idx]
                            
                            # 处理空值和特殊符号
                            if pd.isna(value) or value == '' or value == '-':
                                record[field_name] = 0
                            else:
                                # 处理百分比值
                                if isinstance(value, str) and '%' in value:
                                    try:
                                        value = value.replace('%', '').strip()
                                        record[field_name] = float(value) / 100
                                    except (ValueError, TypeError):
                                        record[field_name] = 0
                                else:
                                    try:
                                        # 尝试转换为浮点数
                                        record[field_name] = float(value)
                                    except (ValueError, TypeError):
                                        record[field_name] = 0
                        else:
                            record[field_name] = 0
                    
                    # 添加上传信息
                    record['upload_date'] = timezone.now()
                    record['uploader'] = user
                    
                    # 打印处理后的部分数据
                    logger.info(f"处理第 {index+1} 行: 时间={time_range}, "
                               f"访客数={record.get('visitor_count', 0)}, "
                               f"浏览量={record.get('page_views', 0)}")
                    
                    # 创建记录
                    JDRealTimeData.objects.create(**record)
                    saved_count += 1
                    
                except Exception as row_error:
                    error_count += 1
                    logger.error(f"处理第 {index+1} 行数据时出错: {str(row_error)}", exc_info=True)
                    continue
            
            logger.info(f"实时概况处理完成，成功保存 {saved_count} 条记录，失败 {error_count} 条")
            return saved_count > 0
            
        except Exception as e:
            logger.error(f"保存实时概况失败: {str(e)}", exc_info=True)
            return False
    
    def _save_to_jd_traffic_data(self, df, user):
        """保存流量总览"""
        try:
            for _, row in df.iterrows():
                date = self._get_column_value(row, ['时间', '日期'])
                visitor_count = self._get_column_value(row, ['访客数'])
                page_views = self._get_column_value(row, ['浏览量'])
                views_per_visitor = self._get_column_value(row, ['人均浏览量'])
                stay_duration = self._get_column_value(row, ['平均停留时长'])
                
                JDTrafficData.objects.create(
                    date=date,
                    visitor_count=visitor_count,
                    page_views=page_views,
                    views_per_visitor=views_per_visitor,
                    stay_duration=stay_duration,
                    upload_date=timezone.now(),
                    uploader=user
                )
            return True
        except Exception as e:
            logger.error(f"保存流量总览失败: {str(e)}", exc_info=True)
            return False
            
    def _save_to_jd_transaction_data(self, df, user):
        """保存交易概况"""
        try:
            for _, row in df.iterrows():
                date = self._get_column_value(row, ['时间', '日期'])
                page_views = self._get_column_value(row, ['浏览量'])
                visitor_count = self._get_column_value(row, ['访客数'])
                transaction_users = self._get_column_value(row, ['成交人数'])
                conversion_rate = self._get_column_value(row, ['成交转化率'])
                order_count = self._get_column_value(row, ['成交单量'])
                product_count = self._get_column_value(row, ['成交商品件数'])
                transaction_amount = self._get_column_value(row, ['成交金额'])
                average_order_value = self._get_column_value(row, ['成交客单价'])
                
                JDTransactionData.objects.create(
                    date=date,
                    page_views=page_views,
                    visitor_count=visitor_count,
                    transaction_users=transaction_users,
                    conversion_rate=conversion_rate,
                    order_count=order_count,
                    product_count=product_count,
                    transaction_amount=transaction_amount,
                    average_order_value=average_order_value,
                    upload_date=timezone.now(),
                    uploader=user
                )
            return True
        except Exception as e:
            logger.error(f"保存交易概况失败: {str(e)}", exc_info=True)
            return False
    
    def _save_to_jd_content_type_analysis(self, df, user):
        """保存内容类型分析数据"""
        try:
            logger.info(f"开始处理内容类型分析数据，数据形状: {df.shape}")
            logger.info(f"列名: {df.columns.tolist()}")
            
            # 显示原始数据的前几行
            for i in range(min(10, len(df))):
                logger.info(f"原始数据第{i+1}行: {df.iloc[i].tolist()}")
            
            saved_count = 0
            for index, row in df.iterrows():
                try:
                    # 跳过空行或表头行
                    if pd.isna(row.iloc[0]) or '日期' in str(row.iloc[0]):
                        continue
                    
                    # 提取所有字段，确保使用正确的列索引而不是列名
                    # 因为表格结构复杂，尝试按位置获取数据
                    date = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else None
                    content_type = str(row.iloc[1]).strip() if len(row) > 1 and not pd.isna(row.iloc[1]) else None
                    
                    # 如果关键字段为空，跳过这一行
                    if not date or not content_type:
                        continue
                    
                    # 直接从表格按位置读取数值
                    # 这些索引需要根据实际表格调整
                    online_content_guide = self._get_number_from_cell(row, 2)  # 在线内容引导进商
                    guide_merchant = self._get_number_from_cell(row, 3)  # 引导进商
                    guide_cart = self._get_number_from_cell(row, 4)  # 引导加购
                    same_day_guide = self._get_number_from_cell(row, 5)  # 当日引导
                    same_day_order = self._get_number_from_cell(row, 6)  # 当日引导成交单量
                    seven_day_guide = self._get_number_from_cell(row, 7)  # 7日引导成
                    seven_day_order = self._get_number_from_cell(row, 8)  # 7日引导成交单量
                    
                    # 记录详细信息用于调试
                    logger.info(f"处理第 {index+1} 行数据:")
                    logger.info(f"原始行数据: {row.tolist()}")
                    logger.info(f"日期: {date}, 内容类型: {content_type}")
                    logger.info(f"在线内容引导进商: {online_content_guide}, 引导进商: {guide_merchant}")
                    logger.info(f"引导加购: {guide_cart}, 当日引导: {same_day_guide}")
                    logger.info(f"当日引导成交单量: {same_day_order}, 7日引导成: {seven_day_guide}")
                    logger.info(f"7日引导成交单量: {seven_day_order}")
                    
                    # 构建完整的数据记录
                    data_content = {
                        "日期": date,
                        "内容类型": content_type,
                        "在线内容引导进商": online_content_guide,
                        "引导进商": guide_merchant,
                        "引导加购": guide_cart,
                        "当日引导": same_day_guide,
                        "当日引导成交单量": same_day_order,
                        "7日引导成": seven_day_guide,
                        "7日引导成交单量": seven_day_order
                    }
                    
                    # 创建记录
                    JDContentTypeAnalysis.objects.create(
                        date=date,
                        content_type=content_type,
                        online_content_guide=online_content_guide,
                        guide_merchant=guide_merchant,
                        guide_cart=guide_cart,
                        same_day_guide=same_day_guide,
                        same_day_order=same_day_order,
                        seven_day_guide=seven_day_guide,
                        seven_day_order=seven_day_order,
                        data_content=json.dumps(data_content, ensure_ascii=False),
                        upload_date=timezone.now(),
                        uploader=user
                    )
                    saved_count += 1
                    logger.info(f"成功保存第 {index+1} 行数据")
                    
                except Exception as row_error:
                    logger.error(f"处理第 {index+1} 行数据时出错: {str(row_error)}", exc_info=True)
                    continue
            
            logger.info(f"内容类型分析数据处理完成，共保存 {saved_count} 条记录")
            return saved_count > 0
            
        except Exception as e:
            logger.error(f"保存内容类型分析数据失败: {str(e)}", exc_info=True)
            return False
    
    def _get_number_from_cell(self, row, index):
        """从单元格获取数字，处理各种情况"""
        try:
            if index >= len(row) or pd.isna(row.iloc[index]):
                return 0
            
            value = row.iloc[index]
            if isinstance(value, (int, float)):
                return value
                
            # 如果是字符串，清理并转换
            if isinstance(value, str):
                value = value.strip().replace(',', '')
                if value == '' or value == '-':
                    return 0
                # 尝试转换为数字
                try:
                    return float(value)
                except ValueError:
                    logger.warning(f"无法将值 '{value}' 转换为数字")
                    return 0
            return 0
        except Exception as e:
            logger.error(f"从单元格获取数字时出错: {str(e)}")
            return 0

    def _extract_number_from_string(self, value):
        """从字符串中提取数字，处理各种格式"""
        if value is None:
            return None
            
        # 如果已经是数字，直接返回
        if isinstance(value, (int, float)):
            return value
            
        # 处理字符串
        if isinstance(value, str):
            # 清理字符串
            value = value.strip()
            
            # 空字符串返回None
            if not value or value == '-':
                return None
                
            # 处理百分比
            if '%' in value:
                try:
                    return float(value.replace('%', '').strip()) / 100
                except (ValueError, TypeError):
                    pass
                    
            # 处理包含"分"的字符串
            if '分' in value:
                try:
                    num_part = value.split('分')[0].strip()
                    return float(num_part)
                except (ValueError, TypeError, IndexError):
                    pass
            
            # 处理带有单位的数字，例如"55万"、"3.2k"等
            units = {'万': 10000, 'w': 10000, 'k': 1000}
            for unit, multiplier in units.items():
                if unit in value.lower():
                    try:
                        num_part = value.lower().split(unit)[0].strip()
                        return float(num_part) * multiplier
                    except (ValueError, TypeError, IndexError):
                        pass
            
            # 处理带有其他文字的数字（只提取第一个数字部分）
            import re
            number_match = re.search(r'[-+]?\d*\.?\d+', value)
            if number_match:
                try:
                    return float(number_match.group(0))
                except (ValueError, TypeError):
                    pass
                    
        return None

    def _save_to_jd_core_content_data(self, df, user):
        """保存核心数据"""
        try:
            for _, row in df.iterrows():
                date = self._get_column_value(row, ['日期'])
                content_data = self._get_column_value(row, ['内容数据'])
                online_content_count = self._get_column_value(row, ['在线内容数'])
                online_content_sku_coverage = self._get_column_value(row, ['在线内容覆盖sku数'])
                new_content_count = self._get_column_value(row, ['新增内容数'])
                new_content_sku_coverage = self._get_column_value(row, ['新增内容覆盖sku数'])
                content_views = self._get_column_value(row, ['内容浏览量'])
                content_visitors = self._get_column_value(row, ['内容访客数'])
                avg_stay_time = self._get_column_value(row, ['人均停留时长'])
                guide_detail_visitors = self._get_column_value(row, ['引导进商详访客数'])
                guide_detail_views = self._get_column_value(row, ['引导进商详浏览量'])
                guide_cart_users = self._get_column_value(row, ['引导加购人数'])
                guide_cart_times = self._get_column_value(row, ['引导加购次数'])
                daily_guide_order_amount = self._get_column_value(row, ['当日引导成交金额'])
                daily_guide_order_users = self._get_column_value(row, ['当日引导成交人数'])
                daily_guide_order_count = self._get_column_value(row, ['当日引导成交单量'])
                
                JDCoreContentData.objects.create(
                    date=date,
                    content_data=content_data,
                    online_content_count=online_content_count,
                    online_content_sku_coverage=online_content_sku_coverage,
                    new_content_count=new_content_count,
                    new_content_sku_coverage=new_content_sku_coverage,
                    content_views=content_views,
                    content_visitors=content_visitors,
                    avg_stay_time=avg_stay_time,
                    guide_detail_visitors=guide_detail_visitors,
                    guide_detail_views=guide_detail_views,
                    guide_cart_users=guide_cart_users,
                    guide_cart_times=guide_cart_times,
                    daily_guide_order_amount=daily_guide_order_amount,
                    daily_guide_order_users=daily_guide_order_users,
                    daily_guide_order_count=daily_guide_order_count,
                    upload_date=timezone.now(),
                    uploader=user
                )
            return True
        except Exception as e:
            logger.error(f"保存核心数据失败: {str(e)}", exc_info=True)
            return False

    def _save_to_jd_influencer_analysis(self, df, user):
        """保存达人分析数据"""
        try:
            logger.info(f"开始处理达人分析数据，数据形状: {df.shape}")
            logger.info(f"读取到的原始列名: {df.columns.tolist()}")
            
            saved_count = 0
            for index, row in df.iterrows():
                try:
                    # 跳过表头行或空行
                    if pd.isna(row.iloc[0]) or '日期' in str(row.iloc[0]):
                        continue
                    
                    # 获取各字段值
                    date = row.get('日期', None)
                    influencer = row.get('达人', None)
                    influencer_name = row.get('达人名称', None)
                    guide_detail_visitors = self._get_column_value(row, ['引导进商详访客数'])
                    guide_cart_users = self._get_column_value(row, ['引导加购人 数', '引导加购人数'])
                    daily_guide_order_amount = self._get_column_value(row, ['当日引导成交金额'])
                    daily_guide_order_count = self._get_column_value(row, ['当日引导成交单量'])
                    
                    # 验证必填字段
                    if pd.isna(date) or pd.isna(influencer):
                        continue
                    
                    # 处理可能的NaN值
                    if pd.isna(guide_detail_visitors):
                        guide_detail_visitors = 0
                    if pd.isna(guide_cart_users):
                        guide_cart_users = 0
                    if pd.isna(daily_guide_order_amount):
                        daily_guide_order_amount = 0
                    if pd.isna(daily_guide_order_count):
                        daily_guide_order_count = 0
                    
                    # 确保所有数值字段为正确的类型
                    try:
                        guide_detail_visitors = int(float(guide_detail_visitors))
                        guide_cart_users = int(float(guide_cart_users))
                        daily_guide_order_amount = float(daily_guide_order_amount)
                        daily_guide_order_count = int(float(daily_guide_order_count))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"转换数值时出错: {e}, 使用默认值0")
                        if isinstance(e, ValueError) and "float NaN" in str(e):
                            # 明确是NaN值导致的错误
                            if "guide_detail_visitors" in str(e):
                                guide_detail_visitors = 0
                            if "guide_cart_users" in str(e):
                                guide_cart_users = 0
                            if "daily_guide_order_amount" in str(e):
                                daily_guide_order_amount = 0
                            if "daily_guide_order_count" in str(e):
                                daily_guide_order_count = 0
                    
                    # 打印处理信息
                    logger.info(f"处理第 {index+1} 行数据:")
                    logger.info(f"日期: {date}, 达人: {influencer}, 达人名称: {influencer_name}")
                    logger.info(f"引导进商详访客数: {guide_detail_visitors}, 引导加购人数: {guide_cart_users}")
                    logger.info(f"当日引导成交金额: {daily_guide_order_amount}, 当日引导成交单量: {daily_guide_order_count}")
                    
                    # 使用正确的字段名创建记录
                    JDInfluencerAnalysis.objects.create(
                        date=date,
                        influencer=influencer,
                        influencer_name=influencer_name,
                        guide_detail_visitors=guide_detail_visitors,
                        guide_cart_users=guide_cart_users,
                        daily_guide_order_amount=daily_guide_order_amount,
                        daily_guide_order_count=daily_guide_order_count,
                        upload_date=timezone.now(),
                        uploader=user
                    )
                    saved_count += 1
                    
                except Exception as row_error:
                    logger.error(f"处理第 {index+1} 行数据时出错: {str(row_error)}", exc_info=True)
                    continue
            
            logger.info(f"达人分析数据处理完成，共保存 {saved_count} 条记录")
            return saved_count > 0
            
        except Exception as e:
            logger.error(f"保存达人分析数据失败: {str(e)}", exc_info=True)
            return False

    def _save_to_jd_source_analysis(self, df, user):
        """保存商智内容数据 - 来源分析数据"""
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 获取必要数据
                date_value = self._get_column_value(row, ['日期', 'date'])
                source_value = self._get_column_value(row, ['来源', 'source'])
                
                # 这里需要修改字段名，从guide_visitors改为detail_visitors
                detail_visitors_value = self._get_column_value(row, ['引导进商详访客数', 'detail_visitors'])
                guide_cart_users_value = self._get_column_value(row, ['引导加购人数', 'guide_cart_users'])
                daily_guide_order_amount_value = self._get_column_value(row, ['当日引导成交金额', 'daily_guide_order_amount'])
                daily_guide_order_count_value = self._get_column_value(row, ['当日引导成交单量', 'daily_guide_order_count'])
                
                # 创建记录
                JDSourceAnalysis.objects.create(
                    date=date_value,
                    source=source_value,
                    detail_visitors=detail_visitors_value,  # 修改这里
                    guide_cart_users=guide_cart_users_value,
                    daily_guide_order_amount=daily_guide_order_amount_value,
                    daily_guide_order_count=daily_guide_order_count_value,
                    upload_date=timezone.now(),
                    uploader=user
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"保存来源分析数据时出错: {e}")
        
        return success_count, error_count

    def _save_to_jd_content_analysis(self, df, user):
        """保存商智内容数据 - 内容分析数据"""
        success_count = 0
        error_count = 0
        
        # 日志记录原始列名
        column_names = df.columns.tolist()
        logging.info(f"读取到的原始列名: {column_names}")
        logging.info(f"开始处理内容分析数据，数据形状: {df.shape}")
        
        for index, row in df.iterrows():
            try:
                # 获取日期和内容类型
                date_value = self._get_column_value(row, ['日期', 'date'])
                content_type_value = self._get_column_value(row, ['内容类型', 'content_type'])
                
                # 记录正在处理的行
                logging.info(f"处理第 {index+1} 行: 日期={date_value}, 内容类型={content_type_value}")
                
                # 其他字段
                content_value = self._get_column_value(row, ['内容', 'content'])
                first_publish_time = self._get_column_value(row, ['首次发布时间', '首次发 布时间'])
                content_name_value = self._get_column_value(row, ['内容名称', 'content_name'])
                influencer_name_value = self._get_column_value(row, ['达人名称', 'influencer_name'])
                
                # 引导访客数等数据，修改为模型中正确的字段名
                detail_visitors_value = self._get_column_value(row, ['引导进商详访客数'])
                cart_users_value = self._get_column_value(row, ['引导加购人数'])
                conversion_amount_value = self._get_column_value(row, ['当日引导成交金额'])
                conversion_orders_value = self._get_column_value(row, ['当日引导成交单量'])
                
                # 使用正确的字段名创建记录
                JDContentAnalysis.objects.create(
                    date=date_value,
                    content=content_value,
                    content_type=content_type_value,
                    first_publish_time=first_publish_time,
                    content_name=content_name_value,
                    influencer_name=influencer_name_value,
                    detail_visitors=detail_visitors_value,
                    cart_users=cart_users_value,
                    conversion_amount=conversion_amount_value,
                    conversion_orders=conversion_orders_value,
                    upload_date=timezone.now()
                    # 注意：不要包含uploader字段，因为模型中没有定义该字段
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                logging.error(f"处理第 {index+1} 行数据时出错: {e}")
                logging.exception(e)
        
        logging.info(f"内容分析数据处理完成，共保存 {success_count} 条记录")
        return success_count, error_count

    def _save_to_jd_product_analysis(self, df, user):
        """保存商智内容数据 - 商品分析数据"""
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 获取必要的字段数据
                time_value = self._get_column_value(row, ['时间', 'time'])
                dimension_value = self._get_column_value(row, ['所选维度', '维度', 'dimension'])
                
                # 保存其他数据为JSON格式
                data_content = {}
                for col in df.columns:
                    if col not in ['时间', 'time', '所选维度', '维度', 'dimension']:
                        data_content[col] = str(row[col])
                
                # 创建记录，确保字段名与模型匹配
                JDProductAnalysis.objects.create(
                    time=time_value,
                    dimension=dimension_value,
                    data_content=json.dumps(data_content, ensure_ascii=False),
                    # 注意：upload_date是自动添加的，不需要手动设置
                    # 模型中没有uploader字段，移除它
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"保存商品分析数据时出错: {e}")
        
        return success_count, error_count

    def _save_to_jd_product_overview(self, df, user):
        """保存商智产品数据 - 商品概况"""
        success_count = 0
        error_count = 0
        
        try:
            # 将整个DataFrame转换为JSON保存
            data_content = df.to_json(orient='records', force_ascii=False)
            
            # 创建记录，确保字段名与模型匹配
            JDProductOverview.objects.create(
                data_content=data_content
                # 注意：upload_date是自动添加的，不需要手动设置
                # 模型中没有uploader字段，移除它
            )
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"保存商品概况数据时出错: {e}")
        
        return success_count, error_count

    def _save_to_jd_inventory_data(self, df, user):
        """保存商智产品数据 - 库存概况"""
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 获取必要的字段数据
                warehouse_type = self._get_column_value(row, ['仓网类型', 'warehouse_type'])
                region = self._get_column_value(row, ['区域', 'region'])
                turnover_rate = self._get_column_value(row, ['数量周转', 'turnover_rate'])
                in_stock_cost = self._get_column_value(row, ['现货库存成本', 'in_stock_cost'])
                in_stock_inventory = self._get_column_value(row, ['现货库存', 'in_stock_inventory'])
                available_inventory = self._get_column_value(row, ['可用库存', 'available_inventory'])
                orderable_inventory = self._get_column_value(row, ['可订购库存', 'orderable_inventory'])
                
                # 保存其他数据为JSON格式
                data_content = {}
                for col in df.columns:
                    if col not in ['仓网类型', 'warehouse_type', '区域', 'region', '数量周转', 'turnover_rate',
                                  '现货库存成本', 'in_stock_cost', '现货库存', 'in_stock_inventory',
                                  '可用库存', 'available_inventory', '可订购库存', 'orderable_inventory']:
                        data_content[col] = str(row[col])
                
                # 创建记录，确保字段名与模型匹配
                JDInventoryData.objects.create(
                    warehouse_type=warehouse_type,
                    region=region,
                    turnover_rate=turnover_rate,
                    in_stock_cost=in_stock_cost,
                    in_stock_inventory=in_stock_inventory,
                    available_inventory=available_inventory,
                    orderable_inventory=orderable_inventory,
                    data_content=json.dumps(data_content, ensure_ascii=False),
                    upload_date=timezone.now(),
                    uploader=user
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"保存库存概况时出错: {e}")
        
        return success_count, error_count

    def _save_to_jd_octopus_jingmai_data(self, df, user):
        """保存京麦数据"""
        logging.info(f"DataFrame shape: {df.shape}")
        logging.info(f"DataFrame columns: {df.columns.tolist()}")
        
        success_count = 0
        error_count = 0
        
        try:
            for index, row in df.iterrows():
                try:
                    # 处理数值字段，将nan和百分比转换为浮点数
                    def safe_convert_number(value, convert_func):
                        if pd.isna(value):
                            return None
                        try:
                            if isinstance(value, str):
                                # 移除空白字符和换行符
                                value = value.strip().replace('\n', '').replace(' ', '')
                                # 处理百分比
                                if '%' in value:
                                    value = value.strip('%')
                                    return convert_func(float(value)) / 100
                                # 处理包含"分"的字符串
                                if '分' in value:
                                    value = value.split('分')[0]
                            return convert_func(value)
                        except (ValueError, TypeError):
                            return None

                    # 处理整数字段
                    customer_count = safe_convert_number(row.get('客户数量'), int)
                    shop_entries = safe_convert_number(row.get('进店数'), int)
                    detail_views = safe_convert_number(row.get('浏览商详'), int)
                    cart_adds = safe_convert_number(row.get('加购'), int)
                    transaction_count = safe_convert_number(row.get('成交数'), int)

                    # 处理浮点数字段
                    entry_rate = safe_convert_number(row.get('进店率'), float)
                    view_rate = safe_convert_number(row.get('浏览率'), float)
                    cart_rate = safe_convert_number(row.get('加购率'), float)
                    cart_to_transaction_rate = safe_convert_number(row.get('加购成交率'), float)
                    new_customer_beat_rate = safe_convert_number(row.get('新客数打败相似店铺百分率'), float)

                    # 创建京麦数据记录
                    jingmai_record = JDOctopusJingmaiData.objects.create(
                        category='八爪鱼',
                        subcategory='京麦采集',  # 修正子类别
                        indicator=str(row.get('指标', '')),
                        description=str(row.get('描述', '')),
                        score_change=str(row.get('评分及升降分', '')),
                        title=str(row.get('标题', '')),
                        score_rate=str(row.get('分数和升降率', '')),
                        customer_metric=str(row.get('客户转化指标', '')),
                        customer_count=customer_count,
                        shop_entries=shop_entries,
                        detail_views=detail_views,
                        cart_adds=cart_adds,
                        transaction_count=transaction_count,
                        entry_rate=entry_rate,
                        view_rate=view_rate,
                        cart_rate=cart_rate,
                        cart_to_transaction_rate=cart_to_transaction_rate,
                        new_customer_beat_rate=new_customer_beat_rate,
                        transaction_rate_beat=str(row.get('成交转化率打败相似店铺', '')),
                        view_rate_beat=str(row.get('浏览率打败相似店铺', '')),
                        entry_rate_beat=str(row.get('进店率打败相似店铺', '')),
                        cart_transaction_rate_beat=str(row.get('加购成交率打败相似店铺', '')),
                        top_shop_type=str(row.get('top店铺类型', ''))
                    )

                    # 处理店铺排名数据
                    ranking_type = row.get('top店铺类型', '')
                    if ranking_type:
                        # 从toplistli2到toplistli249处理店铺排名
                        ranking_count = 0
                        for i in range(2, 250):
                            key = f'toplistli{i}' if i == 2 else f'toplistli2{i-1}'
                            if key in row and not pd.isna(row[key]):
                                shop_name = str(row[key])
                                JDShopRanking.objects.create(
                                    shop_name=shop_name,
                                    ranking=i-1,  # 排名从1开始
                                    ranking_type=ranking_type,
                                    jingmai_data=jingmai_record
                                )
                                ranking_count += 1
                        
                        logging.info(f"成功为第 {index + 1} 行数据创建 {ranking_count} 条店铺排名记录")

                    success_count += 1
                    logging.info(f"成功保存第 {index + 1} 行京麦数据")
                except Exception as e:
                    error_count += 1
                    logging.error(f"保存第 {index + 1} 行京麦数据时出错: {str(e)}", exc_info=True)
                    continue
            
            logging.info(f"京麦数据处理完成，成功: {success_count}，失败: {error_count}")
            return success_count  # 返回成功处理的记录数
        
        except Exception as e:
            logging.error(f"处理京麦数据时发生全局错误: {str(e)}", exc_info=True)
            return 0  # 发生全局错误时返回0

    def _save_to_jd_octopus_product_search(self, df, user):
        """保存八爪鱼 - 京东商品搜索数据"""
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 获取必要的字段数据
                search_keyword = self._get_column_value(row, ['搜索关键词', 'search_keyword'])
                product_name = self._get_column_value(row, ['商品名称', 'product_name'])
                price = self._get_column_value(row, ['价格', 'price'])
                shop_name = self._get_column_value(row, ['商家店名', '店铺名称', 'shop_name'])
                product_sku = self._get_column_value(row, ['商品SKU', 'product_sku'])
                product_link = self._get_column_value(row, ['商品链接', 'product_link'])
                review_count = self._get_column_value(row, ['评价人数', 'review_count'])
                review_link = self._get_column_value(row, ['评论链接', 'review_link'])
                shop_link = self._get_column_value(row, ['店铺链接', 'shop_link'])
                tags = self._get_column_value(row, ['标签', 'tags'])
                cover_image_link = self._get_column_value(row, ['封面图片链接', 'cover_image_link'])
                is_ad = self._get_column_value(row, ['是否广告', 'is_ad'])
                page_number = self._get_column_value(row, ['页码', 'page_number'])
                current_time = self._get_column_value(row, ['当前时间', 'current_time'])
                page_url = self._get_column_value(row, ['页面网址', 'page_url'])
                
                # 创建记录，确保字段名与模型匹配
                JDOctopusProductSearch.objects.create(
                    search_keyword=search_keyword,
                    product_name=product_name,
                    price=price,
                    shop_name=shop_name,
                    product_sku=product_sku,
                    product_link=product_link,
                    review_count=review_count,
                    review_link=review_link,
                    shop_link=shop_link,
                    tags=tags,
                    cover_image_link=cover_image_link,
                    is_ad=is_ad,
                    page_number=page_number,
                    current_time=current_time,
                    page_url=page_url,
                    upload_date=timezone.now(),
                    uploader=user
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"保存京东商品搜索数据时出错: {e}")
        
        return success_count, error_count

    def _save_to_jd_easy_spider_data(self, df, user):
        """保存易采集数据"""
        try:
            logger.info(f"开始处理易采集数据，数据形状: {df.shape}")
            saved_count = 0
            
            for index, row in df.iterrows():
                try:
                    # 获取字段值 - 直接使用 _get_column_value 方法更安全
                    activity_name = self._get_column_value(row, ['活动名称', 'activity_name'])
                    activity_type = self._get_column_value(row, ['活动类型', 'activity_type'])
                    activity_type2 = self._get_column_value(row, ['活动类型2', 'activity_type2'])
                    activity_description = self._get_column_value(row, ['活动说明', 'activity_description'])
                    remaining_time = self._get_column_value(row, ['报名还剩', '报名还 剩', 'remaining_time'])
                    
                    # 确保获取到活动名称
                    if not activity_name:
                        continue
                    
                    # 创建记录 - 直接使用字符串值，不尝试数值转换
                    JDEasySpiderData.objects.create(
                        activity_name=str(activity_name),
                        activity_type=str(activity_type) if activity_type else None,
                        activity_type2=str(activity_type2) if activity_type2 else None,
                        activity_description=str(activity_description) if activity_description else None,
                        remaining_time=str(remaining_time) if remaining_time else None,
                        upload_date=timezone.now()
                    )
                    saved_count += 1
                    
                except Exception as row_error:
                    logger.error(f"处理第 {index+1} 行数据时出错: {str(row_error)}", exc_info=True)
                    continue
            
            logger.info(f"易采集数据处理完成，共保存 {saved_count} 条记录")
            return saved_count
        except Exception as e:
            logger.error(f"保存易采集数据失败: {str(e)}", exc_info=True)
            return False

    # 新增通用列值获取方法
    def _get_column_value(self, row, possible_keys):
        """处理不同文件可能存在的列名差异"""
        # 添加常见列名变体处理
        key_variants = {
            '点击率(%)': ['点击率', '点击率(%)', '点击率%'],
            '加购率(%)': ['加购率', '加购率(%)', '加购率%'],
            '当前时间': ['当前时间', '时间', '日期时间']
        }

        expanded_keys = []
        for key in possible_keys:
            expanded_keys.extend(key_variants.get(key, [key]))

        for key in expanded_keys:
            if key in row:
                return row[key]
        return None

# ===============模型接口===============
# GLM模型
# GLM语言模型chat类型，glm-4
class GLM4View(APIView):
    def post(self, request):
        """
        处理POST请求，调用GLM（Generative Language Model）服务并返回结果。
        """
        # 定义GLM服务的URL地址
        glm_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        
        # 从请求的数据中获取用户的问题，默认为空字符串
        question = request.data.get('question', '')
        
        # 从请求的数据中获取要使用的模型名称
        model_name = request.data.get('model')  # 直接使用传入的模型名称
        
        # 如果问题为空，则返回错误信息并设置HTTP状态码为400 Bad Request
        if not question:
            return Response({"error": "question is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 构造发送到GLM API的头部信息，包括授权和内容类型
        headers = {
            "Authorization": f"Bearer {config.GLM_API_KEY}",  # 使用API密钥进行身份验证
            "Content-Type": "application/json",     # 指定请求体的内容类型为JSON
        }
        
        # 构建发送给GLM API的请求数据
        data = {
            "model": model_name,  # 请求中指定要使用的模型名称
            
            # 用户的消息部分，包含角色（这里是用户）和具体问题内容
            "messages": [{"role": "user", "content": question}],
            
            # 工具配置：这里指定了一个检索工具
            "tools": [
                {
                    "type": "retrieval",  # 工具类型是"检索"
                    
                    # 具体的检索配置：
                    "retrieval": {
                        "knowledge_id": " ",  # 知识库ID
                        
                        # 提示模板，告诉模型如何处理检索到的信息
                        "prompt_template": (
                            "从\n\"\"\"\n{{knowledge}}\n\"\"\"\n中找问题\n\"\"\"\n{{question}}\n\"\"\"\n的答案，如果有对应的答案则用内容回复，没有找到的话就用最有温度的聊天和我对话，不要重复直接回答"
                        )
                    }
                }
            ]
        }

        try:
            # 尝试通过requests库发起一个POST请求到GLM API服务器
            response = requests.post(glm_url, headers=headers, json=data)
            
            # 检查API响应的状态码是否在成功范围内（如2xx）。如果不是，则引发HTTPError异常
            response.raise_for_status()
            
            # 返回API的成功响应数据，并将HTTP状态码设为200 OK
            return Response(response.json(), status=status.HTTP_200_OK)
        
        except requests.exceptions.RequestException as e:
            # 如果发生任何与网络请求相关的错误（例如连接失败、超时等），捕获这些异常并返回详细的错误信息，
            # 同时设置HTTP状态码为503 Service Unavailable表示临时不可用的服务端问题。
            return Response(
                {"error": f"API request failed: {str(e)}"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        except json.JSONDecodeError:
            # 当API返回的数据不是有效的JSON格式时，会抛出json.JSONDecodeError异常；
            # 这里我们捕捉此异常，并告知客户端API响应格式无效，同时设置HTTP状态码为502 Bad Gateway表示网关或代理收到上游服务器的有效响应但是无法解析它。
            return Response(
                {"error": "Invalid API response format"}, 
                status=status.HTTP_502_BAD_GATEWAY
            )
# GLM语言模型多模态识别glm-4v模型
class GLM4VView(APIView):
    def post(self, request):
        glm_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        
        # 直接获取完整的messages结构
        messages = request.data.get('messages', [])
        model_name = request.data.get('model', 'glm-4v-flash')

        # 基本验证
        if not messages:
            return Response({"error": "messages is required"}, status=status.HTTP_400_BAD_REQUEST)

        headers = {
            "Authorization": f"Bearer {config.GLM_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": model_name,
            "messages": messages  # 直接使用客户端传来的messages结构
        }

        try:
            response = requests.post(glm_url, headers=headers, json=data)
            response.raise_for_status()
            return Response(response.json(), status=status.HTTP_200_OK)
            
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except json.JSONDecodeError:
            return Response({"error": "Invalid API response format"}, status=status.HTTP_502_BAD_GATEWAY)
# GLM文生图模型glm-CogView
class GLMCogView(APIView):
    def post(self, request):
        cog_url = "https://open.bigmodel.cn/api/paas/v4/images/generations"
        
        # 获取参数
        model_name = request.data.get('model', 'cogview-3')
        prompt = request.data.get('prompt', '')
        size = request.data.get('size', '1024x1024')  # 默认尺寸
        user_id = request.data.get('user_id', '')  # 可选参数
        
        # 基本验证
        if not prompt:
            return Response({"error": "prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        headers = {
            "Authorization": f"Bearer {config.GLM_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": model_name,
            "prompt": prompt
        }
        
        # 添加可选参数
        if size:
            data["size"] = size
        if user_id:
            data["user_id"] = user_id

        try:
            response = requests.post(cog_url, headers=headers, json=data)
            response.raise_for_status()
            return Response(response.json(), status=status.HTTP_200_OK)
            
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except json.JSONDecodeError:
            return Response({"error": "Invalid API response format"}, status=status.HTTP_502_BAD_GATEWAY)
# GLM文生视频模型CogVideoX
class CogVideoXView(APIView):
    def post(self, request):
        """生成视频请求"""
        try:
            # 初始化智谱AI客户端
            client = ZhipuAI(api_key=config.GLM_API_KEY)
            
            if request.data.get('action') == 'check_status':
                # 查询任务状态
                task_id = request.data.get('task_id')
                if not task_id:
                    return Response({"error": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST)
                    
                response = client.videos.retrieve_videos_result(id=task_id)
                
                # 直接返回视频结果对象的所有属性
                return Response({
                    "task_status": response.task_status,
                    "video_result": [
                        {
                            "url": video.url,
                            "cover_image_url": video.cover_image_url
                        } for video in response.video_result
                    ] if hasattr(response, 'video_result') else []
                }, status=status.HTTP_200_OK)
            else:
                # 生成视频
                # 获取参数
                model_name = request.data.get('model', 'cogvideox-flash')
                prompt = request.data.get('prompt')
                image_url = request.data.get('image_url')
                quality = request.data.get('quality', 'quality')
                with_audio = request.data.get('with_audio', True)
                size = request.data.get('size', '720x480')
                fps = request.data.get('fps', 30)
                
                # 基本验证
                if not prompt:
                    return Response({"error": "prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
                
                # 生成视频
                response = client.videos.generations(
                    model=model_name,
                    prompt=prompt,
                    image_url=image_url,
                    quality=quality,
                    with_audio=with_audio,
                    size=size,
                    fps=fps
                )
                return Response({"task_id": response.id}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
# GLM语音对话模型GLM-4-Voice
class GLM4Voice(APIView):
    def post(self, request):
        """生成语音请求"""
        try:
            # 初始化智谱AI客户端
            client = ZhipuAI(api_key=config.GLM_API_KEY)
            
            # 获取参数
            model_name = request.data.get('model', 'glm-4-voice')
            messages = request.data.get('messages', [])
            do_sample = request.data.get('do_sample', True)
            stream = request.data.get('stream', False)
            temperature = request.data.get('temperature', 0.8)
            top_p = request.data.get('top_p', 0.6)
            max_tokens = request.data.get('max_tokens', 1024)
            stop = request.data.get('stop')
            user_id = request.data.get('user_id')
            request_id = request.data.get('request_id')
            
            # 基本验证
            if not messages:
                return Response({"error": "messages is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 调用API
            kwargs = {
                "model": model_name,
                "messages": messages,
                "do_sample": do_sample,
                "stream": stream,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens
            }
            
            # 添加可选参数
            if stop:
                kwargs["stop"] = stop
            if user_id:
                kwargs["user_id"] = user_id
            if request_id:
                kwargs["request_id"] = request_id
            
            response = client.chat.completions.create(**kwargs)
            
            # 构造响应
            result = {
                "id": response.id,
                "created": response.created,
                "model": response.model,
                "choices": [{
                    "index": choice.index,
                    "finish_reason": choice.finish_reason,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                    }
                } for choice in response.choices],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            # 如果有音频数据，添加到结果中
            if hasattr(response.choices[0].message, "audio"):
                result["choices"][0]["message"]["audio"] = response.choices[0].message.audio
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

# COZE对话模型
class CozeChatView(APIView):
    def post(self, request):
        """生成对话请求"""
        try:
            # 获取参数，api_token和bot_id使用默认配置值，但user_id必须由前端提供
            coze_api_token = request.data.get('api_token', config.COZE_API_TOKEN)
            bot_id = request.data.get('bot_id', config.COZE_BOT_ID)
            user_id = request.data.get('user_id')
            question = request.data.get('question')
            
            # 基本验证
            if not question:
                return Response({"error": "question is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not user_id:
                return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 初始化Coze客户端
            coze = Coze(
                auth=TokenAuth(token=coze_api_token), 
                base_url=0-COZE_BASE_URL
            )
            
            content = ""
            token_count = 0
            
            # 使用stream方式调用API
            for event in coze.chat.stream(
                bot_id=bot_id,
                user_id=user_id,
                additional_messages=[
                    Message.build_user_question_text(question),
                ]
            ):
                # 实时处理消息增量
                if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                    content += event.message.content
                
                # 完成时获取token用量
                if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                    token_count = event.chat.usage.token_count
            
            # 构造响应
            result = {
                "content": content,
                "token_count": token_count
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

# Qwen模型
# 大语言模型-单轮对话
class QwenChat(APIView):
    def post(self, request):
        # 获取请求参数
        content = request.POST.get('content',  '')
        system_role = request.POST.get('system_role',  '用最温柔的语气回复我的问题')
        model = request.POST.get('model',  'qwen2.5-1.5b-instruct')  # 默认模型，可由前端指定
        
        # 构造消息列表
        messages = [
            {'role': 'system', 'content': system_role},
            {'role': 'user', 'content': content}
        ]
        
        try:
            # 调用 Generation.call  方法，关闭流式输出
            response = Generation.call( 
                api_key=config.QWEN_API_KEY,
                model=model,  # 使用前端传入的模型 
                messages=messages,
                result_format="message",
                stream=False  # 关闭流式输出
            )
            
            # 提取完整内容 
            full_content = ""
            if response.output  and response.output.choices: 
                for choice in response.output.choices: 
                    if choice.message  and choice.message.content: 
                        full_content += choice.message.content 
            
            # 返回完整结果
            return Response({'text': full_content})
        
        except Exception as e:
            # 捕获异常并返回错误信息
            return Response({'error': str(e)}, status=500)
# 视觉理解：
class Qwenvl(APIView):
    def post(self, request):
        try:
            # 获取请求数据
            data = request.data
            text = data.get('text', '')
            file_data = data.get('file')
            
            if not file_data:
                return Response({'error': '图片数据必填'}, status=400)
            
            client = OpenAI(
                api_key=config.QWEN_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            # 记录请求信息
            logger.info(f"Qwenvl请求: text={text}")
            
            completion = client.chat.completions.create(
                model="qwen2-vl-2b-instruct",
                messages=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": "你是一个专业的心理医生,需要结合用户提供的图片和问题,从心理和情绪的角度给出温暖的回应。"}]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{file_data}"}
                            },
                            {"type": "text", "text": text or "请分析这张图片"}
                        ]
                    }
                ]
            )
            
            # 记录响应信息
            response_text = completion.choices[0].message.content
            logger.info(f"Qwenvl响应: {response_text}")
            
            return Response({'text': response_text})
            
        except Exception as e:
            logger.error(f"Qwenvl处理错误: {str(e)}\n{traceback.format_exc()}")
            return Response({'error': str(e)}, status=500)

# 大语言模型-长文本对话
class QwenChatFile(APIView):
    def post(self, request):
        try:
            # 获取上传的文件
            file = request.FILES.get('file')
            text = request.POST.get('text', '请分析这个文档')
            
            if not file:
                return Response({'error': '文件不能为空'}, status=400)
                
            # 记录请求信息
            logger.info(f"文件处理请求: filename={file.name}, text={text}")
            
            # 创建临时目录
            temp_dir = Path('temp_files')
            temp_dir.mkdir(exist_ok=True)
            
            # 保存文件
            file_path = temp_dir / file.name
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            try:
                # 初始化客户端
                client = OpenAI(
                    api_key=config.QWEN_API_KEY,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
                
                # 上传文件
                file_object = client.files.create(
                    file=file_path,
                    purpose="file-extract"
                )
                
                # 发送问题
                completion = client.chat.completions.create(
                    model="qwen-long",
                    messages=[
                        {"role": "system", "content": f"fileid://{file_object.id}"},
                        {"role": "user", "content": text}
                    ]
                )
                
                response_text = completion.choices[0].message.content
                # 记录响应信息
                logger.info(f"文件处理响应: {response_text}")
                
                return Response({'text': response_text})
                
            finally:
                # 清理文件
                if file_path.exists():
                    file_path.unlink()
                temp_dir.rmdir()
                
        except Exception as e:
            logger.error(f"文件处理错误: {str(e)}\n{traceback.format_exc()}")
            return Response({'error': str(e)}, status=500)
        
# 带应用Deeskeep版本
class deeskeep(APIView):
    def post(self, request):
        # 1. 从request.data获取内容更可靠，因为可以处理不同类型的请求
        content = request.data.get('content', '')
        session_id = request.session.get('session_id')
        has_thoughts = request.data.get('has_thoughts', True)  # 默认返回思考过程

        try:
            if not session_id:
                # 2. 添加错误处理
                if not config.QWEN_API_KEY or not config.QWEN_Deeskeep_ID:
                    return Response({'error': 'API配置缺失'}, status=500)
                
                # 初始化会话
                init_response = Application.call(
                    api_key=config.QWEN_API_KEY,
                    app_id=config.QWEN_Deeskeep_ID,
                    prompt=' '
                )
                
                # 3. 添加响应验证
                if not hasattr(init_response, 'output') or not hasattr(init_response.output, 'session_id'):
                    return Response({'error': '会话初始化失败'}, status=500)
                
                session_id = init_response.output.session_id
                request.session['session_id'] = session_id

            # 4. 添加输入验证
            if not content.strip():
                return Response({'error': '输入内容不能为空'}, status=400)

            # 调用API，使用用户输入和会话ID，添加has_thoughts参数
            response = Application.call(
                api_key=config.QWEN_API_KEY,
                app_id=config.QWEN_Deeskeep_ID,
                prompt=content,
                session_id=session_id,
                has_thoughts=has_thoughts  # 是否返回思考过程
            )
            
            # 检查状态码
            if response.status_code != 200:
                logger.error(f"API请求失败: request_id={response.request_id}, code={response.status_code}, message={response.message}")
                return Response({
                    'error': '模型请求失败',
                    'request_id': response.request_id,
                    'code': response.status_code,
                    'message': response.message
                }, status=500)
            
            # 构建返回结果
            result = {'text': response.output.text}
            
            # 如果包含思考过程，则添加到结果中
            if has_thoughts and hasattr(response.output, 'thoughts'):
                result['thoughts'] = response.output.thoughts
            
            return Response(result)
            
        except Exception as e:
            # 6. 添加日志记录
            logger.error(f"desskeep错误: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)

# 大语言模型-多轮对话
class QwenChatToke(APIView):
    def post(self, request):
        # 1. 从request.data获取内容更可靠，因为可以处理不同类型的请求
        content = request.data.get('content', '')
        
        # 详细的日志记录，帮助调试
        logger.info(f"QwenChatToke接收到请求，内容长度: {len(content) if content else 0}")
        logger.info(f"请求数据类型: {type(request.data)}")
        logger.info(f"请求头: {request.headers}")

        try:
            # 检查内容是否为空
            if not content or not content.strip():
                logger.error("QwenChatToke接收到空内容")
                return JsonResponse({'error': '输入内容不能为空'}, status=400)
            
            # 设置超时和截断，避免过长内容导致API调用失败
            prompt = content
            if len(prompt) > 30000:
                logger.warning(f"内容过长 ({len(prompt)} 字符)，截断至30000字符")
                prompt = prompt[:30000] + "... [内容已截断]"
            
            # 使用更直接的方式进行调用，设置更长的超时时间
            dashscope.api_key = config.QWEN_API_KEY
            
            response = Generation.call(
                model='qwen-max',
                prompt=prompt,
                max_tokens=2048,
                timeout=300  # 5分钟超时
            )
            
            # 添加响应验证
            if not hasattr(response, 'status_code') or response.status_code != 200:
                error_msg = f'API错误: {getattr(response, "code", "未知")}, {getattr(response, "message", "未知")}'
                logger.error(f"API响应错误: {error_msg}")
                return JsonResponse({'error': error_msg}, status=500)
                
            # 提取并返回响应文本
            result = response.output.text
            return JsonResponse({'text': result})
            
        except Exception as e:
            # 日志记录
            logger.error(f"QwenChatToke错误: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
# 图像识别OCR
class QwenOCR(APIView):
    def post(self, request):
        try:
            client = OpenAI(
                api_key=config.QWEN_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            uploaded_file = request.FILES.get('file')
            question = request.POST.get('question', '提取所有图中文字')
            if not uploaded_file:
                return JsonResponse({'error': '未上传文件'}, status=400)
            
            # 读取并编码文件
            file_data = base64.b64encode(uploaded_file.read()).decode('utf-8')
            
            completion = client.chat.completions.create(
                model="qwen-vl-ocr",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{file_data}"},
                                "min_pixels": 28 * 28 * 4,
                                "max_pixels": 28 * 28 * 1280
                            },
                            {"type": "text", "text": question},
                        ],
                    }
                ]
            )
            
            return JsonResponse({
                'response': completion.choices[0].message.content
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
# 多模态语音对话
class Qwenomni(APIView):
    def post(self, request):
        try:
            client = OpenAI(
                api_key=config.QWEN_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            # 获取参数
            content_type = request.POST.get('type', 'text')  # text/image/audio/video
            text = request.POST.get('text', '')
            voice = request.POST.get('voice', config.DEFAULT_VOICE)
            url = request.POST.get('url', '')  # 获取URL参数
            
            # 获取对话历史
            messages = request.session.get('omni_dialog_history', [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "You are a helpful assistant."}]
                }
            ])
            
            # 构建消息内容
            if content_type == 'text':
                user_content = [{"type": "text", "text": text}]
            elif url:  # 处理URL方式
                if content_type == 'image':
                    user_content = [
                        {"type": "image_url", "image_url": {"url": url}},
                        {"type": "text", "text": text}
                    ]
                elif content_type == 'audio':
                    user_content = [
                        {"type": "input_audio", "input_audio": {"data": url, "format": "mp3"}},
                        {"type": "text", "text": text}
                    ]
                elif content_type == 'video':
                    user_content = [
                        {"type": "video_url", "video_url": {"url": url}},
                        {"type": "text", "text": text}
                    ]
            else:  # 处理文件上传方式
                file = request.FILES.get('file')
                if not file:
                    return JsonResponse({'error': '未上传文件'}, status=400)
                
                file_data = base64.b64encode(file.read()).decode('utf-8')
                
                if content_type == 'image':
                    user_content = [
                        {"type": "image_url", 
                         "image_url": {"url": f"data:image/jpeg;base64,{file_data}"}},
                        {"type": "text", "text": text}
                    ]
                elif content_type == 'audio':
                    user_content = [
                        {"type": "input_audio", 
                         "input_audio": {"data": f"data:;base64,{file_data}", "format": "mp3"}},
                        {"type": "text", "text": text}
                    ]
                elif content_type == 'video':
                    user_content = [
                        {"type": "video_url",
                         "video_url": {"url": f"data:;base64,{file_data}"}},
                        {"type": "text", "text": text}
                    ]
            
            # 添加用户消息到历史
            messages.append({"role": "user", "content": user_content})
            
            def stream_generator():
                completion = client.chat.completions.create(
                    model="qwen-omni-turbo",
                    messages=messages,
                    modalities=["text", "audio"],
                    audio={"voice": voice, "format": "wav"},
                    stream=True
                )
                
                assistant_response = []
                for chunk in completion:
                    if hasattr(chunk.choices[0].delta, "audio"):
                        try:
                            audio_data = chunk.choices[0].delta.audio['data']
                            assistant_response.append({"type": "audio", "audio": {"data": audio_data}})
                            yield f"audio:{audio_data}\n"
                        except Exception as e:
                            transcript = chunk.choices[0].delta.audio['transcript']
                            assistant_response.append({"type": "text", "text": transcript})
                            yield f"text:{transcript}\n"
                    elif hasattr(chunk.choices[0].delta, "content"):
                        content = chunk.choices[0].delta.content
                        if content:
                            assistant_response.append({"type": "text", "text": content})
                            yield f"text:{content}\n"
                
                # 添加助手回复到历史
                messages.append({"role": "assistant", "content": assistant_response})
                request.session['omni_dialog_history'] = messages
            
            return StreamingHttpResponse(stream_generator(), content_type='text/plain; charset=utf-8')
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# Qwen 音频理解
class QwenAudio(APIView):
    def post(self, request):
        try:
            # 从Constance配置获取API密钥
            api_key = config.QWEN_API_KEY
            
            # 设置DashScope客户端
            dashscope.api_key = api_key
            
            # 获取音频文件
            file = request.FILES.get('file')
            if not file:
                logger.warning('未提供音频文件')
                return JsonResponse({'error': '未提供音频文件'}, status=400)
            
            # 记录文件信息
            logger.info(f'接收到音频文件: {file.name}, 大小: {file.size} bytes')
            
            # 检查文件大小
            if file.size > 10 * 1024 * 1024:  # 10MB
                logger.warning(f'文件过大: {file.size} bytes')
                return JsonResponse({'error': '音频文件不能超过10MB'}, status=400)
            
            try:
                # 读取并编码文件
                file_data = file.read()
                base64_audio = base64.b64encode(file_data).decode('utf-8')
                audio_source = f"data:audio/wav;base64,{base64_audio}"
                logger.info('音频文件编码成功')
                
                # 构造消息内容
                messages = [
                    {
                        "role": "system",
                        "content": [
                            {
                                "text": "用最温柔的口气回复我"
                            }
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {"audio": audio_source},
                            {"text": "用最温柔的口气回复我"}
                        ]
                    }
                ]
                
                # 调用通义千问音频理解模型
                logger.info('开始调用千问API')
                response = dashscope.MultiModalConversation.call(
                    model="qwen-audio-turbo-latest",
                    messages=messages,
                    stream=False,
                    result_format="message"
                )
                logger.debug(f'完整API响应: {json.dumps(response, default=lambda o: o.__dict__)}')
                
                # 处理响应
                if response.status_code == 200:
                    try:
                        # 增强响应结构解析
                        content = response.output.choices[0].message.content
                        
                        # 处理不同响应格式
                        if isinstance(content, list):
                            # 合并所有文本内容
                            texts = [item.get('text', '') for item in content if 'text' in item]
                            combined_text = '\n'.join(filter(None, texts))
                        elif isinstance(content, dict):
                            combined_text = content.get('text', '')
                        else:
                            combined_text = str(content)
                        
                        if combined_text:
                            logger.info(f'成功获取回复内容: {combined_text[:200]}...')  # 截断长文本
                            return JsonResponse({'text': combined_text})
                        
                        logger.warning('响应内容为空')
                        return JsonResponse({'error': '未获取到有效回复'}, status=500)
                        
                    except Exception as e:
                        logger.error(f'解析响应失败: {str(e)}\n{traceback.format_exc()}')
                        return JsonResponse({'error': '处理响应时发生错误'}, status=500)
                else:
                    logger.error(f'千问API返回错误: {response.code} - {response.message}')
                    return JsonResponse({
                        'error': '音频处理服务暂时不可用',
                        'detail': response.message
                    }, status=503)
                
            except IOError as e:
                logger.error(f'文件处理错误: {str(e)}')
                return JsonResponse({'error': '文件读取失败'}, status=500)
            finally:
                file.close()  # 确保文件资源释放
                
        except Exception as e:
            logger.error(f'系统错误: {str(e)}\n{traceback.format_exc()}')
            return JsonResponse({'error': '服务器内部错误'}, status=500)

    @action(detail=False, methods=['get'])
    def test_audio_api(self, request):
        try:
            # 使用官方示例音频测试
            test_audio_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
            
            messages = [{
                "role": "user",
                "content": [
                    {"audio": test_audio_url},
                    {"text": "这段音频在说什么?"}
                ]
            }]
            
            response = dashscope.MultiModalConversation.call(
                model="qwen-audio-turbo-latest",
                messages=messages,
                result_format="message"
            )
            
            return JsonResponse({
                'status': 'success',
                'response': response.output.choices[0].message.content[0].text
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def rename_files_in_jd(request):
    """处理文件重命名的视图函数，根据规则清理文件名"""
    try:
        import os
        import logging
        logger = logging.getLogger('ai_app')
        
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # jd 文件夹位于上一级目录下，使用相对路径
        jd_dir = os.path.abspath(os.path.join(current_dir, "..", "jd"))
        
        if not os.path.exists(jd_dir):
            logger.error(f"找不到文件夹: {jd_dir}")
            return JsonResponse({
                'status': 'error',
                'message': f'找不到文件夹: {jd_dir}'
            })
            
        logger.info(f"开始清理文件夹: {jd_dir}")
        
        # 定义匹配规则列表，每个元组为 (关键字, 新文件名)
        rules = [
            ("词下表现", "词下表现"),
            ("商品诊断", "商品诊断"),
            ("整体看板", "整体看板"),
            ("地域分析", "地域分析"),
            ("品牌流量", "品牌流量"),
            ("新秀", "新秀模糊搜索词排行"),
            ("飙升", "飙升模糊搜索词排行"),
            ("热点", "热点模糊搜索词排行"),
            ("竞争分析", "竞争分析"),
            ("站营销", "营销概况"),
            ("矩阵分析", "矩阵分析"),
            ("实时概况", "实时概况"),
            ("流量总览", "流量总览"),
            ("交易概况", "交易概况"),
            ("类型分析", "类型分析"),
            ("核心数据", "核心数据"),
            ("达人分析", "达人分析"),
            ("来源分析", "来源分析"),
            ("内容分析", "内容分析"),
            ("商品分析", "商品分析"),
            ("商品概况", "商品概况"),
            ("库存", "库存概况")
        ]
        
        renamed_count = 0
        error_count = 0
        skipped_count = 0
        renamed_files = []
        error_files = []
        
        # 递归遍历 jd 文件夹中的所有文件
        for root, dirs, files in os.walk(jd_dir):
            for filename in files:
                old_file_path = os.path.join(root, filename)
                # 遍历每个规则，若文件名中包含指定关键字则确定新文件名
                new_base = None
                matching_rule = None
                
                for key, new_name in rules:
                    if key in filename:
                        new_base = new_name
                        matching_rule = key
                        break
                
                if new_base:
                    # 保留原文件扩展名
                    ext = os.path.splitext(filename)[1]
                    new_filename = new_base + ext
                    new_file_path = os.path.join(root, new_filename)
                    
                    # 如果新旧文件名相同，跳过重命名
                    if filename == new_filename:
                        logger.info(f"跳过文件: '{filename}' (已经是标准命名)")
                        skipped_count += 1
                        continue
                        
                    try:
                        os.rename(old_file_path, new_file_path)
                        renamed_count += 1
                        renamed_files.append({
                            'old_name': filename,
                            'new_name': new_filename,
                            'rule': matching_rule
                        })
                        logger.info(f"清理文件: '{filename}' -> '{new_filename}' (规则: {matching_rule})")
                    except Exception as e:
                        error_count += 1
                        error_files.append({
                            'filename': filename,
                            'error': str(e)
                        })
                        logger.error(f"重命名文件 '{filename}' 时发生错误: {e}")
                else:
                    logger.info(f"跳过文件: '{filename}' (不符合任何规则)")
                    skipped_count += 1

        # 记录详细日志
        logger.info(f"文件清理完成: 成功={renamed_count}, 失败={error_count}, 跳过={skipped_count}")
        if renamed_count > 0:
            logger.info(f"重命名文件列表: {renamed_files}")
        if error_count > 0:
            logger.info(f"失败文件列表: {error_files}")

        return JsonResponse({
            'status': 'success',
            'renamed': renamed_count,
            'errors': error_count,
            'skipped': skipped_count,
            'details': {
                'renamed_files': renamed_files[:20],  # 限制数量避免响应过大
                'error_files': error_files[:20]
            }
        })
        
    except Exception as e:
        logger.error(f"文件清理过程发生错误: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def auto_upload_files(request):
    """自动扫描jd文件夹，根据文件名匹配模型并上传到数据库"""
    logger = logging.getLogger('ai_app')
    
    try:
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # jd 文件夹位于上一级目录下，使用相对路径
        jd_dir = os.path.abspath(os.path.join(current_dir, "..", "jd"))
        
        logger.info(f"当前脚本目录: {current_dir}")
        logger.info(f"目标JD目录: {jd_dir}")
        
        if not os.path.exists(jd_dir):
            logger.error(f"找不到文件夹: {jd_dir}")
            return JsonResponse({
                'status': 'error',
                'message': f'找不到文件夹: {jd_dir}'
            })
            
        logger.info(f"开始自动扫描文件夹: {jd_dir}")
        
        # 定义文件名到模型和类别、子类别的映射
        file_model_mapping = {
            # 京麦商品搜索看板
            "词下表现": {
                "model": JDKeywordData, 
                "category": "京麦商品搜索看板", 
                "subcategory": "热搜词",
                "handler": "_save_to_jd_keyword_data"
            },
            "商品诊断": {
                "model": JDProductDiagnosis, 
                "category": "京麦商品搜索看板", 
                "subcategory": "商品诊断",
                "handler": "_save_to_jd_product_diagnosis"
            },
            # 京准通行业大盘
            "整体看板": {
                "model": JDOverallDashboard, 
                "category": "京准通行业大盘", 
                "subcategory": "整体看板",
                "handler": "_save_to_jd_overall_dashboard"
            },
            "地域分析": {
                "model": JDRegionalAnalysis, 
                "category": "京准通行业大盘", 
                "subcategory": "地域分析",
                "handler": "_save_to_jd_regional_analysis"
            },
            "品牌流量": {
                "model": JDBrandTraffic, 
                "category": "京准通行业大盘", 
                "subcategory": "品牌流量",
                "handler": "_save_to_jd_brand_traffic"
            },
            "新秀模糊搜索词排行": {
                "model": JDRisingSearchWords, 
                "category": "京准通行业大盘", 
                "subcategory": "新秀搜索词排行",
                "handler": "_save_to_jd_rising_search_words"
            },
            "飙升模糊搜索词排行": {
                "model": JDSurgingSearchWords, 
                "category": "京准通行业大盘", 
                "subcategory": "飙升搜索词排行",
                "handler": "_save_to_jd_surging_search_words"
            },
            "热点模糊搜索词排行": {
                "model": JDHotSearchWords, 
                "category": "京准通行业大盘", 
                "subcategory": "热点搜索词排行",
                "handler": "_save_to_jd_hot_search_words"
            },
            # 京准通其他数据
            "竞争分析": {
                "model": JDCompetitionAnalysis, 
                "category": "京准通其他数据", 
                "subcategory": "竞争分析",
                "handler": "_save_to_jd_competition_analysis"
            },
            "营销概况": {
                "model": JDMarketingOverview, 
                "category": "京准通其他数据", 
                "subcategory": "营销概况",
                "handler": "_save_to_jd_marketing_overview"
            },
            "矩阵分析": {
                "model": JDMatrixAnalysis, 
                "category": "京准通其他数据", 
                "subcategory": "矩阵分析",
                "handler": "_save_to_jd_matrix_analysis"
            },
            # 商智基本数据
            "实时概况": {
                "model": JDRealTimeData, 
                "category": "商智基本数据", 
                "subcategory": "实时",
                "handler": "_save_to_jd_real_time_data"
            },
            "流量总览": {
                "model": JDTrafficData, 
                "category": "商智基本数据", 
                "subcategory": "流量",
                "handler": "_save_to_jd_traffic_data"
            },
            "交易概况": {
                "model": JDTransactionData, 
                "category": "商智基本数据", 
                "subcategory": "交易",
                "handler": "_save_to_jd_transaction_data"
            },
            # 商智内容数据
            "类型分析": {
                "model": JDContentTypeAnalysis, 
                "category": "商智内容数据", 
                "subcategory": "类型分析",
                "handler": "_save_to_jd_content_type_analysis"
            },
            "核心数据": {
                "model": JDCoreContentData, 
                "category": "商智内容数据", 
                "subcategory": "核心数据",
                "handler": "_save_to_jd_core_content_data"
            },
            "达人分析": {
                "model": JDInfluencerAnalysis, 
                "category": "商智内容数据", 
                "subcategory": "达人分析",
                "handler": "_save_to_jd_influencer_analysis"
            },
            "来源分析": {
                "model": JDSourceAnalysis, 
                "category": "商智内容数据", 
                "subcategory": "来源分析",
                "handler": "_save_to_jd_source_analysis"
            },
            "内容分析": {
                "model": JDContentAnalysis, 
                "category": "商智内容数据", 
                "subcategory": "内容分析",
                "handler": "_save_to_jd_content_analysis"
            },
            "商品分析": {
                "model": JDProductAnalysis, 
                "category": "商智内容数据", 
                "subcategory": "商品分析",
                "handler": "_save_to_jd_product_analysis"
            },
            # 商智产品数据
            "商品概况": {
                "model": JDProductOverview, 
                "category": "商智产品数据", 
                "subcategory": "商品概况",
                "handler": "_save_to_jd_product_overview"
            },
            "库存概况": {
                "model": JDInventoryData, 
                "category": "商智产品数据", 
                "subcategory": "库存",
                "handler": "_save_to_jd_inventory_data"
            },
            # 新增映射 - 八爪鱼和EasySpider数据
            "京东商品搜索": {
                "model": JDOctopusProductSearch,
                "category": "八爪鱼",
                "subcategory": "京东商品搜索",
                "handler": "_save_to_jd_octopus_product_search"
            },
            "京麦采集": {
                "model": JDOctopusJingmaiData,
                "category": "八爪鱼",
                "subcategory": "京麦采集",
                "handler": "_save_to_jd_octopus_jingmai_data"
            },
            "Easy京麦采集": {
                "model": JDEasySpiderData,
                "category": "EasySpider",
                "subcategory": "Easy京麦采集",
                "handler": "_save_to_jd_easy_spider_data"
            }
        }
        
        # 记录所有可能的匹配关键字
        logger.info(f"可匹配的文件名关键字: {list(file_model_mapping.keys())}")
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        processed_files = []
        all_found_files = []
        skipped_files = []  # 新增：记录被跳过的文件
        failed_files = []   # 新增：记录处理失败的文件
        
        # 获取JDDataUploadView实例用于处理上传
        upload_handler = JDDataUploadView()
        
        # 先列出找到的所有文件
        for root, dirs, files in os.walk(jd_dir):
            logger.info(f"正在扫描目录: {root}")
            logger.info(f"发现子目录: {dirs}")
            logger.info(f"发现文件: {files}")
            
            for filename in files:
                file_path = os.path.join(root, filename)
                file_ext = os.path.splitext(filename)[1].lower()
                file_size = os.path.getsize(file_path)
                all_found_files.append({
                    'name': filename,
                    'path': file_path,
                    'extension': file_ext,
                    'size': file_size
                })
        
        logger.info(f"共找到 {len(all_found_files)} 个文件")
        
        # 递归遍历jd文件夹中的所有文件
        for root, dirs, files in os.walk(jd_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                file_base_name = os.path.splitext(filename)[0]
                file_ext = os.path.splitext(filename)[1].lower()
                
                logger.info(f"处理文件: {filename}")
                logger.info(f"  文件路径: {file_path}")
                logger.info(f"  文件基本名: {file_base_name}")
                logger.info(f"  文件扩展名: {file_ext}")
                
                # 只处理CSV和Excel文件
                if file_ext not in ['.csv', '.xlsx', '.xls']:
                    logger.info(f"跳过非数据文件: {filename} (扩展名: {file_ext})")
                    skipped_count += 1
                    skipped_files.append({
                        'filename': filename,
                        'reason': f"不支持的文件格式: {file_ext}"
                    })
                    continue
                
                # 检查文件是否匹配任何模型
                matched_model = None
                for key, mapping in file_model_mapping.items():
                    if key == file_base_name:
                        matched_model = mapping
                        break
                
                if matched_model:
                    try:
                        logger.info(f"处理文件: {filename} (匹配模型: {matched_model['model'].__name__})")
                        
                        # 读取文件
                        if file_ext == '.csv':
                            # 创建临时文件以便检测编码
                            temp_dir = tempfile.gettempdir()
                            temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.csv")
                            
                            # 保存上传的文件到临时文件
                            with open(file_path, 'rb') as src, open(temp_file_path, 'wb') as dst:
                                dst.write(src.read())
                            
                            # 检测文件编码
                            with open(temp_file_path, 'rb') as f:
                                result = chardet.detect(f.read())
                            
                            # 尝试使用检测到的编码读取文件
                            detected_encoding = result['encoding'] or 'gbk'  # 默认使用GBK
                            logger.info(f"检测到文件编码: {detected_encoding}")
                            
                            try:
                                df = pd.read_csv(temp_file_path, encoding=detected_encoding)
                            except UnicodeDecodeError:
                                # 如果检测到的编码不正确，尝试其他常见编码
                                encodings_to_try = ['gbk', 'gb2312', 'gb18030', 'utf-8-sig', 'utf-8', 'latin1']
                                for encoding in encodings_to_try:
                                    try:
                                        df = pd.read_csv(temp_file_path, encoding=encoding)
                                        logger.info(f"成功使用 {encoding} 编码读取文件")
                                        break
                                    except UnicodeDecodeError:
                                        continue
                                    except Exception as e:
                                        logger.error(f"使用 {encoding} 读取时发生错误: {str(e)}")
                                        continue
                                else:
                                    # 如果所有编码都失败
                                    raise UnicodeDecodeError("无法检测到正确的文件编码")
                            
                            # 清理临时文件
                            try:
                                os.remove(temp_file_path)
                            except:
                                pass
                        else:
                            df = pd.read_excel(file_path)
                        
                        # 获取处理器方法名
                        handler_method = getattr(upload_handler, matched_model['handler'])
                        
                        # 调用相应的处理器方法保存数据
                        handler_method(df, request.user)
                        
                        success_count += 1
                        processed_files.append({
                            'filename': filename,
                            'model': matched_model['model'].__name__,
                            'category': matched_model['category'],
                            'subcategory': matched_model['subcategory']
                        })
                        
                        logger.info(f"成功处理文件: {filename}")
                    except Exception as e:
                        failed_count += 1
                        failed_files.append({
                            'filename': filename,
                            'error': str(e)
                        })
                        logger.error(f"处理文件 {filename} 时发生错误: {str(e)}")
                else:
                    skipped_count += 1
                    logger.info(f"跳过文件: {filename} (未找到匹配模型)")
                    skipped_files.append({
                        'filename': filename,
                        'reason': "未找到匹配的模型"
                    })
        
        logger.info(f"自动上传完成: 成功={success_count}, 失败={failed_count}, 跳过={skipped_count}")
        
        return JsonResponse({
            'status': 'success',
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count,
            'processed': processed_files,
            'skipped_files': skipped_files,
            'failed_files': failed_files
        })
        
    except Exception as e:
        logger.error(f"自动上传过程发生错误: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def save_analysis_to_file(request):
    """保存AI分析结果到运营建议.md文件"""
    logger = logging.getLogger('ai_app')
    
    try:
        # 解析请求数据
        data = json.loads(request.body)
        content = data.get('content', '')
        date = data.get('date', '')
        
        if not content:
            return JsonResponse({'success': False, 'error': '分析内容为空'})
        
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # jd 文件夹位于上一级目录下，使用相对路径
        jd_dir = os.path.abspath(os.path.join(current_dir, "..", "jd"))
        
        if not os.path.exists(jd_dir):
            os.makedirs(jd_dir, exist_ok=True)
            logger.info(f"创建目录: {jd_dir}")
        
        # 构建文件路径
        file_path = os.path.join(jd_dir, "运营建议.md")
        
        # 格式化分析内容，添加日期标题
        formatted_content = f"\n\n## {date}的数据分析\n\n{content}\n"
        
        # 追加内容到文件
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(formatted_content)
        
        logger.info(f"成功保存分析结果到: {file_path}")
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"保存分析结果时出错: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})