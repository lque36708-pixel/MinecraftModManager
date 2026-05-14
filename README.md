# 3m — Minecraft Mod Manager

Tải mod từ Modrinth nhanh chóng qua CLI. Không cần đăng nhập, không cần thư viện ngoài — chỉ cần Python 3.

## Cài đặt

```bash
chmod +x 3m.sh 3m.py

# Tùy chọn: thêm vào PATH để gõ '3m' ở bất cứ đâu
sudo ln -s $(pwd)/3m.sh /usr/local/bin/3m
```

## Cách dùng

```
3m set-profile 1.21.1 fabric        # Đặt profile MC version + loader
3m search sodium                    # Tìm mod, kết quả có số thứ tự
3m get -i 1                         # Tải mod theo index
3m get sodium                       # Tải ngay kết quả đầu tiên
3m get sodium, lithium, iris        # Tải nhiều mod cùng lúc
3m show -i 1                        # Xem chi tiết mod theo index
3m show sodium                      # Xem chi tiết mod theo tên
3m profile                          # Xem profile hiện tại
```

## Lưu ý

- Mod được tải vào **thư mục hiện tại** khi chạy lệnh `get`.
- Profile lưu tại `~/.config/3m/profile.json`.
- Cache kết quả search cuối tại `~/.config/3m/last_search.json`.
- Loaders hỗ trợ: `fabric`, `forge`, `quilt`, `neoforge`.
