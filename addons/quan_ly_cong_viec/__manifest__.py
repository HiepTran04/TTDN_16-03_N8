{
    'name': "Quản lý Công việc",
    'version': '1.0',
    'summary': "Theo dõi tiến độ, phân công công việc chi tiết",
    'author': "HiepTD",
    'category': 'Quan Ly',
    'version': '1.0',
    'depends': ['base', 'quan_ly_du_an', 'quan_ly_nhan_su'],
    'data': [
        'security/ir.model.access.csv',
        'views/cong_viec_views.xml',
    ],
    'application': True,
    'installable': True,
}