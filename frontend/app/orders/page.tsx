"use client";

import { useState } from "react";
import { callTool } from "@/lib/api/client";

export default function OrdersPage() {
  const [orderId, setOrderId] = useState("ORD-10001");
  const [userId, setUserId] = useState("u_1001");
  const [result, setResult] = useState<unknown>();
  const [loading, setLoading] = useState(false);

  async function queryOrder() {
    setLoading(true);
    try {
      setResult(await callTool("order_query", { order_id: orderId }));
    } finally {
      setLoading(false);
    }
  }

  async function queryUserOrders() {
    setLoading(true);
    try {
      setResult(await callTool("order_list_by_user", { user_id: userId }));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <header className="pageHeader">
        <h1>订单查询</h1>
        <p>通过 MCP 工具读取 PostgreSQL 中的订单种子数据。</p>
      </header>

      <div className="grid gridTwo">
        <section className="card">
          <div className="cardHeader"><h2>查询条件</h2></div>
          <div className="cardBody stack">
            <label className="stack">
              订单号
              <input className="input" value={orderId} onChange={(event) => setOrderId(event.target.value)} />
            </label>
            <button className="button" disabled={loading} onClick={queryOrder}>查询订单详情</button>
            <label className="stack">
              用户 ID
              <input className="input" value={userId} onChange={(event) => setUserId(event.target.value)} />
            </label>
            <button className="button secondary" disabled={loading} onClick={queryUserOrders}>查询用户订单</button>
          </div>
        </section>

        <section className="card">
          <div className="cardHeader"><h2>返回结果</h2></div>
          <div className="cardBody">
            {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : <p style={{ color: "var(--muted)" }}>暂无查询结果。</p>}
          </div>
        </section>
      </div>
    </div>
  );
}