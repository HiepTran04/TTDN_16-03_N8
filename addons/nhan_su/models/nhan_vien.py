from odoo import models, fields, api
import unicodedata


class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'

    ho_ten = fields.Char("Họ tên", required=True)
    ngay_sinh = fields.Date("Ngày sinh", required=True)

    ma_dinh_danh = fields.Char(
        string="Mã định danh",
        compute="_compute_ma_dinh_danh",
        store=True,
        readonly=True
    )
    tuoi = fields.Char("Tuổi")
    que_quan = fields.Char("Quê quán")
    email = fields.Char("Email")
    so_dien_thoai = fields.Char("Số điện thoại")
    so_bhxh = fields.Char("Số bảo hiểm xã hội")
    dia_chi = fields.Char("Địa chỉ thường trú")
    luong = fields.Char("Lương")

    @api.depends('ho_ten', 'ngay_sinh')
    def _compute_ma_dinh_danh(self):
        for rec in self:
            rec.ma_dinh_danh = rec._gen_ma_dinh_danh()

    @api.onchange('ho_ten', 'ngay_sinh')
    def _onchange_ma_dinh_danh(self):
        self.ma_dinh_danh = self._gen_ma_dinh_danh()

    def _gen_ma_dinh_danh(self):
        self.ensure_one()

        if not self.ho_ten or not self.ngay_sinh:
            return False

        words = self.ho_ten.strip().split()

        initials = ''.join(
            self._remove_accents(word[0]).upper()
            for word in words if word
        )

        dob = fields.Date.to_date(self.ngay_sinh)
        if not dob:
            return False

        dob_str = dob.strftime('%d%m%Y')

        return f"{initials}{dob_str}"
