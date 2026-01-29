from odoo import models, fields, api

class QuanLyChucVu(models.Model):
    _name = 'quan.ly.chuc.vu'
    _description = 'Quản lý Chức vụ'
    _rec_name = 'ten_chuc_vu'
    _order = 'thu_tu_uu_tien asc'

    ma_chuc_vu = fields.Char(string='Mã chức vụ', required=True)
    ten_chuc_vu = fields.Char(string='Tên chức vụ', required=True)
    mo_ta = fields.Text(string='Mô tả công việc')

    thu_tu_uu_tien = fields.Integer(string='Thứ tự hiển thị', default=10)

    nhan_su_ids = fields.One2many('quan.ly.nhan.su', 'chuc_vu_id', string='Nhân sự đảm nhiệm')
    
    # Đếm số lượng
    so_luong_nhan_su = fields.Integer(string='Số lượng nhân sự', compute='_compute_so_luong', store=True)

    @api.depends('nhan_su_ids')
    def _compute_so_luong(self):
        for rec in self:
            rec.so_luong_nhan_su = len(rec.nhan_su_ids)

    _sql_constraints = [
        ('ma_chuc_vu_unique', 'unique(ma_chuc_vu)', 'Mã chức vụ không được trùng lặp!')
    ]