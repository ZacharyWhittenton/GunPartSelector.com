export type OrderStatus = 'open' | 'paid' | 'expired' | 'cancelled';

export interface OrderItemSummary {
  itemName: string;
  unitPriceCents: number;
  quantity: number;
  lineTotalCents: number;
}

export interface OrderSummary {
  id: string;
  status: OrderStatus;
  totalCents: number;
  createdAt: string;
  items: OrderItemSummary[];
}
