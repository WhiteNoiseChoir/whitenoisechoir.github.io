# WhiteNoiseChoir — Audit định danh & Metadata V2 (2026-11-13)

## Phạm vi và bằng chứng
- Production `main` không bị thay đổi. Đây là nhánh kiểm toán, **không phải migration**.
- GitHub Actions run [43344568755](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43344568755), job 131620662009: `inventory=21698`, `browser_formats=21698`, `indexed=21674` lúc 2026-11-13 01:27:25 UTC. Chênh lệch 24 (0,1106%). Không có artifact danh sách nguồn bị loại.
- Đọc mã `scripts/build_studio_asset_catalog.py`: chỉ nhận file có sidecar khớp SHA-256, license thuộc whitelist, HTTPS source, attribution và license URL với CC-BY, duration dương hữu hạn, size khớp, title không rỗng. 24 file **chưa thể phân loại nguyên nhân riêng lẻ** vì không có quyền đọc inventory/sidecar R2 qua connector hiện tại; cần chạy công cụ read-only có R2 credentials trong môi trường bảo mật. Không xuất URL riêng tư/credentials ra log.
- Kiểm toán trực tiếp `studio-engine.js` + `studio-catalog.js`: 15 + 71 = **86 slot**, không có trường `id` tường minh; 37 slot có key chứa SHA-256, 45 slot có key không phải SHA-256, **4 slot chỉ có URL ngoài** (slot 8, 14, 55, 58); 82 key lưu trữ duy nhất. Đừng đồng nhất slot Studio với file R2 duy nhất.

## Chiến lược định danh tương thích ngược
1. R2 content-addressed: `r2-<sha256>`, với SHA-256 được xác thực từ nội dung nếu cần, không chỉ tin tên file.
2. Legacy có key không phải digest: `legacy-key-<sha256(UTF8 storage_key)>`. URL-only: `legacy-url-<sha256(UTF8 canonical URL)>`; đây là **mã tham chiếu**, không được tuyên bố là SHA của nội dung âm thanh. Giữ mapping slot cũ 0..85 cố định và alias URL/key, không sắp xếp lại catalog.
3. Khi đã xác thực byte SHA-256, có thể thêm content ID và bảng alias old->new; **không thay thế ID trong JSON cũ**. Mọi track JSON cũ dùng `asset` số vẫn đọc nguyên trạng; JSON mới có thể thêm `assetRef` nhưng phải QA resolver trước khi đưa vào Studio.
4. Script `scripts/audit_legacy_asset_ids.py` là **read-only** và xuất mapping để duyệt. Không cập nhật Studio engine, UI, video, R2, catalog live.

## Schema AI Metadata V2 — đề xuất (chưa migrate)
Một bản ghi per unique audio object, các giá trị chưa đo phải là `null`, không suy diễn thành dữ liệu xác thực:
- `schema_version:2`, `asset_id`, `content_sha256` (nullable cho URL-only), `storage_key`, `legacy_slots`, `aliases`.
- `source:{provider,source_url,creator,license,license_url,evidence_url,verified_at}`.
- `technical:{duration_seconds,codec,sample_rate_hz,channels,file_bytes,integrated_lufs,true_peak_dbtp}`.
- `semantic:{group,entity,tags,sound_role,environment,near_far,texture,mood,intensity,loop_capability}`.
- `musical:{instrument,bpm,time_signature,key,chords,musical_role}` (nullable, chỉ đo hoặc xác minh).
- Mỗi trường suy luận phải có `evidence:{method,model_or_tool,confidence,measured_at,review_status}`; phân biệt `verified`, `measured`, `inferred`, `unknown`.
- `lifecycle:discovered|stored|indexed|enriched|mix_ready|quarantined`. `mix_ready` đòi hỏi nguồn có quyền sử dụng và kỹ thuật phù hợp; `indexed` không có nghĩa AI đã nghe hiểu.

## Kế hoạch kiểm thử và QA trước khi áp dụng
1. Chạy `python scripts/audit_legacy_asset_ids.py` trên nhánh này; kiểm tra 86 slot, collision, URL-only, mapping bất biến.
2. Viết read-only exclusion report từ R2 ngay trong GitHub Actions dùng secrets hiện có: tổng file, mã SHA của file chưa index, lý do loại theo từng tiêu chí (có thể nhiều lý do/file). Lưu artifact **riêng tư**, không ghi dữ liệu nhạy cảm vào log; không upload/ghi R2.
3. Tạo JSON Schema V2 + validator + fixtures và chạy unit tests; pipeline mới: fast intake kiểm tra quyền/SHA/dedup/kỹ thuật/sidecar, semantic enrichment bất đồng bộ với confidence/evidence. Giữ các dữ liệu unknown là null.
4. Thử import JSON cũ và mới trên bản staging, xác minh 45 presets, loop/audio/video render, rồi mới xin duyệt migration. Không merge/deploy nếu chưa có QA.

## Hạn chế
- Chưa có dữ liệu 24 SHA bị loại; chưa thể xác minh root cause cụ thể hay sửa 24 file.
- Không có bằng chứng chạy thử trong browser production; không sửa source live.
- Mọi phép định danh theo storage key hoặc URL chỉ là mã tham chiếu ổn định khi chuỗi tham chiếu không đổi, không phải content hash.
