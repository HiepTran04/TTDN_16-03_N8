from odoo import models, fields, api

class QuanLyPhongBan(models.Model):
    _name = 'quan.ly.phong.ban'
    _description = 'Quản lý Phòng ban'
    _rec_name = 'ten_phong_ban'
    _order = 'ten_phong_ban asc'

    ma_phong_ban = fields.Char(string='Mã phòng', required=True)
    ten_phong_ban = fields.Char(string='Tên phòng ban', required=True)
    mo_ta = fields.Text(string='Mô tả chức năng, nhiệm vụ')

    nhan_su_ids = fields.One2many('quan.ly.nhan.su', 'phong_ban_id', string='Danh sách nhân viên')

    truong_phong_id = fields.Many2one('quan.ly.nhan.su', string='Trưởng phòng')

    so_luong_nhan_su = fields.Integer(string='Tổng nhân sự', compute='_compute_so_luong', store=True)

    @api.depends('nhan_su_ids')
    def _compute_so_luong(self):
        for rec in self:
            rec.so_luong_nhan_su = len(rec.nhan_su_ids)

    _sql_constraints = [
        ('ma_phong_unique', 'unique(ma_phong_ban)', 'Mã phòng ban không được trùng lặp!')
    ]

    def action_view_nhan_su(self):
        """
        Hàm được gọi khi bấm vào Smart Button 'Nhân sự' trên form Phòng ban.
        Nó sẽ trả về view danh sách nhân viên thuộc phòng ban này.
        """
        self.ensure_one()
        return {
            'name': 'Nhân sự thuộc phòng %s' % self.ten_phong_ban,
            'type': 'ir.actions.act_window',
            'res_model': 'quan.ly.nhan.su',
            'view_mode': 'tree,form',
            'domain': [('phong_ban_id', '=', self.id)],
            'context': {'default_phong_ban_id': self.id},
        }