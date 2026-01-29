from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date
import requests
import json
import base64

class QuanLyCongViec(models.Model):
    _name = 'quan.ly.cong.viec'
    _description = 'Quản lý Công việc chi tiết'
    _rec_name = 'ten_cong_viec'
    _order = 'do_uu_tien desc, han_hoan_thanh asc'

    ma_cong_viec = fields.Char(string='Mã công việc', required=True, copy=False, readonly=True, default='Mới')
    ten_cong_viec = fields.Char(string='Tên công việc', required=True)
    mo_ta = fields.Html(string='Mô tả chi tiết')
    
    du_an_id = fields.Many2one('quan.ly.du.an', string='Thuộc Dự án', required=True, ondelete='cascade')
    phong_ban_id = fields.Many2one(related='du_an_id.phong_ban_id', string='Phòng ban', store=True, readonly=True)

    def _get_default_nguoi_phu_trach(self):
        return self.env.user.employee_id.id if self.env.user.employee_id else False

    nguoi_giao_viec_id = fields.Many2one('quan.ly.nhan.su', string='Người phụ trách', default=_get_default_nguoi_phu_trach)
    nhan_vien_tham_gia_ids = fields.Many2many('quan.ly.nhan.su', string='Nhân viên tham gia')   

    do_uu_tien = fields.Selection([('0', 'Thấp'), ('1', 'Trung bình'), ('2', 'Cao'), ('3', 'Khẩn cấp')], string='Độ ưu tiên', default='1')
    do_kho = fields.Selection([('rat_de', 'Rất dễ'), ('de', 'Dễ'), ('trung_binh', 'Trung bình'), ('kho', 'Khó'), ('rat_kho', 'Rất khó')], string='Độ khó', default='trung_binh')

    trang_thai = fields.Selection([
        ('moi', 'Mới'), ('dang_lam', 'Đang thực hiện'), ('cho_duyet', 'Chờ duyệt'), 
        ('hoan_thanh', 'Hoàn thành'), ('huy', 'Đã hủy')
    ], string='Trạng thái', default='moi', group_expand='_expand_groups')

    tien_do = fields.Integer(string='Tiến độ (%)', default=0)
    hien_thi_tien_do = fields.Integer(related='tien_do', string='Biểu đồ tiến độ', readonly=True)

    ngay_bat_dau = fields.Date(string='Ngày bắt đầu', default=fields.Date.today)
    han_hoan_thanh = fields.Date(string='Hạn hoàn thành', required=True)
    ngay_hoan_thanh_thuc_te = fields.Date(string='Ngày xong thực tế', readonly=True)
    
    thoi_luong_ngay = fields.Integer(string='Thời lượng (Ngày)', compute='_compute_thoi_luong', store=True)
    so_ngay_qua_han = fields.Integer(string='Quá hạn (Ngày)', compute='_compute_trang_thai_deadline', store=True)
    trang_thai_deadline = fields.Selection([('dung_han', 'Đúng hạn'), ('tre_han', 'Trễ hạn'), ('sap_den_han', 'Sắp đến hạn')], string='Tình trạng hạn', compute='_compute_trang_thai_deadline', store=True)

    gio_du_kien = fields.Float(string='Giờ dự kiến (Man-hour)', default=1.0)
    gio_thuc_te = fields.Float(string='Giờ thực tế')
    don_gia_gio = fields.Float(string='Đơn giá/Giờ', default=200000)
    chi_phi_du_kien = fields.Float(string='Chi phí dự kiến', compute='_compute_chi_phi', store=True)
    chi_phi = fields.Float(string='Chi phí thực tế', compute='_compute_chi_phi', store=True)

    loai_cong_viec = fields.Selection([
        ('dev', 'Lập trình (Code)'),
        ('tester', 'Kiểm thử (Test Case/Bug)'),
        ('ba', 'Phân tích (Tài liệu/Yêu cầu)'),
        ('khac', 'Khác')
    ], string='Loại công việc', default='dev', required=True)

    file_ids = fields.Many2many(
        'ir.attachment', 
        string='File đính kèm',
        help='Tải lên code hoặc tài liệu liên quan'
    )
    
    ai_danh_gia_code = fields.Html(string='🤖 AI Review Code', readonly=True, help="Kết quả đánh giá từ AI Senior Dev")

    def action_open_upload_wizard(self):
        return {
            'name': 'Nộp Nhiều File',
            'type': 'ir.actions.act_window',
            'res_model': 'quan.ly.upload.code.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cong_viec_id': self.id}
        }

    def action_ai_review_code(self):
        self.ensure_one()
        
        if not self.file_ids:
            raise UserError("Vui lòng upload ít nhất 1 file trước khi yêu cầu AI đánh giá!")
        
        API_KEY = "YOUR_GEMINI_API_KEY_HERE" 
        MODEL_NAME = "gemini-2.5-flash"
        
        if not API_KEY or API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            raise UserError("Chưa cấu hình API Key!")

        combined_content = ""
        file_count = 0
        
        for file in self.file_ids:
            try:
                if file.datas:
                    content = base64.b64decode(file.datas).decode('utf-8', errors='ignore')
                    combined_content += f"\n\n--- FILE: {file.name} ---\n{content}\n--- END FILE ---\n"
                    file_count += 1
            except Exception:
                combined_content += f"\n[File {file.name} không đọc được nội dung text]\n"

        if len(combined_content) > 60000:
            combined_content = combined_content[:60000] + "\n...(Nội dung quá dài, đã cắt bớt)..."

        role_prompt = ""
        task_specific_prompt = ""

        role_title = "Senior Technical Lead"
        tech_context = "Software Engineering"
        if self.loai_cong_viec == 'ba': 
            role_title = "Senior Business Analyst"
            tech_context = "Business Requirements Analysis"
        elif self.loai_cong_viec == 'tester': 
            role_title = "QA/QC Manager"
            tech_context = "Quality Assurance & Testing"

        full_prompt = (
            f"--- ROLE & PERSONA ---\n"
            f"Bạn là {role_title} với 15 năm kinh nghiệm trong lĩnh vực {tech_context}. "
            f"Tính cách: Nghiêm khắc, tỉ mỉ, không chấp nhận sự cẩu thả hoặc gian lận.\n\n"

            f"--- TASK CONTEXT (ĐỀ BÀI) ---\n"
            f"- Tên Task: '{self.ten_cong_viec}'\n"
            f"- Yêu cầu chi tiết: {self.mo_ta or 'Dựa theo tên task để suy luận nghiệp vụ'}.\n\n"

            f"--- SUBMITTED CONTENT (BÀI LÀM) ---\n"
            f"{combined_content}\n\n"

            f"--- AUDIT PROTOCOL (QUY TRÌNH KIỂM TRA BẮT BUỘC) ---\n"
            f"Bước 1: RELEVANCE CHECK (Kiểm tra sự liên quan - QUAN TRỌNG NHẤT)\n"
            f"   - So sánh nghiệp vụ trong Code/Tài liệu với Yêu cầu Task.\n"
            f"   - Ví dụ: Task là 'Quản lý Sinh viên' (Student, GPA, Class) mà code lại chứa 'Order, Product, Inventory' (Bán hàng) -> LẬP TỨC ĐÁNH GIÁ 0%.\n"
            f"   - Nếu code chỉ là khung (boilerplate) chưa có logic nghiệp vụ -> Đánh giá dưới 10%.\n\n"

            f"Bước 2: QUALITY CHECK (Đánh giá chất lượng)\n"
            f"   - Chỉ khi Bước 1 thông qua, mới bắt đầu chấm điểm logic, cú pháp, và độ hoàn thiện.\n"
            f"   - Tìm các lỗi tiềm ẩn (Bugs, Security, Performance).\n\n"

            f"--- OUTPUT REQUIREMENTS ---\n"
            f"Trả về JSON thuần túy (Raw JSON), không Markdown. Cấu trúc:\n"
            f"{{\n"
            f"  \"completion_percentage\": (integer: 0-100),\n"
            f"  \"review_html\": (string: HTML content).\n"
            f"}}\n\n"

            f"Yêu cầu định dạng 'review_html':\n"
            f"- Nếu Lạc đề/Gian lận: Dùng thẻ <h4 style='color: red;'>⚠️ CẢNH BÁO: CODE KHÔNG HỢP LỆ</h4> và giải thích tại sao.\n"
            f"- Nếu Tốt: Dùng thẻ <ul>, <li> để liệt kê điểm tốt/điểm cần sửa. Sử dụng <b> để nhấn mạnh keywords.\n"
            f"- Giọng văn: Chuyên nghiệp, thẳng thắn, mang tính xây dựng (Constructive Feedback)."
        )

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(data), timeout=60)
            
            if response.status_code != 200:
                raise UserError(f"Lỗi API: {response.text}")
            
            result = response.json()
            if not result.get('candidates'): raise UserError("AI không phản hồi.")
            
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            review_data = json.loads(ai_text)

            percent = review_data.get('completion_percentage', 0)
            
            new_status = 'dang_lam'
            if percent == 0: new_status = 'moi'
            elif 1 <= percent <= 89: new_status = 'dang_lam'
            elif 90 <= percent <= 99: new_status = 'cho_duyet'
            elif percent == 100: new_status = 'hoan_thanh'
            
            review_content = review_data.get('review_html', '')
            
            header_color = "#166534"
            bg_color = "#f0fdf4"
            if self.loai_cong_viec == 'ba': header_color = "#0056b3"; bg_color = "#e3f2fd"
            elif self.loai_cong_viec == 'tester': header_color = "#b91c1c"; bg_color = "#fef2f2"

            final_review_html = f"""
                <div style="background-color: {bg_color}; padding: 15px; border: 1px solid #ccc; border-radius: 8px;">
                    <h4 style="color: {header_color}; margin-top:0;">🤖 KẾT QUẢ ĐÁNH GIÁ ({file_count} FILES)</h4>
                    <p><b>Tiến độ đánh giá:</b> <span style="font-size:1.2em; color:#d97706; font-weight:bold;">{percent}%</span></p>
                    <hr/>
                    {review_content}
                </div>
            """

            self.write({
                'tien_do': percent,
                'trang_thai': new_status,
                'ai_danh_gia_code': final_review_html
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'quan.ly.cong.viec',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'current',
            }

        except Exception as e:
            raise UserError(f"Lỗi hệ thống: {str(e)}")

    @api.onchange('du_an_id')
    def _onchange_du_an_filter_nhan_su(self):
        if self.du_an_id:
            thanh_vien_ids = self.du_an_id.thanh_vien_ids.mapped('nhan_su_id.id')
            if self.du_an_id.quan_ly_id:
                thanh_vien_ids.append(self.du_an_id.quan_ly_id.id)
            return {'domain': {'nhan_vien_tham_gia_ids': [('id', 'in', thanh_vien_ids)]}}
        return {'domain': {'nhan_vien_tham_gia_ids': []}}

    @api.constrains('ngay_bat_dau', 'han_hoan_thanh', 'du_an_id')
    def _check_dates_vs_project(self):
        for rec in self:
            if rec.ngay_bat_dau and rec.han_hoan_thanh and rec.ngay_bat_dau > rec.han_hoan_thanh:
                raise ValidationError("Lỗi: Ngày bắt đầu không thể sau Hạn hoàn thành!")
            
            if rec.du_an_id.ngay_ket_thuc and rec.han_hoan_thanh > rec.du_an_id.ngay_ket_thuc:
                raise ValidationError(f"Lỗi Logic: Hạn chót của công việc ({rec.han_hoan_thanh}) không được vượt quá ngày kết thúc của Dự án ({rec.du_an_id.ngay_ket_thuc})!")

    @api.depends('ngay_bat_dau', 'han_hoan_thanh')
    def _compute_thoi_luong(self):
        for rec in self:
            if rec.ngay_bat_dau and rec.han_hoan_thanh:
                delta = rec.han_hoan_thanh - rec.ngay_bat_dau
                rec.thoi_luong_ngay = delta.days + 1
            else:
                rec.thoi_luong_ngay = 0

    @api.depends('gio_du_kien', 'gio_thuc_te', 'don_gia_gio')
    def _compute_chi_phi(self):
        for rec in self:
            rec.chi_phi_du_kien = rec.gio_du_kien * rec.don_gia_gio
            rec.chi_phi = rec.gio_thuc_te * rec.don_gia_gio

    @api.depends('tien_do', 'han_hoan_thanh', 'trang_thai')
    def _compute_trang_thai_deadline(self):
        today = date.today()
        for rec in self:
            rec.so_ngay_qua_han = 0
            
            if rec.trang_thai == 'hoan_thanh' or rec.tien_do == 100:
                rec.trang_thai_deadline = 'dung_han'
            elif rec.han_hoan_thanh:
                delta = (rec.han_hoan_thanh - today).days
                
                if delta < 0:
                    rec.trang_thai_deadline = 'tre_han'
                    rec.so_ngay_qua_han = abs(delta)
                elif delta <= 2:
                    rec.trang_thai_deadline = 'sap_den_han'
                else:
                    rec.trang_thai_deadline = 'dung_han'
            else:
                rec.trang_thai_deadline = False

    @api.onchange('tien_do')
    def _onchange_tien_do(self):
        if self.tien_do == 0:
            self.trang_thai = 'moi'
            self.ngay_hoan_thanh_thuc_te = False
        elif 1 <= self.tien_do <= 89:
            self.trang_thai = 'dang_lam'
            self.ngay_hoan_thanh_thuc_te = False
        elif 90 <= self.tien_do <= 99:
            self.trang_thai = 'cho_duyet'
            self.ngay_hoan_thanh_thuc_te = False
        elif self.tien_do == 100:
            self.trang_thai = 'hoan_thanh'
            self.ngay_hoan_thanh_thuc_te = date.today()

    @api.onchange('trang_thai')
    def _onchange_trang_thai(self):
        if self.trang_thai == 'moi':
            self.tien_do = 0
            self.ngay_hoan_thanh_thuc_te = False
        elif self.trang_thai == 'dang_lam':
            if self.tien_do == 0 or self.tien_do >= 90:
                self.tien_do = 50 
            self.ngay_hoan_thanh_thuc_te = False
        elif self.trang_thai == 'cho_duyet':
            if self.tien_do < 90 or self.tien_do == 100:
                self.tien_do = 90
            self.ngay_hoan_thanh_thuc_te = False
        elif self.trang_thai == 'hoan_thanh':
            self.tien_do = 100
            if not self.ngay_hoan_thanh_thuc_te:
                self.ngay_hoan_thanh_thuc_te = date.today()

    def write(self, vals):
        res = super(QuanLyCongViec, self).write(vals)
        if 'tien_do' in vals:
            for rec in self:
                rec._onchange_tien_do()
        return res

    @api.model
    def create(self, vals):
        if vals.get('ma_cong_viec', 'Mới') == 'Mới':
            vals['ma_cong_viec'] = self.env['ir.sequence'].next_by_code('quan.ly.cong.viec') or 'CV-Mới'
        return super(QuanLyCongViec, self).create(vals)

    @api.model
    def _expand_groups(self, states, domain, order):
        return ['moi', 'dang_lam', 'cho_duyet', 'hoan_thanh', 'huy']

    def action_confirm_upload(self):
        self.ensure_one()
        for file in self.file_ids:
            file.write({
                'cong_viec_id': self.cong_viec_id.id
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công!',
                'message': 'Đã nộp các file thành công. Hãy bấm AI Đánh giá.',
                'type': 'success',
                'sticky': False,
            }
        }