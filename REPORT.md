# REPORT — Lab Day 12

> Điền **bằng lời và số liệu của chính bạn** (lấy từ màn hình và từ `evidence/*.json`). Mỗi câu 4–8 dòng là đủ. Số không có trong bằng chứng của bạn sẽ bị trừ điểm. Báo cáo công khai trên GitHub; giảng viên đối chiếu với `evidence/` và với bài của các bạn khác.

| | |
|---|---|
| Họ và tên | Đặng Quốc Hiệp |
| MSSV (đúng bằng `--student-id` bạn đã chạy) | 2A202602755 |
| GitHub | QuocHiep123 |
| Seed chia dữ liệu / seed mô hình (xem `evidence/closedloop.json`, mục `student`) | 4 / 5834 |
| Số seed huấn luyện bạn dùng (`--seeds`) | 3 |

## Kết quả cuối

Điền từ `evidence/closedloop.json`, `openloop.json`, `gate.json` (cho mỗi mô hình học, lấy **dải qua các seed**).

| Bộ điều khiển | L2 vòng hở (m) | Va chạm vòng kín trên log (%) | Quyết định cổng |
|---|---|---|---|
| constant-velocity | 1.251 | 19.5% | BLOCK |
| IDM | 1.514 | 0.1% | (baseline) |
| EgoMLP | 0.755 .. 0.761 (TB: 0.759) | 17.8% .. 40.3% (TB: 26.0%) | BLOCK |
| PercMLP | 0.619 .. 0.624 (TB: 0.621) | 0.3% .. 0.7% (TB: 0.5%) | BLOCK |
| PercMLP+ (sau khi sửa) | 0.801 .. 0.819 (TB: 0.811) | 0.1% .. 0.2% (TB: 0.17%) | RELEASE |

## Câu 1 · Dữ liệu
Bước 0 bạn phát hiện những vấn đề gì ở dữ liệu? Vì sao không dùng cột `Acc_LV`, và bạn thay bằng gì? Bao nhiêu quỹ đạo bị loại vì trùng, và vì sao chia theo quỹ đạo?

Ở Bước 0, quá trình kiểm toán dữ liệu (data audit) phát hiện ba vấn đề then chốt:
1. Cột gia tốc xe dẫn `Acc_LV` hoàn toàn không khớp với đạo hàm vận tốc: hệ số tương quan giữa `Acc_LV` và đạo hàm `d(Speed_LV)/dt` chỉ đạt 0.0453 (thực tế xấp xỉ bằng 0), trong khi ở xe theo sau (`Acc_FAV`), tương quan lên tới 0.9291. Nguyên nhân do cảm biến đo thô của xe dẫn bị trễ pha và nhiễu nặng, không tin cậy để làm nhãn khai thác ca phanh. Do đó, hệ thống đã thay thế bằng gia tốc làm mượt `a_lead` được đạo hàm trực tiếp từ chuỗi vận tốc `Speed_LV` qua bộ lọc đạo hàm làm mượt.
2. Bộ dữ liệu thô gồm 9993 quỹ đạo có tới 383 quỹ đạo trùng lặp tuyệt đối (`exact_duplicates_removed = 383`) xuất hiện ở các ID cách xa nhau, khiến tập dữ liệu sạch còn lại 9610 quỹ đạo (`trajectories_clean = 9610`). Nếu không loại trùng, hiện tượng rò rỉ dữ liệu (data leakage) giữa tập huấn luyện và kiểm thử sẽ xảy ra nghiêm trọng.
3. Ta phải chia train/test theo từng quỹ đạo (trajectory) với 167260 cửa sổ huấn luyện và 71873 cửa sổ kiểm thử, thay vì chia ngẫu nhiên theo khung hình (frame). Mỗi quỹ đạo kéo dài từ 70 đến 109 bước thời gian (trung vị 106.0 bước, dt = 0.1s); nếu chia theo frame, các khung hình kế cận có độ tương quan thời gian cực cao sẽ bị phân tán vào cả hai tập, khiến việc đánh giá năng lực khái quát hóa trên chuỗi thời gian thực tế trở nên vô nghĩa.

## Câu 2 · Phát lại
Bản refactor float32 khác bit ở bao nhiêu đoạn, vượt dung sai ở bao nhiêu? Thay đổi AEB làm lệch bao nhiêu đoạn, và vì sao lệch ở đúng những khung đó (mở một đoạn ra xem)? Phát theo thời gian thật làm lộ ra điều gì mà phát nhanh nhất che đi?

Bản refactor tối ưu hóa float32 và thay đổi thứ tự toán tử cho thấy toàn bộ 600/600 đoạn (`not_bit_identical = 600`) đều không trùng khớp từng bit với bản gốc float64 do đặc tính không kết hợp của số thực: `(0.1 + 0.2) + 0.3 = 0.6000000000000001` khác `0.1 + (0.2 + 0.3) = 0.6`. Tuy nhiên, 0/600 đoạn vượt dung sai (`differ_beyond_tol = 0`) với sai số tuyệt đối lớn nhất chỉ đạt `max_abs_diff = 1.98e-5 m/s²`, nhỏ hơn rất nhiều so với ngưỡng `atol = 1e-3` và `rtol = 1e-3`. Điều này chứng minh cần so sánh có dung sai kỹ thuật để tránh các báo động lỗi giả khi tối ưu mã nguồn.

Khi bổ sung quy tắc phanh khẩn cấp AEB (`aeb_ttc = 1.5s`), có đúng 13/600 đoạn xuất hiện sai lệch vượt dung sai (các đoạn [61, 73, 137, 190, 234,...]). Kiểm tra sâu đoạn 61 cho thấy sai lệch diễn ra ở 4 khung hình [98, 99, 100, 101]: tại khung 98, khoảng cách rút ngắn còn `gap = 4.3033 m`, tốc độ tiến gần là `closing = 2.92 m/s`, dẫn đến `TTC = 1.47s < 1.5s`. Lệnh cũ của IDM chỉ phanh `-5.44 m/s²`, nhưng AEB đã can thiệp ép phanh khẩn cấp kịch trần `-6.00 m/s²`.

Chế độ phát nhanh nhất ("fastest") chỉ đơn thuần đẩy thông điệp tiếp theo ngay khi xử lý xong mà không có khái niệm trễ hạn, dẫn đến 0 khung trễ và 0 khung rớt (`late = 0`, `dropped = 0`). Ngược lại, chế độ thời gian thực ("realtime") mô phỏng chu kỳ 100 ms và chi phí tính toán thực tế đã làm lộ ra 588 khung bị trễ (`late = 588`) và 579 khung bị rớt (`dropped = 579`) trong tổng số 60198 khung, làm thay đổi lệnh điều khiển ở 376/600 đoạn với độ lệch cực đại `max_abs_diff = 5.50 m/s²`.

## Câu 3 · Kịch bản
Lưới của bạn (tốc độ cruise, giới hạn khoảng cách, số ô): bao nhiêu % ô **không ai tránh được**? Độ trễ phản ứng 0 → 0,6 s làm vùng đâm của IDM tăng bao nhiêu? Log có phủ vùng khó không? (dẫn giới hạn phanh mạnh nhất của người lái trong log, và phần lưới đòi hỏi hơn thế)

Lưới kịch bản cắt đầu (cut-in grid) được tạo với tốc độ hành trình `v_ego = 10.0 m/s`, dải khoảng cách từ `2.76 m` đến `59.31 m` (60 điểm) và tốc độ tiến gần từ `0.0 m/s` đến `10.0 m/s` (45 điểm), gồm tổng cộng `2700 ô`.
1. Vùng vật lý bất khả kháng: Khi độ trễ phản ứng `t_react = 0.0s`, có `0.96%` số ô (khoảng 26 ô) là tình huống bất khả thi mà không bộ điều khiển nào tránh được kể cả khi phanh kịch sàn ở `b_max = 9.0 m/s²`. Khi độ trễ phản ứng tăng lên `t_react = 0.6s`, vùng bất khả kháng mở rộng lên `5.15%` số ô (138 ô) - tăng hơn 5.3 lần.
2. Với bộ điều khiển IDM, vùng va chạm tăng đúng bằng phần mở rộng bất khả kháng của vật lý: từ `0.96%` (tại trễ 0.0s) lên `5.15%` (tại trễ 0.6s), diện tích va chạm do lỗi điều khiển (`attributable_area`) của IDM hoàn toàn bằng 0.0% ở cả hai độ trễ (đường đâm của IDM trùng khít 100% với biên bất khả kháng).
3. Về độ bao phủ của dữ liệu thực tế: Người lái trong log phanh mạnh nhất ở phân vị 99.9% chỉ đạt `human_brake_limit_p99.9 = 3.62 m/s²` (trong khi cơ cấu phanh xe chịu được tới 9.0 m/s²). Có tới `5.22%` số ô trong lưới (141 ô) đòi hỏi lực phanh giảm tốc vượt quá mức phanh tối đa từng thấy của con người. Khai thác log thực tế trích xuất được 614 sự kiện xe dẫn phanh (`mined_events = 614`, chiếm 6.39% quỹ đạo) với gia tốc đỉnh phân vị p50 là `-2.53 m/s²` và p99 là `-4.21 m/s²`. Các sự kiện này chỉ phân bố ở vùng khoảng cách an toàn và vận tốc tiến gần nhỏ, hoàn toàn không phủ vùng cắt đầu cự ly hẹp với vận tốc cao trên lưới.

## Câu 4 · Vòng hở và vòng kín
Dán bảng L2 và tỷ lệ va chạm của bốn bộ điều khiển (kèm hạng ở mỗi cách chấm). Cặp nào đổi thứ tự? Vì sao IDM có L2 như vậy mà vẫn lái tốt? Vì sao EgoMLP có L2 tốt hơn constant-velocity mà vẫn đâm?

Bảng so sánh L2 vòng hở và tỷ lệ va chạm vòng kín trên 2883 quỹ đạo kiểm thử giữ lại (185 quỹ đạo có xe dẫn phanh):
- PercMLP: L2 vòng hở = 0.621 m (Hạng 1) | Va chạm vòng kín = 0.5% (Hạng 2).
- EgoMLP: L2 vòng hở = 0.759 m (Hạng 2) | Va chạm vòng kín = 26.0% (Hạng 4).
- constant-velocity: L2 vòng hở = 1.251 m (Hạng 3) | Va chạm vòng kín = 19.5% (Hạng 3).
- IDM: L2 vòng hở = 1.514 m (Hạng 4) | Va chạm vòng kín = 0.1% (Hạng 1).

Có 4 cặp bộ điều khiển bị đảo ngược thứ hạng (ranking inversion): `('const-vel', 'IDM')`, `('const-vel', 'EgoMLP')`, `('IDM', 'EgoMLP')`, và `('IDM', 'PercMLP')`.

Giải thích cơ chế vật lý:
1. IDM có L2 vòng hở tệ nhất (1.514 m) vì nó là luật điều khiển tối ưu hóa tính ổn định và khoảng cách an toàn, không được thiết kế để bắt chước từng dao động nhỏ của tài xế con người trong log. Tuy nhiên, trong vòng kín, IDM hình thành vòng phản hồi âm kín (feedback loop): khi khoảng cách thu hẹp, lệnh phanh tăng mạnh tương ứng, giúp xe chỉ va chạm 0.1% (chỉ 2/2883 ca) và trên lát cắt phanh chỉ va chạm 1.1% (2/185 ca).
2. EgoMLP đạt L2 vòng hở tốt hơn constant-velocity (0.759 m so với 1.251 m) nhưng khi vào vòng kín lại đâm nhiều hơn hẳn (26.0% so với 19.5%, và trên lát cắt phanh lên tới 71.9% so với 50.8%). Nguyên nhân cốt lõi là EgoMLP hoàn toàn không có thông tin nhận thức về xe dẫn (không thấy khoảng cách gap và vận tốc xe dẫn v_lead), nó chỉ dự đoán dựa trên lịch sử tốc độ bản thân. Trong vòng kín, các sai lệch tích lũy (compounding errors / covariate shift) khiến xe rơi vào các trạng thái khoảng cách nguy hiểm mà nó không hề hay biết để kích hoạt phanh, dẫn đến chuỗi va chạm thảm khốc.

## Câu 5 · Một lần chạy chưa đủ
EgoMLP dao động bao nhiêu giữa các seed? Khoảng tin cậy Wilson nói gì? Nếu bạn chỉ chạy đúng một seed thì có thể báo kết quả nào, và vì sao điều đó nguy hiểm?

Khi huấn luyện và đánh giá EgoMLP qua 5 seed ngẫu nhiên (`5834` đến `5838`), tỷ lệ va chạm dao động dữ dội từ `17.8%` (ở seed 5836, 514 va chạm) lên tới `40.3%` (ở seed 5837, 1161 va chạm) - độ chênh lệch cực lớn lên tới `22.5 điểm phần trăm` (gấp hơn 2.2 lần). Trên lát cắt xe dẫn phanh gấp, tỷ lệ va chạm biến động từ `41.6%` đến `71.9%`.

Khoảng tin cậy Wilson 95% thể hiện rõ rệt sự phân tách: ở seed tốt nhất (seed 5836), CI95 là `[16.5%, 19.3%]`, trong khi ở seed xấu nhất (seed 5837), CI95 là `[38.5%, 42.1%]`. Hai khoảng tin cậy này hoàn toàn rời nhau và không có bất kỳ điểm chồng lấn nào.

Nếu nhóm kỹ sư chỉ chạy duy nhất một seed:
- Nếu vô tình chọn trúng seed 5836, họ sẽ báo cáo tỷ lệ va chạm chỉ `17.8%` và lầm tưởng rằng mô hình hoạt động tốt hơn bộ điều khiển constant-velocity (`19.5%`).
- Nếu trúng seed 5837, kết quả lại là thảm họa `40.3%`.
Điều này cực kỳ nguy hiểm trong phát triển hệ thống an toàn tự hành, bởi nó che giấu tính bất ổn định nội tại của mạng nơ-ron trước sự ngẫu nhiên trong khởi tạo trọng số và phân phối mini-batch. Một mô hình muốn được xem xét phát hành bắt buộc phải chứng minh cận trên rủi ro ở trường hợp xấu nhất (worst-case bound qua nhiều seed) nằm trong ngưỡng an toàn cho phép.

## Câu 6 · Tác nhân phản ứng
Dán bảng "xe sau phát lại" và "xe sau phản ứng". `T` bạn hiệu chỉnh là bao nhiêu, xe sau chân thực đến mức nào so với xe không phản ứng? Vì sao IDM bị tính "va chạm giả" khi xe sau chỉ phát lại, và điều này làm đổi kết luận về bộ điều khiển ra sao?

Bảng so sánh tỷ lệ va chạm trên lưới cắt đầu (tại độ trễ phản ứng `t_react = 0.6s`) giữa hai thế giới:
- const-vel: xe sau phát lại = 73.4% (đâm sau: 0.0%) | xe sau phản ứng = 73.4% (đâm sau: 0.0%).
- IDM: xe sau phát lại = 70.1% (đâm sau: 64.9%) | xe sau phản ứng = 5.1% (đâm sau: 0.0%).
- EgoMLP: xe sau phát lại = 74.3% (đâm sau: 0.0%) | xe sau phản ứng = 74.3% (đâm sau: 0.0%).
- PercMLP: xe sau phát lại = 93.4% (đâm sau: 76.1%) | xe sau phản ứng = 17.4% (đâm sau: 0.0%).

Tham số khoảng cách thời gian `T` được hiệu chỉnh tối ưu là `T = 1.4s`, đạt khoảng cách phân phối Wasserstein-1 nhỏ nhất là `W1 = 0.349` so với phân phối bám đuôi thực tế của tài xế con người trong log (trung vị thời gian headway là `1.86s`). Mô hình này chân thực vượt trội so với một xe sau không phản ứng cố định (`W1 = 0.866`).

Bản chất "va chạm giả" (fake rear collisions): Khi xe sau chỉ phát lại tốc độ đã ghi nhận trong log mà không có mắt nhìn phía trước, nếu xe thử nghiệm (như IDM) chủ động phanh gấp để tránh xe cắt đầu phía trước, chiếc xe sau sẽ đâm thẳng vào đuôi xe thử nghiệm. Kết quả là IDM bị tính oan tới `64.9%` số vụ va chạm phía sau trên lưới. Khi chuyển sang môi trường xe sau biết phản ứng (IDM có trễ 0.6s), tỷ lệ va chạm sau của IDM giảm ngay về đúng `0.0%`, đưa tỷ lệ va chạm chung từ `70.1%` xuống còn `5.1%`. Nếu không có tác nhân phản ứng, ta sẽ rút ra kết luận phi lý rằng một bộ điều khiển biết phanh an toàn (IDM) lại nguy hiểm hơn một chiếc xe trơ lì không bao giờ phanh (constant-velocity).

## Câu 7 · Cổng phát hành và sửa
Quy tắc nào chặn PercMLP và nguyên nhân gốc là gì (dẫn số)? Bạn sửa bằng gì và vì sao nó chữa đúng nguyên nhân? Sau khi qua cổng, PercMLP+ có **tốt hơn** IDM không? Nó có nên được phát hành không, và bạn đề xuất làm gì trước khi quyết định?

Mô hình PercMLP ban đầu bị cổng kiểm định CHẶN (BLOCK) do trượt 2 quy tắc:
1. Quy tắc R4 (Scenario Grid): Diện tích va chạm có thể tránh được trên lưới cắt đầu là `12.2%` (ngưỡng quy định: baseline `0.0% + 2.0% = 2.0%`).
2. Quy tắc R6 (Reactive World): Tỷ lệ va chạm trong môi trường có xe sau phản ứng lên tới `17.4%` (ngưỡng quy định: baseline `5.1% + 2.0% = 7.1%`).
Nguyên nhân gốc rễ: Tập log giao thông thông thường hầu như không có các kịch bản xe khác chuyển làn tạt đầu ở cự ly hẹp với vận tốc tiến gần cao (độ lệch phân phối kịch bản). Đồng thời, khi tự lái trong vòng kín, các sai số tích lũy nhỏ dần đẩy xe vào vùng trạng thái lạ (covariate shift) mà mô hình không biết cách thoát ra.

Phương pháp sửa: Ta bổ sung 197060 cửa sổ từ 20000 kịch bản cắt đầu mô phỏng (`cutin_windows`) và áp dụng thuật toán DAgger qua 2 vòng (`dagger_windows`). DAgger giải quyết triệt để nguyên nhân gốc vì nó cho mô hình tự lái, ghi nhận chính các trạng thái sai lệch mà nó tự đi vào, rồi lấy nhãn dự báo 3s từ chuyên gia IDM để huấn luyện lại, trang bị cho mô hình năng lực tự phục hồi (recovery policy).
Sau khi sửa, PercMLP+ đạt chuẩn RELEASE và vượt qua cả 7 quy tắc: R4 giảm từ `12.2%` xuống `0.1%`, R6 giảm từ `17.4%` xuống `5.2%` (so với baseline 5.1%), va chạm trên log giảm còn `0.1%..0.2%`.

Đánh giá: PercMLP+ KHÔNG "tốt hơn" IDM, mà chỉ đạt tiêu chí "không kém hơn" (non-inferiority). PercMLP+ học hoàn toàn từ nhãn của IDM, do đó IDM chính là chặn trên năng lực của nó. Khi thử nghiệm ngoài dải phân phối ở vận tốc hành trình 20 m/s (chưa từng thấy lúc train <= 16 m/s), IDM va chạm 0.0% trong khi PercMLP+ vẫn va chạm 0.9%..1.9%. Do đó, chưa nên vội vàng thay thế IDM trên xe thương mại; cần thử nghiệm thêm trong môi trường mô phỏng 3D đa làn, kiểm thử ở chế độ chạy ngầm (shadow mode) trên xe thật có tài xế an toàn và đánh giá độ êm ái gia tốc (comfort/jerk).

## Câu 8 · Bài lab này không chứng minh được gì
Chọn **ít nhất ba** giới hạn quan trọng nhất đối với việc quyết định phát hành và giải thích vì sao mỗi cái làm kết luận của bạn kém chắc chắn. Điều gì cần làm tiếp để thu hẹp khoảng cách đến thế giới thật?

Ba giới hạn quan trọng nhất của bài lab đối với quyết định phát hành hệ thống tự hành thực tế:
1. Mô hình hóa động lực học 1-D thuần túy: Bài lab chỉ xét chuyển động dọc (longitudinal), giả định xe luôn đi thẳng trên một làn đường cố định. Thực tế giao thông đòi hỏi điều khiển kết hợp cả chuyển động ngang (lateral), góc đánh lái chuyển làn, độ trượt bánh (slip angle) và ma sát mặt đường thay đổi theo thời tiết (đường ướt, băng tuyết). Một mô hình an toàn trong 1-D hoàn toàn có thể mất kiểm soát khi phải vừa phanh vừa đánh lái tránh chướng ngại vật.
2. Giả định nhận thức (Perception) lý tưởng: Bài lab cung cấp trực tiếp cự ly (`gap`) và tốc độ xe dẫn (`v_lead`) dưới dạng số thực hoàn hảo (hoặc chỉ thêm nhiễu Gaussian tĩnh nhỏ ±1m, ±0.5m/s). Trong thực tế, hệ thống Perception dựa trên Camera/LiDAR/Radar gặp phải các lỗi rất nghiêm trọng như: mất dấu vật thể (false negative), nhận diện vật thể ma dẫn đến phanh gấp bất ngờ (ghost braking / false positive), và độ trễ thay đổi khó lường theo điều kiện ánh sáng hay thời tiết.
3. Tác nhân giao thông bị đơn giản hóa cao độ: Xe phía sau và xe cắt đầu được mô phỏng bằng luật IDM đồng nhất hoặc phát lại cố định, chưa phản ánh được sự phức tạp của hành vi con người (tài xế mất tập trung, tài xế gây hấn, xe máy lạng lách hoặc người đi bộ bất ngờ băng qua đường).

Hành động tiếp theo để thu hẹp khoảng cách đến thế giới thực: Chuyển sang môi trường mô phỏng 3D độ chân thực cao (như CARLA hoặc Webots) với đầy đủ động lực học xe 6 bậc tự do; tích hợp trực tiếp pipeline nhận thức từ ảnh camera/point cloud thô; và triển khai thử nghiệm hàng triệu kilomet ở chế độ chạy ngầm (shadow mode) trên đội xe thương mại trước khi chính thức cho phép thuật toán can thiệp vào cơ cấu chấp hành.
