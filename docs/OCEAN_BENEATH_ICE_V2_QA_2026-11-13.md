# THE OCEAN BENEATH THE ICE — V2 sửa lỗi và nguồn mở rộng (13/11/2026)

## Dữ kiện được xác nhận

- Ảnh người dùng ở Cốc Cốc/Chromium cho thấy V1: `8/9` nguồn tải, `1` EncodingError, `5` lớp rất nhỏ.
- Lỗi giải mã: NOAA Iceberg harmonic tremor `b621edf7701897ae4d1c4242ee78ea028e82f8cd79d42063bfc1e4bffe3dedfb.wav` (khoảng 271KB). Thông tin NOAA chính thức xác nhận đây là bản thu băng trôi đã tăng tốc 3x. Bỏ hoàn toàn nguồn này khỏi V2; không thay bằng ID giả.
- 8 nguồn V2 khác xuất hiện trong 8/9 nguồn đã tải thành công trên V1; V2 chưa được kiểm tra browser lần thứ hai sau deploy, cũng chưa thể khẳng định chất lượng nghe hoàn chỉnh.
- 10 đoạn timeline, 8 nguồn, 600 giây, `gain >= 0.1`; đây là giải pháp cho cảnh báo cài đặt gain nhỏ, **không thay thế đo LUFS**.
- Master = 0.78, lớp nền 0.34; cá voi nổi hơn; âm băng trầm được lọc thấp để tránh chói. Những con số là điểm khởi đầu cho QA nghe, không phải cam kết mức âm theo dB.

## Tìm kiếm ngoài kho đồng thời (chưa nhập R2)

1. North Slope Borough / NOAA / UW: tiếng cá voi đầu cong Bắc Cực (MP3) + băng biển thật (MP3) `https://www.north-slope.org/departments/wildlife-management/studies-research-projects/oceanography-sea-ice/`. Rất đúng bối cảnh nhưng trang chưa cung cấp giấy phép tái sử dụng thương mại tường minh; tạm giữ ở trạng thái ứng viên, chưa nhập.
2. Wikimedia Commons `https://commons.wikimedia.org/wiki/File:Humpbackwhale2.ogg`, clip cá voi lưng gù 38 giây CC0. Tên loài khác bối cảnh mục tiêu, clip ngắn, không thay trong V2.
3. Freesound `https://freesound.org/people/notsawry/sounds/841320/`, 1 phút 29 giây hydrophone dưới băng hồ Ontario, CC0. Nguồn thực tế khác biển Bắc Cực, tải gốc đòi đăng nhập, chưa nhập.
4. WhaleSonic `https://whalesonic.stream/`: dự án tiếng cá voi Bắc Na Uy, CC BY 4.0; cần truy xuất file dữ liệu, nguồn tác giả, nghĩa vụ ghi credit; chưa nhập.

**Lý do không ép nhập:** yêu cầu người dùng là chỉ dùng R2 thật, không dùng nguồn giả; nguồn ngoài chưa qua ingest + HEAD + decode QA thì không được gắn assetRef.

## Hành động tiếp theo

- V2 trước hết sửa trải nghiệm dựa trên 8 nguồn đã tải được trong ảnh.
- Cần chạy QA online `8/8` và nghe kiểm định; nếu thất bại ghi rõ nguồn và thay / transcode bằng asset mới có SHA thực.
- Với V3 có thể thu thập băng biển Arctic đúng vùng nếu xác minh được quyền sử dụng + download, transcode browser-safe, ghi hash R2 và tối ưu từng lớp theo LUFS.
