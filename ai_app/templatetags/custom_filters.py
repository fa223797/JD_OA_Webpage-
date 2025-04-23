from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """获取字典中的值"""
    return dictionary.get(key, {})

@register.filter
def get_field_value(obj, field):
    """获取对象的字段值"""
    try:
        return getattr(obj, field)
    except (AttributeError, TypeError):
        return ''

@register.filter
def get_verbose_name(model, field_name):
    """获取字段的中文名称"""
    try:
        return model._meta.get_field(field_name).verbose_name
    except:
        return field_name

@register.filter
def get_field_chinese_name(field_name):
    """字段名映射为中文名"""
    field_mapping = {
        'category': '数据类别',
        'subcategory': '子类别',
        'upload_date': '上传日期',
        'search_keyword': '搜索词',
        'traffic_contribution': '流量贡献占比',
        'keyword_rank': '词下排名',
        'main_exposure_product': '主曝光图商品',
        'search_performance': '搜索表现总分',
        'traffic_acquisition': '流量获取力',
        'traffic_conversion': '流量承接力',
        'product_info': '商品信息',
        'click_time': '点击时间',
        'impression_index': '展现指数',
        'click_index': '点击指数',
        'click_rate': '点击率',
        'region_name': '地域名称',
        'conversion_rate': '转化率'
    }
    return field_mapping.get(field_name, field_name) 