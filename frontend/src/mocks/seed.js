export const seed = {
  family: [
    { id: 'm1', name: 'Nguyễn Minh Anh', relation: 'Tôi', age: 29, goal: 'Ăn uống cân bằng', avatar: 'MA', color: '#e5eee6' },
    { id: 'm2', name: 'Nguyễn Văn Bình', relation: 'Bố', age: 58, goal: 'Theo dõi bữa ăn', avatar: 'VB', color: '#f4e9d8' },
    { id: 'm3', name: 'Trần Thu Hà', relation: 'Mẹ', age: 55, goal: 'Ăn đa dạng', avatar: 'TH', color: '#f3e4e0' },
  ],
  diary: [
    { id: 'd1', date: '2026-11-20', meal: 'Bữa sáng', name: 'Yến mạch, chuối và sữa chua', memberId: 'm1', note: 'Bữa ăn minh họa', score: 'Cân bằng', icon: 'bowl' },
    { id: 'd2', date: '2026-11-20', meal: 'Bữa trưa', name: 'Cơm gạo lứt, cá và rau', memberId: 'm1', note: 'Bữa ăn minh họa', score: 'Đa dạng', icon: 'plate' },
    { id: 'd3', date: '2026-11-19', meal: 'Bữa tối', name: 'Canh rau và đậu phụ', memberId: 'm2', note: 'Bữa ăn minh họa', score: 'Đã ghi nhận', icon: 'leaf' },
  ],
  menu: [
    { id: 'breakfast', label: 'Bữa sáng', icon: 'sun', dish: 'Bánh mì trứng và trái cây', detail: 'Khởi đầu ngày mới nhẹ nhàng', locked: false },
    { id: 'lunch', label: 'Bữa trưa', icon: 'plate', dish: 'Cơm gạo lứt, cá hấp và rau', detail: 'Kết hợp các nhóm thực phẩm', locked: false },
    { id: 'dinner', label: 'Bữa tối', icon: 'moon', dish: 'Bún gà và rau xanh', detail: 'Một lựa chọn ấm áp cho cả nhà', locked: false },
  ],
  alternatives: [
    { name: 'Phở gà và rau thơm', detail: 'Lựa chọn minh họa' },
    { name: 'Salad đậu phụ và ngũ cốc', detail: 'Lựa chọn minh họa' },
    { name: 'Cơm, thịt nạc và rau luộc', detail: 'Lựa chọn minh họa' },
  ],
};
