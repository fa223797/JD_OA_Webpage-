# ai
from django.contrib.auth.models import User, AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import os
import mimetypes
from django.contrib.auth import get_user_model

# 模型信息表
class ModelInfo(models.Model):
    ''' 
    模型信息表，用于存储AI模型的基本信息
    '''
    MODEL_TYPES = (
        ('chat', '大语言模型'),
        ('vision', '多模态模型'),
        ('ocr', '文字识别'),
        ('file', '文档理解'),
        ('audio', '语音理解')
    )

    model = models.TextField(verbose_name="模型标识")
    name = models.TextField(verbose_name="模型名称")
    type = models.CharField(
        max_length=20,
        choices=MODEL_TYPES,
        default='chat',
        verbose_name="模型类型"
    )
    context = models.TextField(verbose_name="模型描述")
    cost = models.TextField(verbose_name="费用说明")
    api_endpoint = models.CharField(
        max_length=255,
        verbose_name="接口路径",
        default='/api/vision/'
    )
    
    def __str__(self):
        return f"{self.name} - {self.model} - {self.type} - {self.context} - {self.cost}"
    
    class Meta:
        db_table = "ai_model_info"
        verbose_name = "所有接口配置"
        verbose_name_plural = verbose_name

# 媒体资料列表
class UploadedFile(models.Model):
    """上传文件模型"""
    FILE_TYPES = (
        ('image', '图片'),
        ('audio', '音频'),
        ('video', '视频'),
        ('document', '文档'),
        ('other', '其他')
    )

    file = models.FileField(
        upload_to='uploads/%Y/%m/%d/',
        verbose_name="文件"
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="文件名"
    )
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        editable=False,
        verbose_name="文件类型"
    )
    file_size = models.IntegerField(
        verbose_name="文件大小(字节)"
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name="MIME类型"
    )
    upload_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="上传时间"
    )
    uploader = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name="上传者",
        related_name='uploaded_files',
        default=1  # 设置默认用户ID
    )
    
    def save(self, *args, **kwargs):
        if not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        else:
            # 如果指定了新文件名，保持原扩展名
            original_ext = os.path.splitext(self.file.name)[1]
            new_name = os.path.splitext(self.file_name)[0]
            self.file_name = f"{new_name}{original_ext}"
        
        # 自动判断文件类型
        ext = os.path.splitext(self.file.name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            self.file_type = 'image'
        elif ext in ['.mp3', '.wav', '.ogg', '.m4a', '.flac']:
            self.file_type = 'audio'
        elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.webm']:
            self.file_type = 'video'
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.md', '.markdown']:
            self.file_type = 'document'
        else:
            self.file_type = 'other'
            
        # 设置文件大小
        if not self.file_size:
            self.file_size = self.file.size
            
        # 设置MIME类型
        if not self.mime_type:
            mime_type, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = mime_type or 'application/octet-stream'
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.file_name

    class Meta:
        db_table = 'ai_app_uploadedfile'  # 指定表名
        verbose_name = "多媒体资料"
        verbose_name_plural = verbose_name
        ordering = ['-upload_time']

# =========================京东数据统一表=========================
class JDData(models.Model):
    """京东数据统一表 - 包含所有京东数据字段"""
    # 通用字段
    upload_date = models.DateTimeField('上传日期', auto_now_add=True)
    category = models.CharField('数据类别', max_length=50, null=True, blank=True, choices=[
        ('京麦商品搜索看板', '京麦商品搜索看板'),
        ('京准通行业大盘', '京准通行业大盘'),
        ('京准通其他数据', '京准通其他数据'),
        ('商智基本数据', '商智基本数据'),
        ('商智内容数据', '商智内容数据'),
        ('商智产品数据', '商智产品数据'),
        ('八爪鱼', '八爪鱼'),
        ('EasySpider', 'EasySpider'),
    ])
    subcategory = models.CharField('子类别', max_length=50, null=True, blank=True)
    file = models.FileField('数据文件', upload_to='jd_data/', null=True, blank=True)
    
    # 商品基本信息
    product_info = models.TextField(verbose_name="商品信息", null=True, blank=True)
    
    # 词下表现数据字段
    search_keyword = models.CharField(max_length=255, verbose_name="搜索词", null=True, blank=True)
    traffic_contribution = models.CharField(max_length=50, verbose_name="流量贡献占比", null=True, blank=True)
    keyword_rank = models.CharField(max_length=50, verbose_name="词下排名", null=True, blank=True)
    
    # 主曝光图商品数据字段
    main_exposure_product = models.TextField(verbose_name="主曝光图商品", null=True, blank=True)
    search_performance = models.CharField(max_length=50, verbose_name="搜索表现总分", null=True, blank=True)
    traffic_acquisition = models.CharField(max_length=50, verbose_name="流量获取力", null=True, blank=True)
    traffic_conversion = models.CharField(max_length=50, verbose_name="流量承接力", null=True, blank=True)

    def __str__(self):
        if self.search_keyword:
            return f"{self.category}-{self.subcategory}-{self.search_keyword}"
        return f"{self.category}-{self.subcategory}-{self.upload_date}"
    
    @classmethod
    def log_upload(cls, category, subcategory, file_name, record_count=None, user=None):
        """记录数据上传日志"""
        import logging
        logger = logging.getLogger('ai_app')
        
        user_info = f"用户: {user.username}" if user else "未知用户"
        count_info = f", 记录数: {record_count}" if record_count is not None else ""
        logger.info(f"数据上传 - 类别: {category}, 子类别: {subcategory}, 文件: {file_name}{count_info}, {user_info}")
    
    @classmethod
    def log_upload_error(cls, category, subcategory, file_name, error_msg, user=None):
        """记录数据上传错误日志"""
        import logging
        logger = logging.getLogger('ai_app')
        
        user_info = f"用户: {user.username}" if user else "未知用户"
        logger.error(f"数据上传错误 - 类别: {category}, 子类别: {subcategory}, 文件: {file_name}, 错误: {error_msg}, {user_info}")
    
    class Meta:
        db_table = "jd_data"
        verbose_name = "京东数据"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']
        permissions = [
            ("can_upload_jd_data", "Can upload JD data files"),
            ("can_rename_files", "Can rename JD data files"),
            ("can_auto_upload", "Can auto upload JD data files"),
        ]

# 京麦商品搜索看板 - 热搜词
class JDKeywordData(models.Model):
    search_keyword = models.CharField(max_length=255, verbose_name="搜索词", null=True, blank=True)
    traffic_contribution = models.CharField(max_length=100, blank=True, null=True, verbose_name="流量贡献占比")
    keyword_rank = models.CharField(max_length=100, blank=True, null=True, verbose_name="词下排名")
    product_info = models.TextField(blank=True, null=True, verbose_name="商品信息")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "京麦词下表现"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.search_keyword or '未知搜索词'} ({self.upload_date.strftime('%Y-%m-%d')})"

# 京麦商品搜索看板 - 商品诊断
class JDProductDiagnosis(models.Model):
    main_exposure_product = models.TextField(verbose_name="主曝光图商品", null=True, blank=True)
    search_performance = models.CharField(max_length=100, blank=True, null=True, verbose_name="搜索表现总分")
    traffic_acquisition = models.CharField(max_length=100, blank=True, null=True, verbose_name="流量获取力")
    traffic_conversion = models.CharField(max_length=100, blank=True, null=True, verbose_name="流量承接力")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "京麦商品诊断数据"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"商品诊断 ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通行业大盘 - 整体看板
class JDOverallDashboard(models.Model):
    click_time = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击时间")
    impression_index = models.CharField(max_length=100, blank=True, null=True, verbose_name="展现指数")
    click_index = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击指数")
    click_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击率")
    cart_index = models.CharField(max_length=100, blank=True, null=True, verbose_name="加购指数")
    cart_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="加购率")
    conversion_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="转化率")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "京准通整体看板数据"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"整体看板 ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通行业大盘 - 地域分析
class JDRegionalAnalysis(models.Model):
    region_name = models.CharField(max_length=100, verbose_name="地域名称", null=True, blank=True)
    impression_index = models.CharField(max_length=100, blank=True, null=True, verbose_name="展现指数")
    click_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击率")
    conversion_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="转化率")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "京准通地域分析数据"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.region_name or '未知地域'} ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通行业大盘 - 品牌流量
class JDBrandTraffic(models.Model):
    main_brand_name = models.CharField(max_length=255, verbose_name="主品牌名称", null=True, blank=True)
    traffic_rank = models.CharField(max_length=100, blank=True, null=True, verbose_name="流量排名")
    click_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击率")
    conversion_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="转化率")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "京准通品牌流量总览"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.main_brand_name} ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通行业大盘 - 搜索词排行（基类）
class JDSearchWordsBase(models.Model):
    keyword = models.CharField(max_length=255, verbose_name="关键词", null=True, blank=True)
    search_index = models.CharField(max_length=100, blank=True, null=True, verbose_name="搜索指数")
    competition = models.CharField(max_length=100, blank=True, null=True, verbose_name="竞争力")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        abstract = True

# 京准通行业大盘 - 新秀搜索词排行
class JDRisingSearchWords(JDSearchWordsBase):
    class Meta:
        verbose_name = "京准通新秀搜索词排行"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"新秀搜索词: {self.keyword} ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通行业大盘 - 飙升搜索词排行
class JDSurgingSearchWords(JDSearchWordsBase):
    class Meta:
        verbose_name = "京准通飙升搜索词排行"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"飙升搜索词: {self.keyword} ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通行业大盘 - 热点搜索词排行
class JDHotSearchWords(JDSearchWordsBase):
    class Meta:
        verbose_name = "京准通热点搜索词排行"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"热点搜索词: {self.keyword} ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通其他数据 - 竞争分析
class JDCompetitionAnalysis(models.Model):
    click_time = models.CharField(max_length=100, verbose_name="点击时间")
    brand_name = models.CharField(max_length=200, verbose_name="品牌名称")
    impression_count = models.FloatField(verbose_name="展现量")
    brand_type = models.CharField(max_length=20, verbose_name="品牌类型",
                                choices=[
                                    ('competitor', '竞品品牌'),
                                    ('industry', '行业品牌'),
                                    ('self', '自身品牌')
                                ])
    upload_date = models.DateTimeField(verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="上传用户")
    
    class Meta:
        verbose_name = "京东竞争分析数据"
        verbose_name_plural = verbose_name

# 京准通其他数据 - 营销概况
class JDMarketingOverview(models.Model):
    campaign_time = models.CharField(max_length=100, blank=True, null=True, verbose_name="投放时间")
    cost = models.CharField(max_length=100, blank=True, null=True, verbose_name="花费")
    impressions = models.CharField(max_length=100, blank=True, null=True, verbose_name="展现数")
    clicks = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击数")
    avg_click_cost = models.CharField(max_length=100, blank=True, null=True, verbose_name="平均点击成本")
    cpm = models.CharField(max_length=100, blank=True, null=True, verbose_name="千次展现成本")
    click_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击率")
    total_orders = models.CharField(max_length=100, blank=True, null=True, verbose_name="总订单行")
    total_order_amount = models.CharField(max_length=100, blank=True, null=True, verbose_name="总订单金额")
    total_cart_adds = models.CharField(max_length=100, blank=True, null=True, verbose_name="总加购数")
    conversion_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="转化率")
    avg_order_cost = models.CharField(max_length=100, blank=True, null=True, verbose_name="平均订单成本")
    roi = models.CharField(max_length=100, blank=True, null=True, verbose_name="投产比")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "京准通营销概况数据"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"营销概况 ({self.upload_date.strftime('%Y-%m-%d')})"

# 京准通其他数据 - 矩阵分析
class JDMatrixAnalysis(models.Model):
    product_line = models.CharField(max_length=255, blank=True, null=True, verbose_name="产品线")
    click_time = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击时间")
    cost = models.CharField(max_length=100, blank=True, null=True, verbose_name="花费")
    impressions = models.CharField(max_length=100, blank=True, null=True, verbose_name="展现数")
    clicks = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击数")
    click_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="点击率")
    avg_click_cost = models.CharField(max_length=100, blank=True, null=True, verbose_name="平均点击成本")
    cpm = models.CharField(max_length=100, blank=True, null=True, verbose_name="千次展现成本")
    total_orders = models.CharField(max_length=100, blank=True, null=True, verbose_name="总订单行")
    total_order_amount = models.CharField(max_length=100, blank=True, null=True, verbose_name="总订单金额")
    total_cart_adds = models.CharField(max_length=100, blank=True, null=True, verbose_name="总加购数")
    conversion_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="转化率")
    cart_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="加购率")
    avg_order_cost = models.CharField(max_length=100, blank=True, null=True, verbose_name="平均订单成本")
    roi = models.CharField(max_length=100, blank=True, null=True, verbose_name="投产比")
    direct_orders = models.CharField(max_length=100, blank=True, null=True, verbose_name="直接订单行")
    direct_order_amount = models.CharField(max_length=100, blank=True, null=True, verbose_name="直接订单金额")
    direct_cart_adds = models.CharField(max_length=100, blank=True, null=True, verbose_name="直接加购数")
    indirect_orders = models.CharField(max_length=100, blank=True, null=True, verbose_name="间接订单行")
    indirect_order_amount = models.CharField(max_length=100, blank=True, null=True, verbose_name="间接订单金额")
    indirect_cart_adds = models.CharField(max_length=100, blank=True, null=True, verbose_name="间接加购数")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "京准通矩阵分析数据"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"矩阵分析: {self.product_line or '无产品线'} ({self.upload_date.strftime('%Y-%m-%d')})"

# 商智基本数据 - 实时
class JDRealTimeData(models.Model):
    date = models.CharField(max_length=100, verbose_name="时间")
    page_views = models.IntegerField(default=0, verbose_name="浏览量")
    comp_page_views = models.IntegerField(default=0, verbose_name="浏览量(对比日)")
    page_views_compare = models.FloatField(default=0, verbose_name="较对比日")
    visitor_count = models.IntegerField(default=0, verbose_name="访客数")
    comp_visitor_count = models.IntegerField(default=0, verbose_name="访客数(对比日)")
    visitor_compare = models.FloatField(default=0, verbose_name="较对比日")
    
    # 成交相关
    paid_count = models.IntegerField(default=0, verbose_name="成交人数")
    comp_paid_count = models.IntegerField(default=0, verbose_name="成交人数(对比日)")
    paid_compare = models.FloatField(default=0, verbose_name="较对比日")
    conversion_rate = models.FloatField(default=0, verbose_name="成交转化率")
    comp_conversion_rate = models.FloatField(default=0, verbose_name="成交转化率(对比日)")
    conversion_rate_compare = models.FloatField(default=0, verbose_name="较对比日")
    
    # 成交商品
    paid_items = models.IntegerField(default=0, verbose_name="成交商品件数")
    comp_paid_items = models.IntegerField(default=0, verbose_name="成交商品件数(对比日)")
    paid_items_compare = models.FloatField(default=0, verbose_name="较对比日")
    order_count = models.IntegerField(default=0, verbose_name="成交单量")
    comp_order_count = models.IntegerField(default=0, verbose_name="成交单量(对比日)")
    order_count_compare = models.FloatField(default=0, verbose_name="较对比日")
    
    # 成交金额
    order_amount = models.FloatField(default=0, verbose_name="成交金额")
    comp_order_amount = models.FloatField(default=0, verbose_name="成交金额(对比日)")
    order_amount_compare = models.FloatField(default=0, verbose_name="较对比日")
    customer_price = models.FloatField(default=0, verbose_name="成交客单价")
    comp_customer_price = models.FloatField(default=0, verbose_name="成交客单价(对比日)")
    customer_price_compare = models.FloatField(default=0, verbose_name="较对比日")
    
    # 加购相关
    cart_user_count = models.IntegerField(default=0, verbose_name="加购客户数")
    comp_cart_user_count = models.IntegerField(default=0, verbose_name="加购客户数(对比日)")
    cart_user_compare = models.FloatField(default=0, verbose_name="较对比日")
    cart_items = models.IntegerField(default=0, verbose_name="加购商品件数")
    comp_cart_items = models.IntegerField(default=0, verbose_name="加购商品件数(对比日)")
    cart_items_compare = models.FloatField(default=0, verbose_name="较对比日")
    
    # 加购正负向
    pos_cart_items = models.IntegerField(default=0, verbose_name="加购商品件数(正向)")
    comp_pos_cart_items = models.IntegerField(default=0, verbose_name="加购商品件数(正向)(对比日)")
    pos_cart_items_compare = models.FloatField(default=0, verbose_name="较对比日")
    neg_cart_items = models.IntegerField(default=0, verbose_name="加购商品件数(负向)")
    comp_neg_cart_items = models.IntegerField(default=0, verbose_name="加购商品件数(负向)(对比日)")
    neg_cart_items_compare = models.FloatField(default=0, verbose_name="较对比日")
    
    # UV价值
    uv_value = models.FloatField(default=0, verbose_name="UV价值")
    comp_uv_value = models.FloatField(default=0, verbose_name="UV价值(对比日)")
    uv_value_compare = models.FloatField(default=0, verbose_name="较对比日")
    
    # 上传信息
    upload_date = models.DateTimeField(verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="上传用户")
    
    class Meta:
        verbose_name = "京东实时概况"
        verbose_name_plural = verbose_name

# 商智基本数据 - 流量
class JDTrafficData(models.Model):
    date = models.CharField(max_length=100, blank=True, null=True, verbose_name="日期")
    visitor_count = models.CharField(max_length=100, blank=True, null=True, verbose_name="访客数")
    page_views = models.CharField(max_length=100, blank=True, null=True, verbose_name="浏览量")
    views_per_visitor = models.CharField(max_length=100, blank=True, null=True, verbose_name="人均浏览量")
    stay_duration = models.CharField(max_length=100, blank=True, null=True, verbose_name="平均停留时长")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "商智流量总览"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"流量总览 ({self.upload_date.strftime('%Y-%m-%d')})"

# 商智基本数据 - 交易
class JDTransactionData(models.Model):
    date = models.CharField(max_length=100, blank=True, null=True, verbose_name="日期")
    page_views = models.CharField(max_length=100, blank=True, null=True, verbose_name="浏览量")
    visitor_count = models.CharField(max_length=100, blank=True, null=True, verbose_name="访客数")
    transaction_users = models.CharField(max_length=100, blank=True, null=True, verbose_name="成交人数")
    conversion_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="成交转化率")
    order_count = models.CharField(max_length=100, blank=True, null=True, verbose_name="成交单量")
    product_count = models.CharField(max_length=100, blank=True, null=True, verbose_name="成交商品件数")
    transaction_amount = models.CharField(max_length=100, blank=True, null=True, verbose_name="成交金额")
    average_order_value = models.CharField(max_length=100, blank=True, null=True, verbose_name="成交客单价")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "商智交易概况"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"交易概况 ({self.upload_date.strftime('%Y-%m-%d')})"

# 商智内容数据 - 类型分析
class JDContentTypeAnalysis(models.Model):
    date = models.CharField(max_length=50, verbose_name="日期")
    content_type = models.CharField(max_length=50, verbose_name="内容类型")
    online_content_guide = models.FloatField(default=0, verbose_name="在线内容引导进商")
    guide_merchant = models.FloatField(default=0, verbose_name="引导进商")
    guide_cart = models.FloatField(default=0, verbose_name="引导加购")
    same_day_guide = models.FloatField(default=0, verbose_name="当日引导")
    same_day_order = models.FloatField(default=0, verbose_name="当日引导成交单量")
    seven_day_guide = models.FloatField(default=0, verbose_name="7日引导成")
    seven_day_order = models.FloatField(default=0, verbose_name="7日引导成交单量")
    data_content = models.TextField(null=True, blank=True, verbose_name="数据内容")
    upload_date = models.DateTimeField(verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="上传用户")
    
    class Meta:
        verbose_name = "京东内容类型分析数据"
        verbose_name_plural = verbose_name

# 商智内容数据 - 核心数据
class JDCoreContentData(models.Model):
    date = models.CharField(max_length=100, blank=True, null=True, verbose_name="日期")
    content_data = models.TextField(blank=True, null=True, verbose_name="内容数据")
    online_content_count = models.CharField(max_length=100, blank=True, null=True, verbose_name="在线内容数")
    online_content_sku_coverage = models.CharField(max_length=100, blank=True, null=True, verbose_name="在线内容覆盖sku数")
    new_content_count = models.CharField(max_length=100, blank=True, null=True, verbose_name="新增内容数")
    new_content_sku_coverage = models.CharField(max_length=100, blank=True, null=True, verbose_name="新增内容覆盖sku数")
    content_views = models.CharField(max_length=100, blank=True, null=True, verbose_name="内容浏览量")
    content_visitors = models.CharField(max_length=100, blank=True, null=True, verbose_name="内容访客数")
    avg_stay_time = models.CharField(max_length=100, blank=True, null=True, verbose_name="人均停留时长")
    guide_detail_visitors = models.CharField(max_length=100, blank=True, null=True, verbose_name="引导进商详访客数")
    guide_detail_views = models.CharField(max_length=100, blank=True, null=True, verbose_name="引导进商详浏览量")
    guide_cart_users = models.CharField(max_length=100, blank=True, null=True, verbose_name="引导加购人数")
    guide_cart_times = models.CharField(max_length=100, blank=True, null=True, verbose_name="引导加购次数")
    daily_guide_order_amount = models.CharField(max_length=100, blank=True, null=True, verbose_name="当日引导成交金额")
    daily_guide_order_users = models.CharField(max_length=100, blank=True, null=True, verbose_name="当日引导成交人数")
    daily_guide_order_count = models.CharField(max_length=100, blank=True, null=True, verbose_name="当日引导成交单量")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")

    class Meta:
        verbose_name = "商智核心内容数据"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"核心内容数据 ({self.upload_date.strftime('%Y-%m-%d')})"

# 商智内容数据 - 达人分析
class JDInfluencerAnalysis(models.Model):
    date = models.CharField(max_length=100, verbose_name="日期")
    influencer = models.CharField(max_length=100, verbose_name="达人")
    influencer_name = models.CharField(max_length=100, verbose_name="达人名称")
    influencer_id = models.CharField(max_length=100, verbose_name="达人ID")
    guide_detail_visitors = models.IntegerField(default=0, verbose_name="引导进商详访客数")
    guide_cart_users = models.IntegerField(default=0, verbose_name="引导加购人数")
    daily_guide_order_amount = models.FloatField(default=0, verbose_name="当日引导成交金额")
    daily_guide_order_count = models.IntegerField(default=0, verbose_name="当日引导成交单量")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="上传用户")
    
    class Meta:
        verbose_name = "京东达人分析数据"
        verbose_name_plural = verbose_name

# 商智内容数据 - 来源分析
class JDSourceAnalysis(models.Model):
    date = models.CharField(max_length=50, verbose_name="日期", blank=True, null=True)
    source = models.CharField(max_length=100, verbose_name="来源", blank=True, null=True)
    detail_visitors = models.CharField(max_length=50, verbose_name="引导进商详访客数", blank=True, null=True)
    guide_cart_users = models.CharField(max_length=50, verbose_name="引导加购人数", blank=True, null=True)
    daily_guide_order_amount = models.CharField(max_length=50, verbose_name="当日引导成交金额", blank=True, null=True)
    daily_guide_order_count = models.CharField(max_length=50, verbose_name="当日引导成交单量", blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")
    
    class Meta:
        db_table = "jd_source_analysis"
        verbose_name = "来源分析"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']

# 商智内容数据 - 内容分析
class JDContentAnalysis(models.Model):
    date = models.CharField(max_length=50, verbose_name="日期", blank=True, null=True)
    content = models.TextField(verbose_name="内容", blank=True, null=True)
    content_type = models.CharField(max_length=50, verbose_name="内容类型", blank=True, null=True)
    first_publish_time = models.CharField(max_length=50, verbose_name="首次发布时间", blank=True, null=True)
    content_name = models.CharField(max_length=255, verbose_name="内容名称", blank=True, null=True)
    influencer_name = models.CharField(max_length=100, verbose_name="达人名称", blank=True, null=True)
    detail_visitors = models.CharField(max_length=50, verbose_name="引导进商详访客数", blank=True, null=True)
    cart_users = models.CharField(max_length=50, verbose_name="引导加购人数", blank=True, null=True)
    conversion_amount = models.CharField(max_length=50, verbose_name="当日引导成交金额", blank=True, null=True)
    conversion_orders = models.CharField(max_length=50, verbose_name="当日引导成交单量", blank=True, null=True)
    upload_date = models.DateField(auto_now_add=True, verbose_name="上传日期")
    
    class Meta:
        db_table = "jd_content_analysis"
        verbose_name = "内容分析"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']

# 商智内容数据 - 商品分析
class JDProductAnalysis(models.Model):
    # 字段太多，简化处理
    time = models.CharField(max_length=50, verbose_name="时间", blank=True, null=True)
    dimension = models.CharField(max_length=100, verbose_name="所选维度", blank=True, null=True)
    data_content = models.TextField(verbose_name="商品分析数据", blank=True, null=True)
    upload_date = models.DateField(auto_now_add=True, verbose_name="上传日期")
    
    class Meta:
        db_table = "jd_product_analysis"
        verbose_name = "商品分析"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']

# 商智产品数据 - 商品概况
class JDProductOverview(models.Model):
    # 未提供具体字段，创建通用字段
    data_content = models.TextField(verbose_name="商品概况数据", blank=True, null=True)
    upload_date = models.DateField(auto_now_add=True, verbose_name="上传日期")
    
    class Meta:
        db_table = "jd_product_overview"
        verbose_name = "商品概况"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']

# 商智产品数据 - 库存
class JDInventoryData(models.Model):
    warehouse_type = models.CharField(max_length=50, verbose_name="仓网类型", blank=True, null=True)
    region = models.CharField(max_length=50, verbose_name="区域", blank=True, null=True)
    turnover_rate = models.CharField(max_length=50, verbose_name="数量周转", blank=True, null=True)
    # 添加缺失的属性
    in_stock_cost = models.CharField(max_length=100, blank=True, null=True, verbose_name="现货库存成本")
    in_stock_inventory = models.CharField(max_length=100, blank=True, null=True, verbose_name="现货库存")
    available_inventory = models.CharField(max_length=100, blank=True, null=True, verbose_name="可用库存")
    orderable_inventory = models.CharField(max_length=100, blank=True, null=True, verbose_name="可订购库存")
    # 其他属性保持不变
    data_content = models.TextField(verbose_name="库存概况内容", blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")
    
    class Meta:
        db_table = "jd_inventory_data"
        verbose_name = "库存"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']

# 八爪鱼 - 京麦采集
class JDShopRanking(models.Model):
    """京东店铺排名数据"""
    shop_name = models.CharField('店铺名称', max_length=255)
    ranking = models.IntegerField('排名')
    ranking_type = models.CharField('排名类型', max_length=50)  # 如：店铺新客量、老客复购率等
    jingmai_data = models.ForeignKey('JDOctopusJingmaiData', on_delete=models.CASCADE, related_name='shop_rankings', verbose_name='关联京麦数据')
    upload_date = models.DateTimeField('上传日期', auto_now_add=True)

    class Meta:
        verbose_name = '京东店铺排名'
        verbose_name_plural = verbose_name
        ordering = ['ranking_type', 'ranking']

    def __str__(self):
        return f"{self.ranking_type}-{self.shop_name}(第{self.ranking}名)"

class JDOctopusJingmaiData(JDData):
    """八爪鱼京麦采集数据"""
    indicator = models.CharField('指标', max_length=255)
    description = models.TextField('描述')
    score_change = models.CharField('评分及升降分', max_length=100)
    title = models.CharField('标题', max_length=255)
    score_rate = models.CharField('分数和升降率', max_length=100, null=True, blank=True)
    customer_metric = models.CharField('客户转化指标', max_length=100, null=True, blank=True)
    customer_count = models.IntegerField('客户数量', null=True, blank=True)
    shop_entries = models.IntegerField('进店数', null=True, blank=True)
    detail_views = models.IntegerField('浏览商详', null=True, blank=True)
    cart_adds = models.IntegerField('加购', null=True, blank=True)
    transaction_count = models.IntegerField('成交数', null=True, blank=True)
    entry_rate = models.FloatField('进店率', null=True, blank=True)
    view_rate = models.FloatField('浏览率', null=True, blank=True)
    cart_rate = models.FloatField('加购率', null=True, blank=True)
    cart_to_transaction_rate = models.FloatField('加购成交率', null=True, blank=True)
    new_customer_beat_rate = models.FloatField('新客数打败相似店铺百分率', null=True, blank=True)
    transaction_rate_beat = models.CharField('成交转化率打败相似店铺', max_length=100, null=True, blank=True)
    view_rate_beat = models.CharField('浏览率打败相似店铺', max_length=100, null=True, blank=True)
    entry_rate_beat = models.CharField('进店率打败相似店铺', max_length=100, null=True, blank=True)
    cart_transaction_rate_beat = models.CharField('加购成交率打败相似店铺', max_length=100, null=True, blank=True)
    top_shop_type = models.CharField('top店铺类型', max_length=100, null=True, blank=True)
    
    class Meta:
        verbose_name = '八爪鱼京麦采集数据'
        verbose_name_plural = verbose_name

# 八爪鱼 - 京东商品搜索
class JDOctopusProductSearch(models.Model):
    search_keyword = models.CharField(max_length=100, verbose_name="搜索关键词", blank=True, null=True)
    product_name = models.TextField(verbose_name="商品名称", blank=True, null=True)
    price = models.CharField(max_length=50, verbose_name="价格", blank=True, null=True)
    shop_name = models.CharField(max_length=100, verbose_name="商家店名", blank=True, null=True)
    # 其他字段
    product_sku = models.CharField(max_length=50, verbose_name="商品SKU", blank=True, null=True)
    product_link = models.TextField(verbose_name="商品链接", blank=True, null=True)
    review_count = models.CharField(max_length=50, verbose_name="评价人数", blank=True, null=True)
    review_link = models.TextField(verbose_name="评论链接", blank=True, null=True)
    shop_link = models.TextField(verbose_name="店铺链接", blank=True, null=True)
    tags = models.CharField(max_length=255, verbose_name="标签", blank=True, null=True)
    cover_image_link = models.TextField(verbose_name="封面图片链接", blank=True, null=True)
    is_ad = models.CharField(max_length=10, verbose_name="是否广告", blank=True, null=True)
    page_number = models.CharField(max_length=10, verbose_name="页码", blank=True, null=True)
    current_time = models.CharField(max_length=50, verbose_name="当前时间", blank=True, null=True)
    page_url = models.TextField(verbose_name="页面网址", blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="上传日期")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="上传者")
    
    class Meta:
        db_table = "jd_octopus_product_search"
        verbose_name = "京东商品搜索"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']

# EasySpider - Easy京麦采集
class JDEasySpiderData(models.Model):
    activity_name = models.CharField(max_length=100, verbose_name="活动名称", blank=True, null=True)
    activity_type = models.CharField(max_length=50, verbose_name="活动类型", blank=True, null=True)
    activity_type2 = models.CharField(max_length=50, verbose_name="活动类型2", blank=True, null=True)
    activity_description = models.TextField(verbose_name="活动说明", blank=True, null=True)
    remaining_time = models.CharField(max_length=50, verbose_name="报名还剩", blank=True, null=True)
    upload_date = models.DateField(auto_now_add=True, verbose_name="上传日期")
    
    class Meta:
        db_table = "jd_easy_spider_data"
        verbose_name = "Easy京麦采集"
        verbose_name_plural = verbose_name
        ordering = ['-upload_date']

# 京麦数据看板 - 使用代理模型，不创建新表
class JDDataDashboard(JDData):
    class Meta:
        proxy = True
        verbose_name = "京麦数据看板"
        verbose_name_plural = "京麦数据看板"

class JDTempUpload(models.Model):
    """京东数据临时上传存储"""
    file = models.FileField(upload_to='jd_temp/')
    category = models.CharField(max_length=50)
    subcategory = models.CharField(max_length=50)
    upload_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "临时上传文件"
        verbose_name_plural = verbose_name
        ordering = ['-upload_time']


