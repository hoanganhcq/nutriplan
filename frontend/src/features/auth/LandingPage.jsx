import { Link } from 'react-router-dom';
import { DemoLabel } from '../../components/Feedback.jsx';
import Icon from '../../components/Icon.jsx';
import FoodArt from '../../components/FoodArt.jsx';

export default function LandingPage() {
  return <div className="landing">
    <header className="landing__header"><Link className="brand" to="/welcome"><span className="brand__mark"><Icon name="logo" size={22} /></span> NutriPlan</Link><Link className="button button--outline" to="/dang-nhap">Đăng nhập</Link></header>
    <main className="landing__main">
      <div className="landing__copy"><DemoLabel /><h1>Chăm sóc bữa ăn,<br /><em>gắn kết cả nhà.</em></h1><p>Ghi lại bữa ăn, xem gợi ý thực đơn và theo dõi thói quen ăn uống của từng thành viên trong một không gian dễ dùng.</p><div className="landing__actions"><Link className="button button--primary" to="/dang-nhap">Bắt đầu trải nghiệm <span aria-hidden="true">↗</span></Link><a className="button button--quiet" href="#how">Khám phá cách hoạt động ↓</a></div><small>Bản demo sử dụng dữ liệu minh họa, không phải tư vấn y tế.</small></div>
      <div className="landing__art"><div className="art-circle art-circle--one"/><div className="art-circle art-circle--two"/><div className="art-card art-card--top"><Icon name="leaf" size={30} /> <span>Bữa ăn hôm nay<br /><b>Đầy màu sắc</b></span></div><FoodArt className="art-plate" /><div className="art-card art-card--bottom"><Icon name="sparkles" size={19} /> Mỗi bữa ăn là một khởi đầu tốt</div></div>
    </main>
    <section id="how" className="landing__features"><div><span>01 / GHI NHẬN</span><h2>Chụp và xác nhận</h2><p>Tải ảnh bữa ăn, chỉnh tên món và khẩu phần trước khi lưu.</p></div><div><span>02 / THEO DÕI</span><h2>Nhật ký gia đình</h2><p>Tra cứu các bữa ăn đã ghi lại theo ngày và thành viên.</p></div><div><span>03 / LÊN KẾ HOẠCH</span><h2>Thực đơn linh hoạt</h2><p>Đổi món, khóa món yêu thích và tạo gợi ý mới.</p></div></section>
  </div>;
}
