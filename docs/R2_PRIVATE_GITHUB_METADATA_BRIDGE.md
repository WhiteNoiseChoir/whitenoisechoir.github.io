# WhiteNoiseChoir — cầu nối ChatGPT ↔ R2 qua GitHub Private

## Thực trạng và phạm vi
- Repo source: `WhiteNoiseChoir/whitenoisechoir.github.io` (**Public**), GitHub App của ChatGPT đã cài cho mọi repository của organization WhiteNoiseChoir.
- Bucket R2: `whitenoisechoir-media`. GitHub Actions đã có quyền đọc qua R2 secrets hiện hữu.
- Chỉ xuất **chỉ mục SQLite FTS5 canonical của WS1 trên R2** (19.680 thiên nhiên SHA unique + 2.559 ứng viên âm nhạc theo snapshot 13/11; số thực phải qua checksum/count), kết hợp role hints WS2 đã hoàn thành theo checkpoint R2. Không copy audio, không công khai chỉ mục. Mỗi JSONL chứa tối đa 100 bản ghi để GPT đọc nhanh.
- Đích là **duy nhất** `WhiteNoiseChoir/wnc-metadata-index` và bắt buộc **Private**. Script xác minh GitHub API trước khi đọc R2, và xác minh lần nữa trước khi push; nếu repository Public hoặc thiếu quyền, dừng và không upload.
- Không dùng `GITHUB_TOKEN` của repo Public để giả định ghi xuyên repo (token mặc định chỉ dùng cho source repo).

## Những việc người sở hữu tài khoản phải làm (không có thao tác GitHub create repository/Actions secrets trong connector hiện tại)
1. Tạo repo `WhiteNoiseChoir/wnc-metadata-index` ở chế độ **Private**, bật README và nhánh `main`: https://github.com/organizations/WhiteNoiseChoir/repositories/new
2. Tạo **fine-grained personal access token** với **Repository access: Only select repositories → wnc-metadata-index** và **Contents: Read and write** (Metadata mặc định). Không cấp Administration, Actions, Secrets hay quyền vào tất cả repo.
3. Ở repo nguồn `WhiteNoiseChoir/whitenoisechoir.github.io` → Settings → Secrets and variables → Actions → New repository secret: tên `WNC_METADATA_REPO_TOKEN`; dán token tại giao diện GitHub, KHÔNG dán trong ChatGPT hoặc issue/PR.
4. Sau khi cả repo Private và token đã được thiết lập, GPT có thể tự cập nhật file `ops/metadata_sync_request.json` trên main bằng commit có tiền tố `chore(metadata): sync-request` để kích hoạt workflow. Ngoài ra chủ repo vẫn có thể mở Actions → workflow `WNC R2 metadata to PRIVATE GitHub index (manual until configured)` → Run workflow trên `main`.
5. Kiểm tra repo Private có `index/manifest.json`, `index/groups/<group>/part-001.jsonl`. ChatGPT dùng GitHub connector đọc/tìm kiếm file từ repository Private.
6. Chỉ khi đã xác nhận không lộ dữ liệu, mới bật schedule đồng bộ 4 giờ/lần.

## Nguồn canonical và giới hạn bao phủ
- Script active: `scripts/sync_r2_ai_index_private_github.py` (workflow chạy manual). Script sidecar đời đầu được giữ để tham chiếu, không còn là entrypoint đồng bộ.
- Manifest source: R2 `internal/ai-metadata-index/v1/current.json` -> SQLite FTS5 SHA256 verified; full source classes `nature` + `music`, từ chối nếu thiếu một nhóm.
- WS2 overlay: R2 `internal/ws2-sleep-relax-enrichment/v1/source-<index_sha_prefix>/` gồm checkpoint và từng lô 500; chỉ role hint lexical, không coi là đã nghe kiểm định.
- WS3 discovery: các ứng viên khám phá mới **chưa** có trong WS1 canonical sẽ chưa xuất hiện cho đến khi WS1 index refresh; không cộng trùng và không tự tuyên bố toàn bộ metadata nghiên cứu đã được đồng bộ.
- QA an toàn đọc thực từ R2 có thể chạy mà không xuất dữ liệu; chỉ xuất số liệu tổng hợp vào log.

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
- Script đã qua kiểm thử mock/QA nguồn R2 theo run kiểm định; chưa có snapshot private GitHub cho đến khi tạo repo Private và thêm token. Đừng nhầm kiểm tra read-only với kết nối GPT đã sẵn sàng.

## Kích hoạt từ kết nối GitHub của ChatGPT
- Marker `ops/metadata_sync_request.json` không chứa dữ liệu riêng tư, ban đầu ở trạng thái `not_requested`.
- Commit lên main với tiền tố chính xác `chore(metadata): sync-request` và chỉ sửa marker sẽ chạy workflow theo nhánh push.
- Workflow kiểm tra private-target và PAT bắt buộc trước khi đọc/upload R2; nếu không, từ chối an toàn.
- Không kích hoạt tự động WS2/WS3/WS4, không tạo lịch song song; schedule đồng bộ riêng chỉ bật sau nghiệm thu thành công.
