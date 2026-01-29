{
    'name': 'Quản lý Dự án',
    'version': '1.0',
    'summary': 'Hệ thống quản lý dự án, tiến độ và nguồn lực',
    'author': 'HiepTD',
    'category': 'Quan Ly',
    'depends': ['base', 'quan_ly_nhan_su'],
    'data': [
        'security/ir.model.access.csv',
        'views/du_an_views.xml',
        'views/report_views.xml',
    ],
    'application': True,
    'installable': True,
}