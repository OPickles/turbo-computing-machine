import sys, os, asyncio, uuid
import streamlit as st
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.shadow_bookmaker.application.orchestrator import BrokerOrchestrator
from src.shadow_bookmaker.domain.models import CustomerTicket, TicketLeg

st.set_page_config(page_title="Shadow Broker | 生产级风控台", layout="wide")

@st.cache_resource
def get_orchestrator(): return BrokerOrchestrator()

orchestrator = get_orchestrator()

def render_decision(decision, ticket):
    st.markdown("### ⚡ 智能路由指令")
    if decision.action == "REJECT": 
        st.error(f"🔴 拒单: {decision.reason}")
    elif decision.action == "ACCEPT_B_BOOK": 
        st.info(f"🔵 吃单入库: {decision.reason}")
    elif decision.action in ["ACCEPT_PARTIAL_HEDGE", "ACCEPT_A_BOOK_HEDGE"]: 
        st.warning(f"🟡 对冲降维: {decision.reason}\n\n👉 **动作指示: 拿 ¥{decision.hedge_stake:.0f} 扔向大盘抛售 (要求赔率 > {decision.hedge_odds:.2f})**")

    if decision.action != "REJECT":
        if st.button("✅ 签字确权 (落盘固化)", type="primary"):
            orchestrator.commit_decision(decision, ticket)
            st.toast("入库成功！资金水池与订单簿已死死锁定在硬盘中。", icon="💾")
            if "last_decision" in st.session_state: del st.session_state.last_decision
            if "last_ticket" in st.session_state: del st.session_state.last_ticket
            st.rerun()

def main():
    st.title("🏦 影子做市商 | 永久底仓与审计溯源")
    st.markdown("此时此刻，你的账本已接入 SQLite 硬盘。哪怕直接拔掉服务器电源，你的风控数据也绝对不会丢失！")
    
    main_tabs = st.tabs(["🎮 业务模拟前台", "🌊 庄家水池", "🧾 历史订单簿"])
    
    with main_tabs[0]:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("📥 录单发票")
            ticket_type = st.radio("单据类型", ["单关", "二串一"], horizontal=True)
            stake = st.number_input("下注金额 (¥)", 1000, 50000, 10000, 1000)
            
            if ticket_type == "单关":
                match_id = st.text_input("赛事指纹", "Manchester United vs Tottenham Hotspur", disabled=True)
                sel = st.selectbox("客户押注", ["home", "away", "draw"])
                odds = st.number_input("客户赔率", 1.01, 10.0, 2.00, 0.05)
                submit = st.button("🚀 呼叫大脑", use_container_width=True)
                if submit:
                    ticket = CustomerTicket(ticket_id=f"T-{uuid.uuid4().hex[:5].upper()}", ticket_type="single", stake=stake, legs=[TicketLeg(match_id=match_id, selection=sel, customer_odds=odds)])
            else:
                l1_s = st.selectbox("选项 1", ["home", "away", "draw"], key="p_s1")
                l1_o = st.number_input("赔率 1", 1.01, 10.0, 2.05, 0.05, key="p_o1")
                l2_s = st.selectbox("选项 2", ["home", "away", "draw"], key="p_s2")
                l2_o = st.number_input("赔率 2", 1.01, 10.0, 1.80, 0.05, key="p_o2")
                submit = st.button("🚀 呼叫大脑", use_container_width=True)
                if submit:
                    ticket = CustomerTicket(ticket_id=f"PLY-{uuid.uuid4().hex[:5].upper()}", ticket_type="parlay_2", stake=stake, legs=[
                        TicketLeg(match_id="Manchester United vs Tottenham Hotspur", selection=l1_s, customer_odds=l1_o),
                        TicketLeg(match_id="Real Madrid vs Barcelona", selection=l2_s, customer_odds=l2_o)
                    ])

            if submit:
                try: loop = asyncio.get_running_loop()
                except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                st.session_state.last_decision = loop.run_until_complete(orchestrator.evaluate_incoming_tickets([ticket]))[0]
                st.session_state.last_ticket = ticket
                
        with c2:
            st.subheader("📊 裁决结果")
            if "last_decision" in st.session_state and "last_ticket" in st.session_state:
                render_decision(st.session_state.last_decision, st.session_state.last_ticket)

    with main_tabs[1]:
        st.subheader("🌐 全局净头寸大屏")
        exposures = orchestrator.ledger.get_all_exposures()
        if exposures:
            df_data = []
            for m_id, state in exposures.items():
                wcs = min(state.values())
                df_data.append({
                    "赛事": m_id.split("vs")[0].strip() + " vs...",
                    "主队赢(你盈亏)": state["home"],
                    "平局(你盈亏)": state["draw"],
                    "客队赢(你盈亏)": state["away"],
                    "🚨 极限亏损线": wcs
                })
            df = pd.DataFrame(df_data)
            def color_pnl(val):
                if isinstance(val, (int, float)):
                    if val < 0: return 'color: #ff4b4b; font-weight: bold'
                    if val > 0: return 'color: #00fa9a; font-weight: bold'
                return ''
            st.dataframe(df.style.map(color_pnl, subset=["主队赢(你盈亏)", "平局(你盈亏)", "客队赢(你盈亏)", "🚨 极限亏损线"]).format(precision=0), use_container_width=True)
        else:
            st.info("数据水池为空。")

        if st.button("💣 强制核销全系统数据 (次日清盘)", type="secondary"):
            orchestrator.wipe_all_data()
            if "last_decision" in st.session_state: del st.session_state.last_decision
            st.rerun()

    with main_tabs[2]:
        st.subheader("🧾 成功落盘的审计流水")
        history = orchestrator.db.get_order_book()
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True)
        else:
            st.write("暂无确权入库的订单。")

if __name__ == "__main__":
    main()