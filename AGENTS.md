# WhiteNoiseChoir — Quy tắc vận hành cố định (2026-11-12)

> Chính sách do chủ dự án yêu cầu, áp dụng cho **mọi lần tạo bản phối, dựng video và mở rộng kho âm thanh**. Phải đọc và thực thi trước khi xử lý nguồn âm thanh ngoài. Đây là yêu cầu lâu dài, không phải yêu cầu chỉ cho V4/V5.

## CHIẾN LƯỢC CHÍNH — NHẬP KHO THEO NHU CẦU TỪNG BẢN PHỐI (CHỐT 2026-11-13)

**Không tự động tải toàn bộ metadata.** Metadata âm nhạc (2.559 bản ghi ở thời điểm chốt) là kho tra cứu ứng viên, không phải số file audio hay số asset Studio. Chủ dự án chọn **Just-in-Time Audio Acquisition** làm quy trình mặc định. Không quét, tải và nhập hàng loạt chỉ vì tồn tại metadata.

Khi chủ dự án yêu cầu tạo hoặc sửa một bản phối, thực hiện theo đúng thứ tự:
1. Phân tích nhu cầu bối cảnh, sound identity, timeline, thời lượng và các lớp âm còn thiếu.
2. Tra cứu asset sẵn có ở Studio/R2 trước để tái sử dụng và tránh tải trùng.
3. Nếu thiếu, tìm trong metadata R2; nếu không có bản phù hợp thì chủ động tìm trên Internet, không chuyển việc tự tìm nguồn cho người dùng.
4. Kiểm tra nguồn và giấy phép, kể cả quyền đối với tác phẩm, biểu diễn, bản ghi khi cần; không giả định Creative Commons của trang là đủ cho mọi trường hợp thương mại.
5. Tải file gốc có thể tiếp cận hợp pháp; kiểm tra magic bytes, codec, ffprobe, giải mã toàn bộ, thời lượng, kích thước và SHA-256; tránh tải trùng. Lưu file thực vào R2 qua workflow/credentials phù hợp và xác minh đối tượng bằng HEAD/checksum.
6. Đăng ký asset ID, R2 key, metadata, attribution và trạng thái QA vào catalog Studio theo cơ chế append-only; xác minh tải, CORS và phát trên Studio. Không tự tuyên bố đã nghe QA hay có quyền thương mại khi chưa xác minh.
7. Tạo và gửi JSON bản phối tương thích Studio với ID thật để chủ dự án tự nhập lên website và nghe thử. Không tạo ID giả, không tuyên bố hoàn thành nếu lớp audio chưa tồn tại.
8. Nếu bị 429/403 hoặc không có quyền tải, dừng tải không an toàn, ghi rõ trở ngại; có thể tìm phương án thay thế được cấp phép và báo riêng phần chưa hoàn tất.

**Giới hạn hoạt động nền:** Giữ các lịch quét/nhập hàng loạt ở trạng thái tạm dừng. Không tự tái khởi chạy WS3 hay đợt nhập toàn bộ 2.559 bản ghi trừ khi chủ dự án ra lệnh mới, rõ ràng. Chỉ thực hiện nhập riêng các âm thanh cần cho bản phối cụ thể khi được yêu cầu.

**Báo cáo:** Tách biệt số metadata ứng viên, số file âm thanh thật đã lưu R2 (khử trùng SHA), số asset có trong catalog Studio, số phát được, số được duyệt nghe và số được duyệt quyền phát hành. Chỉ số 96/96 trên Studio là số mục đang khớp bộ lọc / tổng asset không pending, không phải 96/2.559 đã nhập.



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

## QUY TRÌNH PUBLIC (2026-11-12) — QUY TẮC BẮT BUỘC

- Trang chủ `/`: bản phối **cố định 10 phút**, chỉ xuất/tải WAV, **không** ghép hoặc render MP4; ẩn toàn bộ preset chưa phát hành. Trang `/vi/` và các URL `/vi/<draft>/` tiếp tục là xưởng phối + ghép video để chủ dự án QA.
- **Không tự ý Public** khi mới có WAV, video ngắn, metadata hoặc chỉ có GitHub Pages deploy. Phải đợi **yêu cầu rõ ràng của chủ dự án**, xác minh MP4 cuối 10 phút đã ghép âm thanh, WAV master, bản audio-only nén, thumbnail, nguồn gốc/copyright, timeline và nội dung SEO tiếng Anh.
- Trình tự chuẩn: owner yêu cầu Public → cập nhật **`data/publication-requests.json`** chứa các bản được yêu cầu Public → workflow `.github/workflows/publish_approved_mixes.yml` kiểm tra bốn URL R2, MIME, HTTP Range/CORS, thời lượng và phê duyệt → tạo **`data/published-mixes.json`** + `/<English-Slug>/index.html` + lưới video `/library/` + sitemap. Không chỉnh public manifest thủ công để vượt qua gate.
- Bản Public có trang canonical tiếng Anh riêng, VideoObject/AudioObject/BreadcrumbList, OG/Twitter, nội dung editorial độc lập, **timeline âm thanh chỉ đọc** và trình phát lặp tối đa 10 giờ. Video/audio 10 phút được lặp trong trình duyệt; không tạo tệp 10 giờ khổng lồ. Không hứa playback 10 giờ liên tục trên mọi trình duyệt/màn hình khóa nếu chưa có kiểm thử thực tế.
- Các trang nháp (V3/V4/V5) không được chuyển thành trang SEO công khai nếu thiếu lệnh Public. Hiện public manifest là `[]`.
- Tệp yêu cầu Public trong repository công khai **không phải kho bí mật**; không lưu secrets, credential hoặc nội dung riêng tư cần bảo mật ở đó. Với release cần bảo mật trước ngày ra mắt, dùng private workflow/store.
- Chuẩn chi tiết: `docs/PUBLICATION_WORKFLOW.md`.
