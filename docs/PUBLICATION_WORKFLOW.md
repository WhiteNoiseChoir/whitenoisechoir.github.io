# WhiteNoiseChoir — quy trình xuất bản bản phối chính thức
Ngày áp dụng: 2026-11-12 · Khóa chặn Public v1

## Ba khu vực có nhiệm vụ khác nhau

1. **Trang chủ `/` (English Studio):** chỉ phối âm thời lượng cố định **10 phút (600 giây)**. Một nút tạo và tải WAV. Không cho dựng video MP4, không chọn thời lượng 30/60 phút; không hiển thị preset cũ. Bản WAV có thể được tạo nội bộ trong trình duyệt để tải xuống nhưng không có mục ghép video.
2. **`/vi/` và dự án nháp `/vi/<project>/`:** xưởng sản xuất, chỉnh timeline, xuất WAV, dựng video và ghép MP4 để kiểm tra. Dự án V3/V4/V5 nháp không tự thành trang công khai.
3. **`/library/` và `/<English-Slug>/`:** chỉ bản đã sản xuất, duyệt và **chủ dự án yêu cầu Public**. Thư viện hiển thị lưới video; URL tiếng Anh riêng, metadata SEO, video đã ghép, timeline khóa chỉnh sửa. Menu chọn bản công khai trên Studio chỉ lấy từ chính manifest đã duyệt.

## Quy trình sản xuất → Public (bắt buộc)

### A. Sản xuất và kiểm tra hoàn chỉnh

- Chốt 600 giây âm thanh WAV, đã nghe kiểm tra và xác minh không bị im lặng, clipping hoặc lỗi giải mã.
- Chốt clip AI/nguyên liệu, thực hiện hậu kỳ nếu cần rồi ghép thành **MP4 cuối cùng xấp xỉ 600 giây, có âm thanh**.
- Tạo thêm bản MP3/AAC 600 giây từ cùng master đã duyệt cho chế độ audio-only, giữ WAV gốc làm tài sản tải về.
- Tạo poster thumbnail 16:9. Chỉ dùng file cuối đã duyệt, không lấy bản render thử.
- Lưu WAV, compressed audio, MP4 và thumbnail vào Cloudflare R2, ghi SHA256, codec, thời lượng, giấy phép các nguồn/creator và kiểm tra HTTP 206 Range + CORS từ `whitenoisechoir.com`.
- Lưu snapshot timeline bao gồm các lớp âm, start/duration/gain/group, không chỉ URL nguồn ngoài.

### B. SEO và duyệt

- Đặt English slug duy nhất, ví dụ **`Living-Forest-Creek`** (chỉ tạo URL khi đã Public).
- Viết title, meta description, nội dung biên tập tiếng Anh độc lập, alt cho thumbnail, từ khóa tập trung không cannibalize.
- Thêm schema VideoObject, AudioObject, BreadcrumbList, og:image, og:video và canonical.
- Chủ dự án xác nhận hoàn tất sản xuất + duyệt nghe/nhìn và ra lệnh **Public**; không suy diễn từ việc đã render hoặc tải lên R2.
- Ghi nhận **`ownerApproved:true`**, **`productionComplete:true`**, **`qaApproved:true`**, **`status:"published"`**, ngày công khai, và bốn URL R2 vào `data/published-mixes.json`. Đây là nguồn sự thật; không có nút Public trực tiếp trong trình duyệt của khách.

### C. Cổng xuất bản tự động

Workflow `.github/workflows/publish_approved_mixes.yml` chạy khi manifest đổi:
1. Xác nhận slug, quyền phê duyệt, SEO, nội dung bài, snapshot timeline và thời lượng 10 phút.
2. Kiểm tra **bốn URL R2 thực tế** (MP4 10 phút, thumbnail, audio-only 10 phút, WAV master), MIME, HTTP Range/CORS.
3. Tạo trang HTML SEO riêng với player và **timeline hiển thị cố định**. Trang không tải Studio editor và không cho chỉnh âm thanh.
4. Tạo card video ở `/library/` và cập nhật `sitemap.xml`.
5. Commit các HTML đã sinh. GitHub Pages deploy thành công thì mới xác nhận URL live.

Nếu thiếu một trong các điều kiện trên: **chặn xuất bản**. Không để dự án nháp vào sitemap hoặc hiển thị như bản phát hành.

## Phát đến 10 giờ

- Trang Public mặc định chọn **10 giờ**, có lựa chọn 1/3/5/8/10 giờ và Video+Audio / Audio-only.
- Trình duyệt **lặp lại video MP4 10 phút hoặc compressed audio 10 phút**, đặt bộ đếm giờ và dừng khi đủ thời gian nghe. **Không render hoặc tải tệp 10 giờ hàng chục GB**.
- Tính giờ theo thời gian đang phát, dừng đồng hồ khi pause; hiển thị thời gian đã nghe và thời lượng đặt.
- Cho phép Audio-only để hỗ trợ nghe lâu, màn hình khóa trên thiết bị hỗ trợ. Không thể bảo đảm trình duyệt, hệ điều hành hoặc mạng không tạm dừng video; cần QA thiết bị thực tế trước khi tuyên bố phát liên tục 10 giờ được kiểm chứng.
- Điểm nối 10 phút phải được thử nghe/nhìn. Nếu cần lặp chính xác tuyệt đối, nghiên cứu HLS/MSE server-side crossfade, không tuyên bố thuộc tính 'gapless' chỉ vì HTMLMediaElement.loop=true.

## Các URL đang tồn tại

- Trang chủ: `https://whitenoisechoir.com/`.
- Studio sản xuất: `https://whitenoisechoir.com/vi/`.
- Bản nháp V4: `https://whitenoisechoir.com/vi/Living-Forest-Creek/`.
- Bản nháp V5: `https://whitenoisechoir.com/vi/The-Forest-Is-Alive-Tonight/`.
- Thư viện Public: `https://whitenoisechoir.com/library/`.
- **Chưa có bản nào được xác nhận Public.** `data/published-mixes.json` hiện là `[]`, vì vậy URL công khai `/Living-Forest-Creek/` chưa được tạo.

## Quản lý dữ liệu và trách nhiệm

- Không tự động Public từ một URL MP4, một file WAV hay một ảnh thumbnail nếu thiếu phê duyệt.
- Không đưa WAV chưa nghiệm thu, MP3 preview bitrate thấp hoặc asset chưa import R2 vào phát hành.
- Source list của mỗi bản phải được bảo tồn theo quy tắc kho dài hạn trong `AGENTS.md`.
- Nếu yêu cầu bỏ Public, xoá entry manifest rồi để pipeline xoá trang HTML do chính nó tạo, card trong thư viện và URL khỏi sitemap; kiểm tra cache CDN/search sau đó.
