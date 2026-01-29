from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
import requests
import json

class QuanLyDuAn(models.Model):
    _name = 'quan.ly.du.an'
    _description = 'Quản lý Dự án'
    _rec_name = 'ten_du_an'
    _order = 'do_uu_tien desc, ngay_bat_dau desc'

    ma_du_an = fields.Char(string='Mã dự án', required=True, copy=False, readonly=True, default='Mới')
    ten_du_an = fields.Char(string='Tên Dự án', required=True)
    mo_ta = fields.Html(string='Mô tả chi tiết')
 
    loai_du_an = fields.Selection([
        ('noi_bo', 'Dự án Nội bộ'),
        ('khach_hang', 'Dự án Khách hàng'),
        ('nghien_cuu', 'R&D'),
        ('thau', 'Hồ sơ thầu')
    ], string='Loại dự án', default='noi_bo', required=True)

    do_uu_tien = fields.Selection([('0', 'Thấp'), ('1', 'Trung bình'), ('2', 'Cao'), ('3', 'Khẩn cấp')], string='Độ ưu tiên', default='1')
    khach_hang = fields.Char(string='Khách hàng / Đối tác')
    
    trang_thai = fields.Selection([
        ('moi', 'Mới thiết lập'),
        ('lap_ke_hoach', 'Đang lập kế hoạch'),
        ('dang_chay', 'Đang thực hiện'),
        ('tam_dung', 'Tạm dừng'),
        ('hoan_thanh', 'Hoàn thành'),
        ('huy', 'Đã hủy')
    ], string='Trạng thái', default='moi')

    tien_do = fields.Integer(string='Tiến độ (%)', compute='_compute_tien_do', store=True)

    quan_ly_id = fields.Many2one('quan.ly.nhan.su', string='Quản trị dự án (PM)', required=True, domain="[('chuc_vu_id.ma_chuc_vu', 'in', ['GD', 'TP'])]")
    
    phong_ban_id = fields.Many2one(related='quan_ly_id.phong_ban_id', string='Phòng ban chủ trì', readonly=True, store=True)

    thanh_vien_ids = fields.One2many('quan.ly.thanh.vien', 'du_an_id', string='Thành viên tham gia')
    nhan_su_da_chon_ids = fields.Many2many('quan.ly.nhan.su', compute='_compute_nhan_su_da_chon', string='Danh sách ID đã chọn')

    cong_viec_ids = fields.One2many('quan.ly.cong.viec', 'du_an_id', string='Danh sách công việc')
    van_de_ids = fields.One2many('quan.ly.van.de', 'du_an_id', string='Vấn đề & Rủi ro')
    tai_chinh_ids = fields.One2many('quan.ly.tai.chinh', 'du_an_id', string='Tài chính')

    ngay_bat_dau = fields.Date(string='Ngày bắt đầu', default=fields.Date.today)
    ngay_ket_thuc = fields.Date(string='Ngày kết thúc (Dự kiến)', compute='_compute_ngay_ket_thuc', store=True, readonly=False)
    
    ngan_sach_du_kien = fields.Float(string='Ngân sách dự kiến (VNĐ)')
    
    tong_chi = fields.Float(string='Tổng Chi thực tế', compute='_compute_tai_chinh', store=True)
    tong_thu = fields.Float(string='Tổng Thu thực tế', compute='_compute_tai_chinh', store=True)
    loi_nhuan = fields.Float(string='Lợi nhuận', compute='_compute_tai_chinh', store=True)

    chenh_lech = fields.Float(string='Chênh lệch (Ngân sách - Thực tế)', compute='_compute_tai_chinh', store=True)
    
    canh_bao_ngan_sach = fields.Boolean(string='Vượt ngân sách?', compute='_compute_tai_chinh')
    
    so_luong_cong_viec = fields.Integer(string='Số công việc', compute='_compute_so_luong_cong_viec')

    def action_ai_lap_ke_hoach(self):
        self.ensure_one()
        
        API_KEY = "YOUR_GEMINI_API_KEY_HERE"
        MODEL_NAME = "gemini-2.5-flash"
        
        if not API_KEY or API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            raise UserError("Vui lòng nhập API Key trong code!")

        all_employees = self.env['quan.ly.nhan.su'].search([])
        if not all_employees:
            raise UserError("Hệ thống chưa có nhân sự nào!")

        staff_data = []
        exclude_roles = ['trưởng phòng', 'giám đốc', 'phó phòng', 'chủ tịch', 'quản lý']

        for emp in all_employees:
            job_title = emp.chuc_vu_id.ten_chuc_vu if emp.chuc_vu_id else "Nhân viên"
            job_lower = job_title.lower()
            is_high_level = False
            for role in exclude_roles:
                if role in job_lower:
                    is_high_level = True
                    break
            
            if is_high_level: continue

            dept_name = "Không rõ"
            if emp.phong_ban_id:
                if hasattr(emp.phong_ban_id, 'ten_phong_ban') and emp.phong_ban_id.ten_phong_ban:
                    dept_name = emp.phong_ban_id.ten_phong_ban
                elif hasattr(emp.phong_ban_id, 'name') and emp.phong_ban_id.name:
                    dept_name = emp.phong_ban_id.name
            
            staff_data.append(f"- ID: {emp.id}, Tên: {emp.ho_ten}, Chức vụ: {job_title}, Phòng: {dept_name}")
        
        if not staff_data:
            raise UserError("Không tìm thấy nhân viên phù hợp.")

        staff_text = "\n".join(staff_data)

        prompt = (
            f"--- ROLE & CONTEXT ---\n"
            f"Bạn là một Senior Project Manager (PM) với 10 năm kinh nghiệm quản lý dự án phần mềm theo mô hình Agile/Scrum. "
            f"Nhiệm vụ của bạn là lập kế hoạch triển khai chi tiết cho dự án sau:\n"
            f"- Tên dự án: '{self.ten_du_an}'\n"
            f"- Yêu cầu/Mô tả: {self.mo_ta or 'Triển khai theo tiêu chuẩn ngành'}\n\n"

            f"--- AVAILABLE RESOURCES (Nhân sự khả dụng) ---\n"
            f"Dưới đây là danh sách nhân viên cùng bộ kỹ năng của họ. CHỈ ĐƯỢC CHỌN NGƯỜI TRONG DANH SÁCH NÀY:\n"
            f"{staff_text}\n\n"

            f"--- OBJECTIVES (Nhiệm vụ cụ thể) ---\n"
            f"1. **Phân vai (Role Casting):** Dựa trên tên và kỹ năng (nếu có), hãy gán vai trò phù hợp nhất (Dev, Tester, BA, Designer, DevOps...). "
            f"Một người có thể kiêm nhiệm nếu team thiếu người, nhưng ưu tiên chuyên môn hóa.\n"
            f"2. **Phân rã công việc (WBS - Work Breakdown Structure):** Chia dự án thành 6-12 đầu việc (Tasks) cụ thể, logic, có tính tuần tự (Ví dụ: Phân tích -> Thiết kế -> Code -> Test -> Deploy).\n"
            f"3. **Phân công (Assignment):** Giao việc cho đúng người (Dựa trên ID). Đảm bảo không ai bị quá tải (Overload) hoặc ngồi chơi (Idle).\n"
            f"4. **Dự toán (Estimation):**\n"
            f"   - Ước lượng thời gian (ngày) và giờ công (man-hour) thực tế.\n"
            f"   - Tính chi phí dựa trên mức lương trung bình: 200,000 VNĐ/giờ (1 ngày = 8 giờ).\n\n"

            f"--- STRICT CONSTRAINTS (Ràng buộc bắt buộc) ---\n"
            f"- 'assignee_ids' PHẢI là danh sách chứa các ID số nguyên lấy từ dữ liệu nhân sự đã cung cấp. KHÔNG được bịa ra ID mới.\n"
            f"- Tổng chi phí (total_budget) phải là tổng của tất cả các task cộng lại.\n"
            f"- Output PHẢI là chuỗi JSON thuần túy (Raw JSON), không có Markdown (```json), không có lời dẫn.\n\n"

            f"--- OUTPUT FORMAT (JSON STRUCTURE) ---\n"
            f"{{\n"
            f"  \"total_budget\": (integer: tổng chi phí VNĐ),\n"
            f"  \"project_duration_days\": (integer: tổng thời gian dự kiến),\n"
            f"  \"selected_members\": [\n"
            f"      {{ \"id\": (integer: ID lấy từ input), \"role\": \"(string: Dev/Tester/BA...)\", \"reason\": \"(string: Lý do chọn ngắn gọn)\" }}\n"
            f"  ],\n"
            f"  \"tasks\": [\n"
            f"      {{\n"
            f"          \"name\": \"(string: Tên công việc chuyên nghiệp)\",\n"
            f"          \"desc\": \"(string: Mô tả chi tiết phạm vi công việc)\",\n"
            f"          \"deadline_days\": (integer: số ngày hoàn thành),\n"
            f"          \"man_hours\": (float: tổng giờ làm),\n"
            f"          \"cost\": (integer: man_hours * 200000),\n"
            f"          \"assignee_ids\": [(integer: ID nhân sự)]\n"
            f"      }}\n"
            f"  ]\n"
            f"}}"
        )

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = { "contents": [{"parts": [{"text": prompt}]}] }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(data), timeout=60)
            if response.status_code != 200: raise UserError(f"Lỗi API: {response.text}")
            
            result = response.json()
            if not result.get('candidates'): raise UserError("AI không trả về kết quả.")
            
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            plan_data = json.loads(ai_text)

            self.write({'ngan_sach_du_kien': plan_data.get('total_budget', 0)})

            emp_role_map = {} 
            members_data = plan_data.get('selected_members', [])
            current_ids = self.thanh_vien_ids.mapped('nhan_su_id.id')

            for mem in members_data:
                emp_id = mem.get('id')
                ai_role = mem.get('role', 'dev')
                emp_role_map[emp_id] = ai_role

                if not self.env['quan.ly.nhan.su'].browse(emp_id).exists(): continue

                if emp_id not in current_ids:
                    self.env['quan.ly.thanh.vien'].create({
                        'du_an_id': self.id, 'nhan_su_id': emp_id, 'vai_tro_du_an': ai_role 
                    })
                else:
                    existing = self.thanh_vien_ids.filtered(lambda m: m.nhan_su_id.id == emp_id)
                    existing.write({'vai_tro_du_an': ai_role})

            tasks = plan_data.get('tasks', [])
            today = fields.Date.today()
            
            for task in tasks:
                deadline = today + timedelta(days=task.get('days', 1))
                assignee_ids = task.get('assignee_ids', [])
                valid_assignees = self.env['quan.ly.nhan.su'].browse(assignee_ids).exists().ids
                
                auto_type = 'dev'
                if valid_assignees:
                    first_person_id = valid_assignees[0]
                    person_role = emp_role_map.get(first_person_id, 'dev')
                    
                    if person_role == 'tester':
                        auto_type = 'tester'
                    elif person_role == 'ba':
                        auto_type = 'ba'
                    elif person_role == 'designer':
                        auto_type = 'khac'
                    else:
                        auto_type = 'dev'

                self.env['quan.ly.cong.viec'].create({
                    'du_an_id': self.id,
                    'ten_cong_viec': task.get('name'),
                    'mo_ta': task.get('desc'),
                    'han_hoan_thanh': deadline,
                    'nhan_vien_tham_gia_ids': [(6, 0, valid_assignees)],
                    'trang_thai': 'moi',
                    'tien_do': 0,
                    'chi_phi_du_kien': task.get('cost', 0),
                    'chi_phi': 0,
                    'loai_cong_viec': auto_type
                })

            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Thành công!', 'message': 'Đã lập kế hoạch và phân loại công việc tự động.', 'type': 'success'}
            }

        except Exception as e:
            raise UserError(f"Lỗi: {str(e)}")

    @api.depends('cong_viec_ids', 'cong_viec_ids.tien_do')
    def _compute_tien_do(self):
        for rec in self:
            if rec.cong_viec_ids:
                total = sum(task.tien_do for task in rec.cong_viec_ids)
                rec.tien_do = int(total / len(rec.cong_viec_ids))
            else:
                rec.tien_do = 0
            
            if rec.tien_do == 100 and rec.trang_thai != 'hoan_thanh':
                rec.trang_thai = 'hoan_thanh'
            elif rec.tien_do > 0 and rec.tien_do < 100 and rec.trang_thai == 'moi':
                rec.trang_thai = 'dang_chay'

    @api.depends('tai_chinh_ids', 'cong_viec_ids.chi_phi', 'ngan_sach_du_kien')
    def _compute_tai_chinh(self):
        for rec in self:
            chi_phi_cong_viec = sum(rec.cong_viec_ids.mapped('chi_phi'))
            chi_khac = sum(t.so_tien for t in rec.tai_chinh_ids if t.loai_giao_dich == 'chi')
            thu = sum(t.so_tien for t in rec.tai_chinh_ids if t.loai_giao_dich == 'thu')
            rec.tong_chi = chi_phi_cong_viec + chi_khac
            rec.tong_thu = thu
            rec.loi_nhuan = rec.tong_thu - rec.tong_chi
            rec.chenh_lech = rec.ngan_sach_du_kien - rec.tong_chi
            rec.canh_bao_ngan_sach = rec.tong_chi > rec.ngan_sach_du_kien if rec.ngan_sach_du_kien > 0 else False

    @api.depends('cong_viec_ids.han_hoan_thanh')
    def _compute_ngay_ket_thuc(self):
        for rec in self:
            deadlines = rec.cong_viec_ids.mapped('han_hoan_thanh')
            valid_deadlines = [d for d in deadlines if d]
            if valid_deadlines: rec.ngay_ket_thuc = max(valid_deadlines)

    @api.depends('thanh_vien_ids', 'thanh_vien_ids.nhan_su_id')
    def _compute_nhan_su_da_chon(self):
        for rec in self: rec.nhan_su_da_chon_ids = rec.thanh_vien_ids.mapped('nhan_su_id')

    @api.depends('cong_viec_ids')
    def _compute_so_luong_cong_viec(self):
        for rec in self: rec.so_luong_cong_viec = len(rec.cong_viec_ids)

    @api.constrains('quan_ly_id')
    def _check_quyen_pm(self):
        for rec in self:
            if rec.quan_ly_id and rec.quan_ly_id.chuc_vu_id.ma_chuc_vu not in ['GD', 'TP']:
                raise ValidationError(f"Ông/Bà {rec.quan_ly_id.ho_ten} không đủ thẩm quyền làm PM.")

    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc')
    def _check_dates(self):
        for rec in self:
            if rec.ngay_bat_dau and rec.ngay_ket_thuc and rec.ngay_bat_dau > rec.ngay_ket_thuc:
                raise ValidationError("Lỗi Logic: Ngày bắt đầu không được lớn hơn Ngày kết thúc!")

    def action_hoan_thanh_du_an(self):
        for rec in self:
            cong_viec_chua_xong = rec.cong_viec_ids.filtered(lambda t: t.trang_thai != 'hoan_thanh')
            if cong_viec_chua_xong: raise ValidationError(f"Vẫn còn {len(cong_viec_chua_xong)} công việc chưa xong.")
            rec.trang_thai = 'hoan_thanh'
            rec.tien_do = 100

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': f'Công việc: {self.ten_du_an}', 'type': 'ir.actions.act_window',
            'view_mode': 'tree,form', 'res_model': 'quan.ly.cong.viec',
            'domain': [('du_an_id', '=', self.id)], 'context': {'default_du_an_id': self.id},
        }

    def action_view_tai_chinh(self):
        self.ensure_one()
        return {
            'name': f'Tài chính: {self.ten_du_an}', 'type': 'ir.actions.act_window',
            'view_mode': 'tree,form', 'res_model': 'quan.ly.tai.chinh',
            'domain': [('du_an_id', '=', self.id)], 'context': {'default_du_an_id': self.id},
        }

    @api.model
    def create(self, vals):
        if vals.get('ma_du_an', 'Mới') == 'Mới':
            vals['ma_du_an'] = self.env['ir.sequence'].next_by_code('quan.ly.du.an') or 'DA001'
        return super(QuanLyDuAn, self).create(vals)

class QuanLyCongViec(models.Model):
    _name = 'quan.ly.cong.viec'
    _description = 'Công việc chi tiết'
    _rec_name = 'ten_cong_viec'

    du_an_id = fields.Many2one('quan.ly.du.an', string='Dự án', required=True, ondelete='cascade')
    ten_cong_viec = fields.Char(string='Tên công việc', required=True)
    do_uu_tien = fields.Selection([('0', 'Thấp'), ('1', 'Trung bình'), ('2', 'Cao'), ('3', 'Khẩn cấp')], string='Độ ưu tiên', default='1')
    nhan_vien_tham_gia_ids = fields.Many2many('quan.ly.nhan.su', string='Nhân viên tham gia')
    nguoi_giao_viec_id = fields.Many2one('quan.ly.nhan.su', string='Người phụ trách')
    han_hoan_thanh = fields.Date(string='Hạn chót')
    tien_do = fields.Integer(string='Tiến độ (%)', default=0)
    chi_phi = fields.Float(string='Chi phí phát sinh')
    chi_phi_du_kien = fields.Float(string='Chi phí dự kiến')
    gio_du_kien = fields.Float(string='Giờ dự kiến (Man-hour)', default=1.0)
    gio_thuc_te = fields.Float(string='Giờ thực tế')
    trang_thai_deadline = fields.Selection([('dung_han', 'Đúng hạn'), ('tre_han', 'Trễ hạn'), ('sap_den_han', 'Sắp đến hạn')], string='Tình trạng hạn', compute='_compute_trang_thai_deadline', store=True)

    loai_cong_viec = fields.Selection([
        ('dev', 'Lập trình (Code)'),
        ('tester', 'Kiểm thử (Test Case/Bug)'),
        ('ba', 'Phân tích (Tài liệu/Yêu cầu)'),
        ('khac', 'Khác')
    ], string='Loại công việc', default='dev', required=True)
    
    do_kho = fields.Selection([
        ('de', 'Dễ'), ('tb', 'Trung bình'), ('kho', 'Khó')
    ], string='Độ khó', default='tb')

    trang_thai = fields.Selection([
        ('moi', 'Mới'), ('dang_lam', 'Đang làm'), ('hoan_thanh', 'Hoàn thành')
    ], string='Trạng thái', default='moi')

class ThanhVienDuAn(models.Model):
    _name = 'quan.ly.thanh.vien'
    _description = 'Thành viên tham gia dự án'

    du_an_id = fields.Many2one('quan.ly.du.an', string='Dự án', required=True, ondelete='cascade')
    nhan_su_id = fields.Many2one('quan.ly.nhan.su', string='Nhân sự', required=True)
    
    chuc_vu_id = fields.Many2one(related='nhan_su_id.chuc_vu_id', string='Chức vụ', readonly=True)
    code_chuc_vu = fields.Char(related='nhan_su_id.chuc_vu_id.ma_chuc_vu', string='Mã chức vụ', readonly=True)
    phong_ban_id = fields.Many2one(related='nhan_su_id.phong_ban_id', string='Phòng ban', readonly=True)
    email = fields.Char(related='nhan_su_id.email', string='Email', readonly=True)
    so_dien_thoai = fields.Char(related='nhan_su_id.so_dien_thoai', string='SĐT', readonly=True)
    
    vai_tro_du_an = fields.Selection([
        ('ba', 'BA'), ('dev', 'Developer'), ('tester', 'Tester'), 
        ('designer', 'Designer'), ('support', 'Support')
    ], string='Vai trò dự án', required=True, default='dev')

    _sql_constraints = [('unique_thanh_vien_du_an', 'unique(du_an_id, nhan_su_id)', 'Lỗi: Nhân sự này ĐÃ CÓ trong dự án!')]

class VanDeDuAn(models.Model):
    _name = 'quan.ly.van.de'
    _description = 'Vấn đề phát sinh'

    du_an_id = fields.Many2one('quan.ly.du.an', string='Dự án', required=True, ondelete='cascade')
    ten_van_de = fields.Char(string='Tiêu đề vấn đề', required=True)
    mo_ta = fields.Text(string='Mô tả chi tiết')
    muc_do = fields.Selection([('thap', 'Thấp'), ('cao', 'Cao')], string='Mức độ', default='thap')
    trang_thai = fields.Selection([('moi', 'Mới'), ('xong', 'Xong')], string='Trạng thái', default='moi')

class TaiChinhDuAn(models.Model):
    _name = 'quan.ly.tai.chinh'
    _description = 'Tài chính dự án'

    du_an_id = fields.Many2one('quan.ly.du.an', string='Dự án', required=True, ondelete='cascade')
    loai_giao_dich = fields.Selection([('thu', 'Thu'), ('chi', 'Chi')], string='Loại', default='chi')
    noi_dung = fields.Char(string='Nội dung')
    so_tien = fields.Float(string='Số tiền')
    ngay_giao_dich = fields.Date(string='Ngày giao dịch', default=fields.Date.today)