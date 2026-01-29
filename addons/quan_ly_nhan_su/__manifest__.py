{
    'name': 'Quản lý Nhân sự',
    'version': '1.0',
    'summary': 'Quản lý Hồ sơ, Phòng ban, Chức vụ',
    'author': 'HiepTD',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/nhan_su_views.xml',
        'views/phong_ban_views.xml',
        'views/chuc_vu_views.xml',
        'data/master_data.xml',
    ],
    'installable': True,
    'application': True,
}