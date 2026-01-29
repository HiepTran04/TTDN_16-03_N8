from odoo import models, fields, api, modules
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta
import re
import base64

class QuanLyNhanSu(models.Model):
    _name = 'quan.ly.nhan.su'
    _description = 'Quản lý Hồ sơ Nhân sự'
    _rec_name = 'ho_ten'
    _order = 'thu_tu_chuc_vu asc, ho_ten asc, ma_nhan_su asc'

    DANH_SACH_TINH_THANH = [
        ('ha_noi', 'TP Hà Nội'),
        ('tp_hcm', 'TP Hồ Chí Minh'),
        ('hai_phong', 'TP Hải Phòng'),
        ('da_nang', 'TP Đà Nẵng'),
        ('can_tho', 'TP Cần Thơ'),
        ('hue', 'TP Huế'),
        ('nghe_an', 'Nghệ An'),
        ('thanh_hoa', 'Thanh Hóa'),
        ('phu_tho', 'Phú Thọ'),
        ('bac_ninh', 'Bắc Ninh'),
        ('hung_yen', 'Hưng Yên'),
        ('ninh_binh', 'Ninh Bình'),
        ('quang_ninh', 'Quảng Ninh'),
        ('thai_nguyen', 'Thái Nguyên'),
        ('tuyen_quang', 'Tuyên Quang'),
        ('lao_cai', 'Lào Cai'),
        ('son_la', 'Sơn La'),
        ('lang_son', 'Lạng Sơn'),
        ('cao_bang', 'Cao Bằng'),
        ('dien_bien', 'Điện Biên'),
        ('lai_chau', 'Lai Châu'),
        ('ha_tinh', 'Hà Tĩnh'),
        ('quang_tri', 'Quảng Trị'),
        ('quang_ngai', 'Quảng Ngãi'),
        ('gia_lai', 'Gia Lai'),
        ('dak_lak', 'Đắk Lắk'),
        ('lam_dong', 'Lâm Đồng'),
        ('khanh_hoa', 'Khánh Hòa'),
        ('tay_ninh', 'Tây Ninh'),
        ('dong_nai', 'Đồng Nai'),
        ('vinh_long', 'Vĩnh Long'),
        ('dong_thap', 'Đồng Tháp'),
        ('an_giang', 'An Giang'),
        ('ca_mau', 'Cà Mau'),
    ]

    DANH_SACH_NGAN_HANG = [
        ('vcb', 'Vietcombank (Ngoại thương)'),
        ('vietin', 'VietinBank (Công thương)'),
        ('bidv', 'BIDV (Đầu tư & PT)'),
        ('agri', 'Agribank (Nông nghiệp)'),
        ('tcb', 'Techcombank (Kỹ thương)'),
        ('mb', 'MBBank (Quân đội)'),
        ('vpb', 'VPBank (Việt Nam Thịnh Vượng)'),
        ('acb', 'ACB (Á Châu)'),
        ('sacom', 'Sacombank (Sài Gòn Thương Tín)'),
        ('tp', 'TPBank (Tiên Phong)'),
        ('vib', 'VIB (Quốc tế)'),
        ('hdb', 'HDBank (PT TP.HCM)'),
        ('shb', 'SHB (Sài Gòn - Hà Nội)'),
        ('msb', 'MSB (Hàng Hải)'),
        ('ocb', 'OCB (Phương Đông)'),
        ('seab', 'SeABank (Đông Nam Á)'),
        ('exim', 'Eximbank (Xuất Nhập Khẩu)'),
        ('scb', 'SCB (Sài Gòn)'),
        ('nam_a', 'Nam A Bank'),
        ('bac_a', 'Bac A Bank'),
        ('viet_a', 'Viet A Bank'),
        ('pvcom', 'PVcomBank (Đại chúng)'),
        ('shinhan', 'Shinhan Bank'),
        ('khac', 'Ngân hàng khác...')
    ]
 
    ma_nhan_su = fields.Char(string='Mã nhân sự', readonly=True, copy=False, default='Mới')
    ho_ten = fields.Char(string='Họ và tên', required=True)
 
    image_1920 = fields.Image("Ảnh đại diện", compute='_compute_avatar_mac_dinh', store=True, readonly=False)
    image_128 = fields.Image("Ảnh nhỏ", related="image_1920", store=True)

    user_id = fields.Many2one('res.users', string='Tài khoản hệ thống', help="Liên kết user đăng nhập để phân quyền")

    phong_ban_id = fields.Many2one('quan.ly.phong.ban', string='Phòng ban')
    chuc_vu_id = fields.Many2one('quan.ly.chuc.vu', string='Chức vụ')
    thu_tu_chuc_vu = fields.Integer(related='chuc_vu_id.thu_tu_uu_tien', store=True, string='Thứ tự chức vụ')

    code_phong_ban = fields.Char(related='phong_ban_id.ma_phong_ban', store=True)
    code_chuc_vu = fields.Char(related='chuc_vu_id.ma_chuc_vu', store=True)

    trang_thai = fields.Selection([
        ('dang_lam', 'Đang làm việc'),
        ('nghi_viec', 'Đã nghỉ việc')
    ], string='Trạng thái', default='dang_lam')

    email = fields.Char(string='Email công việc')
    so_dien_thoai = fields.Char(string='Số điện thoại')
    email_ca_nhan = fields.Char(string='Email cá nhân')
    
    dia_chi_thuong_tru = fields.Text(string='Địa chỉ thường trú')
    dia_chi_hien_tai = fields.Text(string='Chỗ ở hiện tại')
    que_quan = fields.Selection(selection=DANH_SACH_TINH_THANH, string='Quê quán')

    ngay_sinh = fields.Date(string='Ngày sinh', required=True)
    tuoi = fields.Integer(string='Tuổi', compute='_tinh_tuoi', store=True)
    gioi_tinh = fields.Selection([('nam', 'Nam'), ('nu', 'Nữ'), ('khac', 'Khác')], string='Giới tính')
    hon_nhan = fields.Selection([('doc_than', 'Độc thân'), ('ket_hon', 'Đã kết hôn')], string='Hôn nhân')
    
    cccd = fields.Char(string='Số CCCD/CMND')
    ngay_cap = fields.Date(string='Ngày cấp')
    noi_cap = fields.Char(string='Nơi cấp')

    ngay_vao_lam = fields.Date(string='Ngày bắt đầu làm', default=fields.Date.today)
    
    ngay_nghi_viec = fields.Date(string='Ngày nghỉ việc')
    
    tham_nien = fields.Char(string='Thâm niên', compute='_compute_tham_nien', store=False)

    loai_hop_dong = fields.Selection([
        ('thu_viec', 'Thử việc'), 
        ('chinh_thuc', 'Chính thức'), 
        ('vo_thoi_han', 'Vô thời hạn')
    ], string='Loại hợp đồng', default='thu_viec')
    
    ngay_ket_thuc_thu_viec = fields.Date(string='Hết hạn thử việc', compute='_compute_het_han_thu_viec', store=True)
    
    muc_luong_co_ban = fields.Float(string='Lương cơ bản (VNĐ)')
    phu_cap = fields.Float(string='Phụ cấp')

    so_tai_khoan = fields.Char(string='Số tài khoản')
    ten_ngan_hang = fields.Selection(selection=DANH_SACH_NGAN_HANG, string='Tên ngân hàng')
    chi_nhanh = fields.Char(string='Chi nhánh')
    
    trinh_do = fields.Selection([
        ('trung_cap', 'Trung cấp'), ('cao_dang', 'Cao đẳng'),
        ('dai_hoc', 'Đại học'), ('thac_si', 'Thạc sĩ')
    ], string='Trình độ học vấn')
    truong_dao_tao = fields.Char(string='Trường đào tạo')
    chuyen_nganh = fields.Char(string='Chuyên ngành')

    @api.onchange('ho_ten', 'email', 'email_ca_nhan')
    def _chuan_hoa_du_lieu(self):
        for rec in self:
            if rec.ho_ten:
                rec.ho_ten = rec.ho_ten.title().strip()
            if rec.email:
                rec.email = rec.email.lower().strip()
            if rec.email_ca_nhan:
                rec.email_ca_nhan = rec.email_ca_nhan.lower().strip()

    @api.depends('ngay_vao_lam', 'ngay_nghi_viec', 'trang_thai')
    def _compute_tham_nien(self):
        today = date.today()
        for rec in self:
            if not rec.ngay_vao_lam:
                rec.tham_nien = "Chưa xác định"
                continue

            end_date = rec.ngay_nghi_viec if rec.trang_thai == 'nghi_viec' and rec.ngay_nghi_viec else today
            
            diff = relativedelta(end_date, rec.ngay_vao_lam)
            rec.tham_nien = f"{diff.years} năm {diff.months} tháng"

    @api.depends('ngay_vao_lam', 'loai_hop_dong')
    def _compute_het_han_thu_viec(self):
        for rec in self:
            if rec.loai_hop_dong == 'thu_viec' and rec.ngay_vao_lam:
                rec.ngay_ket_thuc_thu_viec = rec.ngay_vao_lam + relativedelta(months=2)
            else:
                rec.ngay_ket_thuc_thu_viec = False

    @api.depends('ngay_sinh')
    def _tinh_tuoi(self):
        today = date.today()
        for rec in self:
            if rec.ngay_sinh:
                rec.tuoi = today.year - rec.ngay_sinh.year - (
                    (today.month, today.day) < (rec.ngay_sinh.month, rec.ngay_sinh.day)
                )
            else:
                rec.tuoi = 0

    @api.constrains('email', 'email_ca_nhan', 'tuoi', 'cccd', 'so_dien_thoai', 'so_tai_khoan', 'muc_luong_co_ban')
    def _kiem_tra_hop_le(self):
        mau_email = r"[^@]+@[^@]+\.[^@]+"
        for rec in self:
            if rec.email and not re.match(mau_email, rec.email):
                raise ValidationError("Email công việc không hợp lệ!")
            if rec.email_ca_nhan and not re.match(mau_email, rec.email_ca_nhan):
                raise ValidationError("Email cá nhân không hợp lệ!")

            if rec.ngay_sinh and rec.tuoi < 18:
                raise ValidationError(f"Nhân viên mới {rec.tuoi} tuổi. Quy định phải đủ 18 tuổi trở lên!")

            if rec.cccd:
                if not rec.cccd.isdigit():
                    raise ValidationError("Số CCCD/CMND chỉ được phép chứa số!")
                if len(rec.cccd) not in [9, 12]:
                    raise ValidationError("Số CCCD phải là 12 số hoặc CMND 9 số!")

            if rec.so_dien_thoai:
                sdt_clean = rec.so_dien_thoai.replace(" ", "").replace(".", "").replace("+", "")
                if not sdt_clean.isdigit():
                    raise ValidationError("Số điện thoại không hợp lệ!")
            
            if rec.muc_luong_co_ban < 0 or rec.phu_cap < 0:
                raise ValidationError("Lương và phụ cấp không được là số âm!")

    @api.onchange('ho_ten', 'ngay_sinh')
    def _tu_dong_tao_ma_nv(self):
        for rec in self:
            if not rec.ma_nhan_su or rec.ma_nhan_su == 'Mới':
                if rec.ho_ten and rec.ngay_sinh:
                    cac_tu = rec.ho_ten.strip().split()
                    viet_tat = "".join([tu[0].upper() for tu in cac_tu])
                    ngay_sinh_str = rec.ngay_sinh.strftime('%d%m%Y')
                    rec.ma_nhan_su = f"{viet_tat}{ngay_sinh_str}"

    @api.depends('gioi_tinh')
    def _compute_avatar_mac_dinh(self):
        for rec in self:
            if isinstance(rec.id, models.NewId) or not rec.image_1920:
                img_path = False
                if rec.gioi_tinh == 'nam':
                    img_path = modules.get_module_resource('quan_ly_nhan_su', 'static/src/img', 'avatar_nam.png')
                elif rec.gioi_tinh == 'nu':
                    img_path = modules.get_module_resource('quan_ly_nhan_su', 'static/src/img', 'avatar_nu.png')
                elif rec.gioi_tinh == 'khac':
                    img_path = modules.get_module_resource('quan_ly_nhan_su', 'static/src/img', 'avatar_khac.png')

                if img_path:
                    try:
                        with open(img_path, 'rb') as f:
                            rec.image_1920 = base64.b64encode(f.read())
                    except FileNotFoundError:
                        pass
                else:
                    if isinstance(rec.id, models.NewId):
                        rec.image_1920 = False

    @api.model
    def create(self, vals):
        if vals.get('ma_nhan_su', 'Mới') == 'Mới':
            ho_ten = vals.get('ho_ten')
            ngay_sinh = vals.get('ngay_sinh')
            if ho_ten and ngay_sinh:
                cac_tu = ho_ten.strip().split()
                viet_tat = "".join([tu[0].upper() for tu in cac_tu])
                # Xử lý định dạng ngày sinh an toàn hơn
                ngay_sinh_str = "00000000"
                if isinstance(ngay_sinh, str): 
                    parts = ngay_sinh.split('-')
                    if len(parts) == 3: ngay_sinh_str = f"{parts[2]}{parts[1]}{parts[0]}"
                elif hasattr(ngay_sinh, 'strftime'):
                    ngay_sinh_str = ngay_sinh.strftime('%d%m%Y')
                vals['ma_nhan_su'] = f"{viet_tat}{ngay_sinh_str}"

        if vals.get('ho_ten'):
            vals['ho_ten'] = vals['ho_ten'].title().strip()

        record = super(QuanLyNhanSu, self).create(vals)
        record._cap_nhat_truong_phong_cho_phong_ban()
        return record

    def write(self, vals):
        if vals.get('trang_thai') == 'nghi_viec':
            if not vals.get('ngay_nghi_viec'):
                vals['ngay_nghi_viec'] = fields.Date.today()
            
            for rec in self:
                if rec.user_id:
                    rec.user_id.active = False
                
                if rec.phong_ban_id and rec.phong_ban_id.truong_phong_id.id == rec.id:
                    rec.phong_ban_id.write({'truong_phong_id': False})

        if vals.get('ho_ten'):
            vals['ho_ten'] = vals['ho_ten'].title().strip()

        res = super(QuanLyNhanSu, self).write(vals)
        if 'chuc_vu_id' in vals or 'phong_ban_id' in vals:
            for rec in self:
                rec._cap_nhat_truong_phong_cho_phong_ban()
        return res

    def _cap_nhat_truong_phong_cho_phong_ban(self):
        for rec in self:
            if rec.phong_ban_id and rec.chuc_vu_id:
                if rec.chuc_vu_id.ma_chuc_vu == 'TP' and rec.trang_thai == 'dang_lam': 
                    rec.phong_ban_id.sudo().write({
                        'truong_phong_id': rec.id
                    })

    @api.constrains('chuc_vu_id', 'phong_ban_id', 'trang_thai')
    def _kiem_tra_duy_nhat_truong_phong(self):
        for rec in self:
            if rec.trang_thai == 'dang_lam' and rec.phong_ban_id and rec.chuc_vu_id.ma_chuc_vu == 'TP':
                truong_phong_cu = self.search([
                    ('phong_ban_id', '=', rec.phong_ban_id.id),
                    ('chuc_vu_id.ma_chuc_vu', '=', 'TP'),
                    ('trang_thai', '=', 'dang_lam'),
                    ('id', '!=', rec.id)
                ], limit=1)

                if truong_phong_cu:
                    raise ValidationError(
                        f"Lỗi: Phòng '{rec.phong_ban_id.ten_phong_ban}' đã có Trưởng phòng là {truong_phong_cu.ho_ten}."
                    )

    @api.constrains('chuc_vu_id', 'trang_thai')
    def _kiem_tra_duy_nhat_giam_doc(self):
        for rec in self:
            if rec.trang_thai == 'dang_lam' and rec.chuc_vu_id.ma_chuc_vu == 'GD':
                giam_doc_hien_tai = self.search([
                    ('chuc_vu_id.ma_chuc_vu', '=', 'GD'),
                    ('trang_thai', '=', 'dang_lam'),
                    ('id', '!=', rec.id)
                ], limit=1)
                if giam_doc_hien_tai:
                    raise ValidationError(
                        f"Lỗi: Doanh nghiệp chỉ được phép có 1 Giám đốc! Hiện tại là {giam_doc_hien_tai.ho_ten}."
                    )