import { Button, Input, Card } from '../../components';

export default function ComponentsDemo() {
  return (
    <div>
      <h1>Component demo</h1>

      <h2>Button</h2>
      <div style={{ display: 'flex', gap: 12 }}>
        <Button>Nút chính</Button>
        <Button variant="secondary">Nút phụ</Button>
        <Button disabled>Bị khóa</Button>
      </div>

      <h2>Input</h2>
      <Input label="Họ và tên" placeholder="Nhập họ và tên" />
      <Input label="Email" error="Email chưa đúng" />

      <h2>Card</h2>
      <Card>
        <h3>Tiêu đề thẻ</h3>
        <p>Nội dung bên trong.</p>
      </Card>
    </div>
  );
}
