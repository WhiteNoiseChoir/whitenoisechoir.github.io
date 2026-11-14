# WhiteNoiseChoir — cầu nối ChatGPT ↔ R2 qua GitHub Private

## Thực trạng và phạm vi
- Repo source: `WhiteNoiseChoir/whitenoisechoir.github.io` (**Public**), GitHub App của ChatGPT đã cài cho mọi repository của organization WhiteNoiseChoir.
- Bucket R2: `whitenoisechoir-media`. GitHub Actions đã có quyền đọc qua R2 secrets hiện hữu.
- Chỉ xuất **metadata sidecar JSON** và danh sách tên object R2 (không copy audio); chỉ mục JSONL dạng nhóm 250 bản ghi mỗi tệp.
- Đích là **duy nhất** `WhiteNoiseChoir/wnc-metadata-index` và bắt buộc **Private**. Script xác minh GitHub API trước khi đọc R2, và xác minh lần nữa trước khi push; nếu repository Public hoặc thiếu quyền, dừng và không upload.
- Không dùng `GITHUB_TOKEN` của repo Public để giả định ghi xuyên repo (token mặc định chỉ dùng cho source repo).

## Những việc người sở hữu tài khoản phải làm (không có thao tác GitHub create repository/Actions secrets trong connector hiện tại)
1. Tạo repo `WhiteNoiseChoir/wnc-metadata-index` ở chế độ **Private**, bật README và nhánh `main`: https://github.com/organizations/WhiteNoiseChoir/repositories/new
2. Tạo **fine-grained personal access token** với **Repository access: Only select repositories → wnc-metadata-index** và **Contents: Read and write** (Metadata mặc định). Không cấp Administration, Actions, Secrets hay quyền vào tất cả repo.
3. Ở repo nguồn `WhiteNoiseChoir/whitenoisechoir.github.io` → Settings → Secrets and variables → Actions → New repository secret: tên `WNC_METADATA_REPO_TOKEN`; dán token tại giao diện GitHub, KHÔNG dán trong ChatGPT hoặc issue/PR.
4. Mở Actions → workflow `WNC R2 metadata to PRIVATE GitHub index (manual until configured)` → Run workflow trên `main`.
5. Kiểm tra repo Private có `index/manifest.json`, `index/groups/<group>/part-001.jsonl`. ChatGPT dùng GitHub connector đọc/tìm kiếm file từ repository Private.
6. Chỉ khi đã xác nhận không lộ dữ liệu, mới bật schedule đồng bộ 4 giờ/lần.

## Phân biệt trạng thái
- `R2_OBJECT_LISTED`: tên object xuất hiện trong danh sách R2, **không** bảo đảm bytes đúng SHA, trình duyệt giải mã được hoặc quyền phát hành đã duyệt.
- `METADATA_ONLY`: có sidecar nhưng không xác minh được object âm thanh, tạo `candidate-<sha>` thay vì `r2-<sha>`.
- `LICENSE_DECLARED_REVIEW`: có khai báo giấy phép từ metadata; vẫn phải kiểm tra nguồn và điều kiện phát hành.
- `NOT_VERIFIED_BY_INDEX`: chưa có kiểm thử WebAudio/Studio trong đợt đồng bộ metadata.

## Ví dụ truy vấn sau khi đồng bộ
"Trong repo WhiteNoiseChoir/wnc-metadata-index, đọc index/manifest.json, tìm các shard nhóm lake/water. Chọn 15 file có R2_OBJECT_LISTED, license CC0, độ dài hơn 120 giây, chưa được xác nhận phát và đề xuất bước QA trước khi thêm vào bản phối."

## Giới hạn
- Giữ nguyên Studio asset catalog mã hóa trong R2. Cầu nối không làm lộ toàn bộ metadata qua repo Public.
- Không thể tự thao tác trên R2 trực tiếp chỉ với GitHub connector; mọi thay đổi R2 phải đi qua workflow có secret và kiểm định.
- Metadata nghiên cứu chưa có sidecar SHA trong các prefix liệt kê sẽ chưa xuất hiện. Muốn phủ hết các kho metadata discovery khác phải bổ sung trình xuất cho từng schema sau khi kiểm kê thực tế.
- Script chưa có snapshot thực tế cho tới khi tạo repo Private và thêm token.
