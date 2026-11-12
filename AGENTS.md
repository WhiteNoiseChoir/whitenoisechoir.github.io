# WhiteNoiseChoir — Quy tắc vận hành cố định (2026-11-12)

> Chính sách do chủ dự án yêu cầu, áp dụng cho **mọi lần tạo bản phối, dựng video và mở rộng kho âm thanh**. Phải đọc và thực thi trước khi xử lý nguồn âm thanh ngoài. Đây là yêu cầu lâu dài, không phải yêu cầu chỉ cho V4/V5.

## NGUYÊN TẮC BẮT BUỘC: CẦN NGUỒN NGOÀI → THU GOM VÀ NHẬP KHO LUÔN

**Không chỉ tìm một đường dẫn rồi gắn trực tiếp vào timeline.** Mỗi khi bản phối cần một âm thanh chưa có nguồn đủ tốt trong kho WhiteNoiseChoir, nhân tiện tìm kiếm bên ngoài phải **thu gom file gốc thực tế và nhập vào kho âm thanh dùng chung** để mọi bản phối sau tái sử dụng được.

Quy trình bắt buộc:

1. **Tra kho nội bộ trước** bằng tên, nhóm, alias, metadata, đặc trưng âm thanh; tránh tải trùng.
2. **Tìm nguồn bên ngoài** khi không có file đủ phù hợp; chọn bản ghi tự nhiên, đúng sound identity, phù hợp bối cảnh, ưu tiên nguồn gốc rõ ràng và giấy phép CC0/giấy phép phù hợp nhu cầu phát hành. Không mặc định mọi âm thanh đều không có bản quyền.
3. **Tải bản ghi gốc** (WAV/FLAC/MP3/M4A đúng tệp được cung cấp; ưu tiên bản gốc chất lượng cao, không lấy preview bitrate thấp làm master nếu có bản tốt hơn). Không trộn lẫn metadata thu gom với asset đã sở hữu.
4. **Xác minh file thực**: magic bytes/codec, khả năng decode bằng ffprobe/ffmpeg, thời lượng, kích thước, kênh, sample rate, kiểm tra âm thanh sai danh mục/giọng nói/nhạc, SHA-256; loại trùng theo checksum; nghe kiểm tra hoặc đánh dấu "chưa nghe QA" một cách minh bạch.
5. **Lưu bền vững vào Cloudflare R2** của WhiteNoiseChoir, với key chuẩn của kho tài sản (ưu tiên content-addressed, ví dụ `asset-library/raw/sha256/ab/<sha256>.<ext>`, phù hợp cấu trúc hiện hành). Giữ bản gốc, không chỉ lưu link bên ngoài. Không ghi credential/token vào repo, log hoặc báo cáo.
6. **Bổ sung metadata/catalog index**: ID/bucket key, tên VI/EN, nhóm và tags, sound identity, source URL, creator, giấy phép, attribution, thời lượng, codec, channels, bitrate/sample rate, checksum, kích thước, ngày nhập, tình trạng QA và trạng thái quyền sử dụng. Tuân thủ cơ chế vault riêng nếu dữ liệu nội bộ bị giới hạn truy cập. Không công khai danh sách tài sản private không cần thiết.
7. **Kiểm thử truy cập từ Studio**: R2 HTTP object và CORS, tải/giải mã âm thanh, phát thử đúng âm, timeline và xuất WAV; chống lặp gây lỗi. Nếu truy cập thất bại, phải báo lỗi và xử lý trước khi quảng bố "đã nhập kho".
8. **Dùng lại asset nội bộ trong bản phối** và cập nhật các dự án đang cần âm thanh đó; không để phụ thuộc vào CDN/preview bên thứ ba lâu dài.

## Trạng thái phải phân biệt rõ

- `DISCOVERED`: mới tìm thấy URL/metadata, chưa có file.
- `DOWNLOADED`: đã tải file vào vùng làm việc, chưa xác minh hoặc chưa lưu bền vững.
- `VALIDATED`: file tải xong và qua xác minh kỹ thuật/nguồn/giấy phép, chưa chắc đã vào R2.
- `STORED_R2`: đã upload và xác minh đối tượng tồn tại, checksum/độ dài phù hợp.
- `CATALOGED`: đã có metadata/ID nội bộ liên kết đúng với object thật.
- `STUDIO_READY`: đã kiểm tra Studio tải, phát, đưa timeline và xuất WAV (nếu khả thi).
- `QA_LISTENING_PENDING` / `APPROVED`: phân biệt chất lượng nghe chưa nghiệm thu và đã nghiệm thu.

**Không được gọi link preview bên ngoài, record nghiên cứu hay key tưởng tượng là “đã bổ sung vào kho”.** Nếu không có quyền upload R2, tệp gốc yêu cầu đăng nhập, giới hạn tool hoặc nguồn không đáp ứng giấy phép, báo đúng chỗ bị chặn. Có thể thêm lớp preview `mute: true` để nghe thử, ghi rõ `EXTERNAL_PREVIEW_PENDING_IMPORT`, nhưng đây chỉ là biện pháp tạm; phải quay lại nhập R2 khi có thể.

## Định hướng phối âm

- Kho âm thanh được mở rộng liên tục **thông qua nhu cầu thật của từng bản phối**, không phải chỉ thu gom file nhiều mà không phân loại.
- Độ phong phú của cảnh rừng đến từ layering, stereo space, timeline và nhiều sự kiện nhỏ tự nhiên; không chỉ đẩy mưa/lửa lên lớn.
- Giữ nguyên bản phối cũ đã duyệt; tạo URL bản mới riêng khi cần so sánh. Không thay nguồn, phá timeline hoặc làm hỏng xuất WAV đang hoạt động.
- Một nguồn bên ngoài thu gom một lần có thể dùng cho hàng chục bản phối; kiểm tra trùng trước khi tải.
- Báo cáo sau mỗi lần thêm nguồn: số lượng phát hiện, số bản ghi tải được, số nguồn thực sự đã nhập R2, số đã sẵn sàng Studio, số còn thiếu và lý do.

## Hạng mục nguồn ngoài đang cần xử lý

V4 Living Forest Creek / V5 The Forest Is Alive Tonight hiện dùng **6 nguồn ngoài phân biệt, 20 clip trên hai timeline**, vẫn chủ yếu là MP3 preview hoặc URL bên thứ ba (dế đêm, ếch/dế ven suối ×2, giọt nước mái hiên, chó ngủ, tiếng gỗ). **Các preview này chưa đồng nghĩa đã import vào R2**. Khi tiếp tục dự án, ưu tiên nhập bản gốc vào R2 và đổi sang ID nội bộ sau khi xác minh.

Source of truth: GitHub repo `WhiteNoiseChoir/whitenoisechoir.github.io`, production `https://whitenoisechoir.com/`, Cloudflare R2 cho tài sản âm thanh, Vietnamese Studio `/vi/`.
