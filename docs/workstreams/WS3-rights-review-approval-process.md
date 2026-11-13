# WS3 V2 — Duyệt quyền và nhập thử audio từ music candidates

## Kết quả kỹ thuật hiện tại

- Candidates trong private R2 là **metadata nguồn**, không phải file audio hoặc giấy phép đã xác minh toàn diện.
- `scripts/prepare_music_rights_review.py` đọc ứng viên Wikimedia Commons thuộc CC0/CC BY 3.0/4.0, lọc URL và kích thước, hỏi lại Commons API để kiểm tra nguồn, phiên bản và giấy phép hiện tại; lập **tối đa 8 hồ sơ**.
- Hồ sơ đầy đủ chỉ được lưu trong R2 private: `internal/music-candidates/rights-review-queue/v1/<run-id>-<attempt>.json`. Artifact trên GitHub chỉ có thống kê tổng hợp, không chứa URL chi tiết.
- Mọi trường phê duyệt mặc định `null`, không có workflow nào tự thay thành `true`.

## Những gì người duyệt phải làm

1. Truy cập hồ sơ R2 private bằng tài khoản được cấp quyền; đối chiếu trang Commons chính thức, người tạo và lời mô tả nguồn.
2. **Xác minh riêng quyền với recording/performance và quyền với underlying composition** (nếu file là một đoạn chơi bài nhạc, bản ghi cover, bản phối có tác phẩm khác thì giấy phép upload alone không đủ). Với tiếng nhạc cụ đơn giản, ghi rõ cơ sở nhận định không có tác phẩm được bảo hộ độc lập, thay vì mặc định không có bản quyền.
3. Kiểm tra điều khoản CC BY: tên tác giả, URL giấy phép, phiên bản, cách attribution, quyền remix và phân phối thương mại. CC0 cũng cần xác minh người công bố có quyền áp dụng CC0.
4. Chỉ khi có bằng chứng đầy đủ, tạo object JSON trong R2 private tại `internal/music-candidates/approved-audio/v1/<candidate-id>.json`. Sao chép `approval_template` từ queue, ghi đè các trường bằng kết quả **đã xác minh thực**; điền `reviewed_by`, `reviewed_at`, `evidence_urls`, `license`, `source_revision_sha1`, `attribution_text` (đặc biệt bắt buộc cho CC BY).
5. Người duyệt phải tự đối chiếu mỗi điều kiện; không dùng tool để tự động sinh `true` dựa duy nhất trên nhãn license của source.

## Gate nhập file

`scripts/pilot_import_music_candidates.py --ingest --batch-size 8 --max-records 8000 --byte-budget-mib 250`:

- Chỉ Commons, nguồn/media HTTPS cho phép, source license được kiểm tra trước và không thay đổi, kích thước mỗi file <=32 MiB.
- CC0 và CC BY 3.0/4.0 được xét, nhưng **CC BY chỉ đi qua khi attribution hợp lệ và hồ sơ độc lập được duyệt**; không có trường hợp nới lỏng.
- Không tự download bất kỳ file nào khi thiếu object approval R2 đúng schema.
- Lấy original media, giới hạn byte/redirect, `ffprobe`, SHA-256 chống trùng với asset library.
- Lưu binary content-addressed vào private R2, xác minh HEAD length + sha metadata; ghi sidecar chứng cứ, ngăn auto xuất bản.
- `STORED_R2_QA_LISTENING_PENDING` **không đồng nghĩa** `CATALOGED`, `STUDIO_READY` hoặc an toàn xuất video thương mại. Các trạng thái này phải nghiệm thu riêng.

## Báo cáo

Đọc `MUSIC_RIGHTS_REVIEW_FINAL` và `MUSIC_AUDIO_PILOT_FINAL` trong GitHub Actions, phân biệt: nguồn được kiểm tra, hồ sơ đã duyệt, bytes tải, file validated, file STORED_R2, files cataloged / studio-ready. Nếu 0 approval, 0 binary import là đúng theo fail-closed policy.

## Chống xung đột

Workflow chỉ chạy trên nhánh `feature/music-verified-audio-intake-20261113`, mọi PR đều Draft. Không sửa `main`, Studio, mixer, publication manifest hoặc website.
