"use client";

import { FormEvent, useState } from "react";
import { callTool } from "@/lib/api/client";

export default function TicketsPage() {
  const [userId, setUserId] = useState("u_1001");
  const [orderId, setOrderId] = useState("ORD-10001");
  const [summary, setSummary] = useState("用户要求人工跟进物流问题");
  const [details, setDetails] = useState("用户反馈物流长时间未更新，希望人工客服协助处理。");
  const [result, setResult] = useState<unknown>();
  const [afterSaleResult, setAfterSaleResult] = useState<unknown>();

  async function createTicket(event: FormEvent) {
    event.preventDefault();
    setResult(await callTool("ticket_create", {
      user_id: userId,
      order_id: orderId,
      type: "logistics",
      priority: "medium",
      summary,
      details,
    }));
  }

  async function createAfterSale() {
    setAfterSaleResult(await callTool("after_sale_create", {
      user_id: userId,
      order_id: orderId,
      type: "return_refund",
      reason: "用户申请退货退款",
    }));
  }

  return (
    <div>
      <header className="pageHeader">
        <h1>工单 / 售后</h1>
        <p>第一版通过 MCP 工具创建工单和售后申请，不做复杂后台流转。</p>
      </header>

      <div className="grid gridTwo">
        <section className="card">
          <div className="cardHeader"><h2>创建人工工单</h2></div>
          <form className="cardBody stack" onSubmit={createTicket}>
            <input className="input" value={userId} onChange={(event) => setUserId(event.target.value)} />
            <input className="input" value={orderId} onChange={(event) => setOrderId(event.target.value)} />
            <input className="input" value={summary} onChange={(event) => setSummary(event.target.value)} />
            <textarea className="textarea" value={details} onChange={(event) => setDetails(event.target.value)} />
            <div className="formRow">
              <button className="button" type="submit">创建工单</button>
              <button className="button secondary" type="button" onClick={createAfterSale}>创建售后</button>
            </div>
          </form>
        </section>

        <section className="card">
          <div className="cardHeader"><h2>处理结果</h2></div>
          <div className="cardBody stack">
            <div>
              <strong>工单结果</strong>
              {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : <p style={{ color: "var(--muted)" }}>暂无工单结果。</p>}
            </div>
            <div>
              <strong>售后结果</strong>
              {afterSaleResult ? <pre>{JSON.stringify(afterSaleResult, null, 2)}</pre> : <p style={{ color: "var(--muted)" }}>暂无售后结果。</p>}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}