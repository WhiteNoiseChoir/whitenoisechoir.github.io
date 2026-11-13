# WS3 chained music metadata → private audio staging

## Ý định

Chuyển metadata nghiên cứu trong R2 (ví dụ baseline ít nhất 1.962) thành **file audio gốc có kiểm tra kỹ thuật**, theo lô có checkpoint. Các con số sau đây phải báo riêng: metadata ứng viên, URL/revision được recheck, file đã download, file staged R2, file SHA trùng, file đã có quyền phát hành, file Studio-ready.

**Không suy luận 1.962 ứng viên = 1.962 file có thể tải hoặc phát hành**, không coi 8 file nhạc cụ đã lưu từ workflow riêng là toàn bộ tiến độ của pipeline metadata.

## Luồng hiện có

- `scripts/bulk_stage_music_candidates.py` đọc candidate-index private `internal/music-candidates/v1/`, các receipts đã xử lý, và danh sách SHA trong existing asset library.
- Chỉ xử lý **Wikimedia Commons CC0 / CC-BY 3.0/4.0** trong vòng này. Các adapter Internet Archive/Openverse còn phải nghiên cứu riêng. Các provider đó không bị đánh dấu đã hoàn tất.
- Dùng `prepare_music_rights_review.revalidate_source` gọi Commons API kiểm tra lại license claim, URL original, revision và size. Source claim vẫn không thay cho quyền underlying composition/performance.
- Đã xác thực file: tải original từ host allowlist, size cap 32 MiB, SHA-256, ffprobe và ffmpeg full decode, so với SHA của asset hiện có.
- **Không** ghi vào catalog/Studio, **không** xuất bản. Ghi private tại `internal/music-audio-staging/v1/sha256/` và sidecar `provenance/`, trạng thái **STORED_R2_RIGHTS_QA_PENDING**. File có thể sử dụng để nghe/phối **thử nội bộ** sau khi truy cập R2 đúng quyền.
- Mỗi candidate đã xử lý thành công hoặc xác nhận SHA trùng có receipt create-only trong `internal/music-audio-staging/v1/receipts/`. Các lỗi mạng/quyền không tạo receipt hoàn thành giả; lần sau có thể retry sau khi sửa nguyên nhân.
- Mỗi batch có checkpoint R2 `internal/music-audio-staging/v1/runs/` và log `WS3_CHAIN_BATCH`; kết thúc log `WS3_CHAIN_FINAL`.
- `music_metadata_audio_chain.yml` xử lý tối đa **6 batch x 8 file = 48 file/run**, <=250 MiB tải, <=72 source API rechecks, <=130 phút, 5 lỗi download trước khi dừng. Serial concurrency cùng WS3 PR #89, không đua ghi.
- Unit tests offline bắt buộc thành công trước khi chạy intake.

## Tiếp tục tự động

- Trong một Actions run, ngay sau khi đủ 8 file xử lý, script **tự chuyển sang batch tiếp theo**, lưu checkpoint. Không cần người thao tác mỗi batch.
- Giữa hai Actions run, lịch tự động **WS3 — Nhập audio R2 liên tục** (mỗi giờ) kiểm tra workflow mới nhất trên branch `feature/music-audio-continuous-stage-20261113`. Nếu run đang pending/in_progress, **không** khởi chạy trùng. Nếu run đã hoàn tất thành công và còn Commons candidates có thể xử lý, cập nhật `config/music_audio_staging_batch.json` trên feature branch với **predecessor run ID, confirmed conclusion và sequence tăng đúng một**, từ đó trigger push lô tiếp theo. Không viết commit chỉ để duy trì vòng lặp; khi không có progress/candidates mới cần ghi rõ BLOCKED và dừng restart vô ích.
- Feature workflow không tự workflow_dispatch khi file chưa hiện diện trên GitHub default branch. Lịch tối thiểu một giờ nên có thể có khoảng chờ giữa các runs; không hứa chạy vô hạn tức thời. Không thay đổi default branch để lách.
- Khi số Commons candidates hiện có được xử lý hết, thử mở rộng adapter mới sau khi xây gate HTTPS/host/rights đúng cho nguồn đó; không tự nhận đã hết toàn bộ backlog nếu Openverse/Internet Archive còn tồn tại.

## Quyền sử dụng

File staged được lưu riêng để nghiên cứu/nghe thử/phối thử nội bộ khi nguồn claim phù hợp, nhưng **không được coi là asset đủ quyền đưa lên YouTube hay bán thương mại** khi chưa xác minh tác giả/người sở hữu quyền recording/composition và điều kiện ghi công. Nếu thiếu bằng chứng, vẫn giữ `rights_review_pending`. Không sử dụng pipeline này để tải nguồn không có license phù hợp hoặc vượt cơ chế truy cập.

## Nghiệm thu

Từ logs cần xác minh số `new_private_staged_audio_files_this_run`, `duplicate_audio_sha256_this_run`, `downloaded_bytes_this_run`, `states`, R2 receipt count; `studio_ready_by_this_run=0` và `public_commercial_release_rights_cleared_by_this_run=0`. Không trừ toàn bộ metadata (bao gồm provider unsupported) từ số downloads để gọi hiệu quả quét.
