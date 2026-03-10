"""
System prompts cho các tình huống phân tích khác nhau
"""

SYSTEM_FULL_ANALYSIS = """Bạn là chuyên gia phân tích tài chính cấp cao chuyên về thị trường chứng khoán Việt Nam.
Bạn có kiến thức sâu về chuẩn mực kế toán VAS (Thông tư 200, 202), đặc thù ngành thép, và thị trường vốn Việt Nam.

## QUY TẮC BẮT BUỘC
1. KHÔNG tự tính toán số liệu — tất cả chỉ số đã được tính sẵn và truyền vào cho bạn. Hãy dùng trực tiếp.
2. Luôn cite số liệu cụ thể khi đưa ra nhận định (VD: "doanh thu 40.6 nghìn tỷ, +17.7% YoY")
3. Phân biệt rõ báo cáo riêng lẻ (công ty mẹ) vs hợp nhất — đây là sự khác biệt quan trọng
4. Với holding company: giải thích rõ bản chất, không áp các chỉ số vận hành thông thường
5. Luôn đề cập các flags/bất thường đã phát hiện trong phần rủi ro
6. Câu văn ngắn gọn, rõ ràng, tránh hoa mỹ

## FORMAT ĐẦU RA
Trả về JSON hợp lệ (không có markdown fence, không có text ngoài JSON):
{
  "executive_summary": "2-3 câu tóm tắt quan trọng nhất cho ban lãnh đạo",
  "highlights": [
    {"title": "...", "detail": "...", "sentiment": "positive|negative|neutral"}
  ],
  "risks": [
    {"title": "...", "detail": "...", "severity": "high|medium|low"}
  ],
  "sections": {
    "profitability": "Phân tích lợi nhuận (3-5 câu)",
    "liquidity": "Phân tích thanh khoản (2-3 câu)",
    "leverage": "Phân tích đòn bẩy (2-3 câu)",
    "cashflow": "Phân tích dòng tiền nếu có dữ liệu (2-3 câu)",
    "segment": "Phân tích theo phân khúc nếu có (2-3 câu)"
  },
  "outlook": "Nhận định ngắn hạn 1-2 quý tới (2-3 câu)"
}"""

SYSTEM_CHAT_QA = """Bạn là trợ lý phân tích báo cáo tài chính. Context báo cáo đã được cung cấp đầy đủ.

## NGUYÊN TẮC TRẢ LỜI
- Trả lời trực tiếp, ngắn gọn, cite số liệu cụ thể
- Nếu câu hỏi liên quan đến sự khác biệt riêng lẻ vs hợp nhất, giải thích rõ
- Nếu không có đủ dữ liệu để trả lời chắc chắn: nói rõ, không đoán mò
- Với holding company: nhắc nhở khi người dùng có thể đang hiểu nhầm

Trả về JSON:
{
  "answer": "Câu trả lời chi tiết",
  "cited_figures": ["figure1", "figure2"],
  "confidence": "high|medium|low",
  "caveat": "Lưu ý nếu có (optional)"
}"""

SYSTEM_COMPARISON = """Bạn là chuyên gia phân tích xu hướng tài chính đa kỳ.
Được cung cấp dữ liệu nhiều kỳ báo cáo, hãy phân tích xu hướng và động lực tăng trưởng.

Trả về JSON:
{
  "trend_summary": "Tóm tắt xu hướng tổng thể",
  "key_trends": [{"metric": "...", "trend": "...", "implication": "..."}],
  "turning_points": ["Điểm chuyển nếu có"],
  "forecast_note": "Nhận định ngắn"
}"""


def build_analysis_prompt(data, metrics, flags, language: str = "vi") -> str:
    """Build user prompt với data đã tính sẵn"""
    import json

    flag_texts = [f"[{f.type.value}] {f.code}: {f.message}" for f in flags]

    # Key figures summary (dễ đọc cho LLM)
    key_figures = {}
    if metrics.revenue:
        key_figures["doanh_thu_thuan_ty"] = metrics.revenue
    if metrics.revenue_prev:
        key_figures["doanh_thu_ky_truoc_ty"] = metrics.revenue_prev
    if metrics.net_profit:
        key_figures["lnst_ty"] = metrics.net_profit
    if metrics.net_profit_prev:
        key_figures["lnst_ky_truoc_ty"] = metrics.net_profit_prev
    if metrics.gross_margin:
        key_figures["bien_ln_gop_pct"] = metrics.gross_margin
    if metrics.net_margin:
        key_figures["bien_ln_rong_pct"] = metrics.net_margin
    if metrics.total_assets:
        key_figures["tong_tai_san_ty"] = metrics.total_assets
    if metrics.equity:
        key_figures["vcsh_ty"] = metrics.equity
    if metrics.total_liabilities:
        key_figures["tong_no_ty"] = metrics.total_liabilities
    if metrics.subsidiary_income:
        key_figures["ln_cty_con_chuyen_ve_ty"] = metrics.subsidiary_income

    prompt = f"""Phân tích báo cáo tài chính sau:

## THÔNG TIN BÁO CÁO
- Công ty: {data.company_name} ({data.company_code})
- Kỳ: {data.period}
- Loại báo cáo: {"Hợp nhất (Consolidated)" if data.is_consolidated else "Công ty mẹ riêng lẻ (Parent Only)"}
- Holding company: {"CÓ — chủ yếu đầu tư vào công ty con" if data.is_holding_company else "Không"}

## CHỈ SỐ TÀI CHÍNH (đã tính bằng Python — dùng trực tiếp, không tính lại)
{json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2)}

## SỐ LIỆU CHÍNH (đơn vị: tỷ đồng)
{json.dumps(key_figures, ensure_ascii=False, indent=2)}

## BẤT THƯỜNG PHÁT HIỆN TỰ ĐỘNG
{chr(10).join(flag_texts) if flag_texts else "Không có bất thường đặc biệt"}

## PHÂN KHÚC KINH DOANH
{json.dumps(data.segments, ensure_ascii=False, indent=2) if data.segments else "Không có dữ liệu phân khúc"}

## THUYẾT MINH (trích)
{data.notes_text[:1500] if data.notes_text else "Không có"}

Hãy phân tích toàn diện và trả về JSON theo format đã quy định.
Ngôn ngữ: {"Tiếng Việt" if language == "vi" else "English"}"""

    return prompt


def build_chat_prompt(data, metrics, flags, question: str, history: list) -> tuple[str, list]:
    """Build messages cho Q&A session"""
    import json

    context_summary = f"""
CONTEXT BÁO CÁO: {data.company_name} {data.period} {"(Hợp nhất)" if data.is_consolidated else "(Công ty mẹ)"}
METRICS: {json.dumps(metrics.to_dict(), ensure_ascii=False)}
FLAGS: {[f.message for f in flags]}
SEGMENTS: {json.dumps(data.segments, ensure_ascii=False) if data.segments else "N/A"}
"""

    messages = []

    # Nếu có history, thêm vào
    for h in history[-6:]:  # Giới hạn 6 turns
        messages.append(h)

    # Nếu chưa có context trong history, thêm vào message đầu
    if not history:
        messages.append({
            "role": "user",
            "content": f"Context báo cáo:\n{context_summary}\n\nCâu hỏi: {question}"
        })
    else:
        messages.append({"role": "user", "content": question})

    return SYSTEM_CHAT_QA, messages
