import sys, os, asyncio
import streamlit as st
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.shadow_bookmaker.application.orchestrator import BrokerOrchestrator
from src.shadow_bookmaker.domain.models import CustomerTicket, TicketLeg

st.set_page_config(page_title="Shadow Broker | 信用网风控台", layout="wide")

@st.cache_resource
def get_orchestrator(): return BrokerOrchestrator()

def main():
    st.title("🛡️ Shadow Broker | A/B仓风控路由中控台")
    st.markdown("系统核心规则：**自动剥离大盘抽水 -> 计算真实数学期望 -> 动态路由 (吃单入库 / 抛盘对冲 / 直接拒单)**")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📥 录入客户工单")
        with st.form("ticket_form"):
            stake = st.number_input("下注金额 (¥)", min_value=1000, max_value=50000, value=8000, step=1000)
            
            st.markdown("##### 比赛场次设置")
            match_id_1 = st.text_input("赛事指纹", "Manchester United vs Tottenham Hotspur", disabled=True)
            selection_1 = st.selectbox("下注选项", ["home", "away", "draw"])
            customer_odds_1 = st.number_input("客户要求赔率", min_value=1.01, max_value=10.0, value=1.85, step=0.05)
            
            submit = st.form_submit_button("🚀 提交智能引擎裁决", use_container_width=True)

    with col2:
        st.subheader("📊 风控雷达判决令")
        if submit:
            ticket = CustomerTicket(
                ticket_id=f"TCK-{str(uuid.uuid4())[:6].upper()}", ticket_type="single", stake=stake,
                legs=[TicketLeg(match_id=match_id_1, selection=selection_1, customer_odds=customer_odds_1)]
            )
            
            orchestrator = get_orchestrator()
            with st.spinner("请求 Pinnacle 标杆大盘，执行极其复杂的 De-vigging (去水) 计算..."):
                try: loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                decisions = loop.run_until_complete(orchestrator.evaluate_incoming_tickets([ticket]))
            
            decision = decisions[0]
            
            # UI 渲染
            if decision.action == "REJECT":
                st.error("### 🔴 毒药单警告：全额拒单 (REJECT)")
                st.write(f"**拦截原因:** {decision.reason}")
            elif decision.action == "ACCEPT_A_BOOK_HEDGE":
                 st.success("### 🟢 无风险套利：接单并抛盘 (A-Book)")
                 st.write(f"**决策理由:** {decision.reason}")
                 st.info(f"👉 **系统动作:** 拿着客户的钱，去外围下注 **¥{decision.hedge_stake:.0f}** (目标最低赔率必须 > {decision.hedge_odds:.2f})")
            elif decision.action == "ACCEPT_B_BOOK":
                 st.info("### 🔵 优质韭菜单：全额吃飞入底仓 (B-Book)")
                 st.write(f"**决策理由:** {decision.reason}")
                 st.info(f"👉 **系统动作:** 自己硬吃这笔金额 **¥{decision.b_book_stake:.0f}**，长期赢取大数概率差额。")
            elif decision.action == "ACCEPT_PARTIAL_HEDGE":
                 st.warning("### 🟡 敞口超限：部分对冲降维 (Partial Hedge)")
                 st.write(f"**决策理由:** {decision.reason}")
                 st.info(f"👉 **系统动作:** 截留自己吃下 **¥{decision.b_book_stake:.0f}**，剩余溢出风险拿去大盘打水 **¥{decision.hedge_stake:.0f}**。")

            st.markdown("---")
            st.markdown("#### 核心算力透视")
            metrics_cols = st.columns(4)
            metrics_cols[0].metric("客户综合赔率", f"{ticket.total_odds:.2f}")
            metrics_cols[1].metric("大盘去水真实胜率", f"{decision.true_probability*100:.1f}%")
            metrics_cols[2].metric("庄家期望优势(EV)", f"{decision.house_ev*100:.2f}%")
            metrics_cols[3].metric("万一爆冷的净亏损", f"¥ {ticket.liability:.0f}")

if __name__ == "__main__":
    main()