import sys, os, asyncio
import streamlit as st
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.shadow_bookmaker.application.orchestrator import BrokerOrchestrator
from src.shadow_bookmaker.domain.models import CustomerTicket, TicketLeg

st.set_page_config(page_title="Shadow Broker | A/B仓路由总台", layout="wide")

@st.cache_resource
def get_orchestrator(): return BrokerOrchestrator()

def render_decision(decision, ticket):
    if decision.action == "REJECT":
        st.error("### 🔴 毒药单警告：全额拒单 (REJECT)")
        st.write(f"**拦截原因:** {decision.reason}")
    elif decision.action == "ACCEPT_A_BOOK_HEDGE":
        st.success("### 🟢 无风险套利：接单并抛盘 (A-Book)")
        st.info(f"👉 **动作:** 拿着客户的钱，去外围下注 **¥{decision.hedge_stake:.0f}**")
    elif decision.action == "ACCEPT_B_BOOK":
        st.info("### 🔵 优质韭菜单：全额吃飞入底仓 (B-Book)")
        st.write(f"**决策:** {decision.reason}")
        st.info(f"👉 **指令:** 本金 **¥{decision.b_book_stake:.0f}** 闭着眼睛全吃。")
    elif decision.action == "ACCEPT_PARTIAL_HEDGE":
        st.warning("### 🟡 敞口超限：降维对冲 (Partial Hedge)")
        st.write(f"**决策:** {decision.reason}")
        st.info(f"👉 **核指令:** 截留底仓，并立刻去大盘重注单场 **¥{decision.hedge_stake:.0f}** (赔率要求 > {decision.hedge_odds:.2f}) 强行断腿。")

    st.markdown("---")
    cols = st.columns(4)
    cols[0].metric("客户总赔率", f"{ticket.total_odds:.2f}")
    cols[1].metric("大盘真实胜率", f"{decision.true_probability*100:.2f}%")
    cols[2].metric("庄家期望(EV)", f"{decision.house_ev*100:.2f}%")
    cols[3].metric("万一爆冷净亏", f"¥ {ticket.liability:.0f}")

def main():
    st.title("🛡️ Shadow Broker | 风控核心中控台")
    st.markdown("机制：**De-vig 去水 -> EV 计算 -> 智能路由 (吃飞入库 / 断腿对冲 / 拒单)**")
    
    tab1, tab2 = st.tabs(["🎯 单关票 (Single)", "🔗 二串一票 (Parlay)"])
    orchestrator = get_orchestrator()

    with tab1:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("📥 录入单关")
            with st.form("single_form"):
                stake = st.number_input("下注金额 (¥)", 1000, 50000, 15000, 1000)
                match_id = st.text_input("赛事指纹", "Manchester United vs Tottenham Hotspur", disabled=True)
                sel = st.selectbox("选项", ["home", "away", "draw"])
                odds = st.number_input("客户赔率", 1.01, 10.0, 2.00, 0.05)
                submit_s = st.form_submit_button("🚀 裁决单场")
        with c2:
            st.subheader("📊 裁决雷达")
            if submit_s:
                ticket = CustomerTicket(ticket_id=f"SGL-{uuid.uuid4().hex[:6].upper()}", ticket_type="single", stake=stake, legs=[TicketLeg(match_id=match_id, selection=sel, customer_odds=odds)])
                try: loop = asyncio.get_running_loop()
                except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                render_decision(loop.run_until_complete(orchestrator.evaluate_incoming_tickets([ticket]))[0], ticket)

    with tab2:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("📥 录入二串一 (高利润区)")
            with st.form("parlay_form"):
                p_stake = st.number_input("下注金额 (¥)", 1000, 50000, 10000, 1000)
                st.markdown("**第一腿 (Leg 1)**")
                l1_m = st.text_input("赛事 1", "Manchester United vs Tottenham Hotspur", disabled=True)
                l1_s = st.selectbox("选项 1", ["home", "away", "draw"], key="s1")
                l1_o = st.number_input("赔率 1", 1.01, 10.0, 2.05, 0.05, key="o1")
                st.markdown("**第二腿 (Leg 2)**")
                l2_m = st.text_input("赛事 2", "Real Madrid vs Barcelona", disabled=True)
                l2_s = st.selectbox("选项 2", ["home", "away", "draw"], index=0, key="s2")
                l2_o = st.number_input("赔率 2", 1.01, 10.0, 1.80, 0.05, key="o2")
                submit_p = st.form_submit_button("🚀 核动力断腿裁决")
        with c2:
            st.subheader("📊 降维抛盘运算")
            if submit_p:
                ticket = CustomerTicket(ticket_id=f"PLY-{uuid.uuid4().hex[:6].upper()}", ticket_type="parlay_2", stake=p_stake, legs=[
                        TicketLeg(match_id=l1_m, selection=l1_s, customer_odds=l1_o),
                        TicketLeg(match_id=l2_m, selection=l2_s, customer_odds=l2_o)
                    ])
                try: loop = asyncio.get_running_loop()
                except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                render_decision(loop.run_until_complete(orchestrator.evaluate_incoming_tickets([ticket]))[0], ticket)

if __name__ == "__main__":
    main()