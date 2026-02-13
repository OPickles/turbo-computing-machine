import sys, os, asyncio, uuid
import streamlit as st
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.shadow_bookmaker.application.orchestrator import BrokerOrchestrator
from src.shadow_bookmaker.domain.ledger import GlobalLedger
from src.shadow_bookmaker.domain.models import CustomerTicket, TicketLeg

st.set_page_config(page_title="Shadow Broker | 全局清算矩阵", layout="wide")

# 运用 Session State 让系统拥有持久化记忆
if "ledger" not in st.session_state:
    st.session_state.ledger = GlobalLedger()
    st.session_state.orchestrator = BrokerOrchestrator(st.session_state.ledger)

orchestrator = st.session_state.orchestrator

def render_decision(decision):
    st.markdown("### ⚡ 智能路由指令")
    if decision.action == "REJECT": 
        st.error(f"🔴 拒单: {decision.reason}")
    elif decision.action == "ACCEPT_B_BOOK": 
        st.info(f"🔵 吃单入库: {decision.reason}")
    elif decision.action in ["ACCEPT_PARTIAL_HEDGE", "ACCEPT_A_BOOK_HEDGE"]: 
        st.warning(f"🟡 对冲降维: {decision.reason}\n\n👉 **动作指示: 拿 ¥{decision.hedge_stake:.0f} 扔向外网大盘对冲 (要求赔率 > {decision.hedge_odds:.2f})**")

    # 手动确权模拟（真实生产环境中这是系统毫秒级自动完成的）
    if decision.action != "REJECT":
        if st.button("✅ 签字确权，将风险并入总账本", type="primary"):
            orchestrator.commit_decision(decision)
            st.toast("入库成功！右侧账本水位已更新。", icon="🌊")
            del st.session_state.last_decision
            st.rerun()

def main():
    st.title("🏦 影子做市商 | 全局盈亏清算矩阵 (PnL Ledger)")
    st.markdown("突破**单据孤岛**！连续录单观察庄家水位的涨跌，体会华尔街多空对冲与系统智能泄洪的威力。")
    st.markdown("---")

    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📥 流水线模拟器 (蚂蚁搬家)")
        st.info("不改变参数，连续发射同一张注单，观察何时系统判定水位溢出并强制大盘泄洪！")
        
        tab1, tab2 = st.tabs(["🎯 单关进单", "🔗 串子进单"])
        with tab1:
            stake = st.number_input("下注金额 (¥)", 1000, 50000, 15000, 1000, key="s_stake")
            match_id = st.text_input("赛事指纹", "Manchester United vs Tottenham Hotspur", disabled=True)
            sel = st.selectbox("客户押注", ["home", "away", "draw"], key="s_sel")
            odds = st.number_input("客户赔率", 1.01, 10.0, 2.00, 0.05, key="s_odds")
            submit_s = st.button("🚀 发射沙盘单据", use_container_width=True)
            
        with tab2:
            p_stake = st.number_input("下注金额 (¥)", 1000, 50000, 10000, 1000, key="p_stake")
            l1_s = st.selectbox("选项 1", ["home", "away", "draw"], key="p_s1")
            l1_o = st.number_input("赔率 1", 1.01, 10.0, 2.05, 0.05, key="p_o1")
            l2_s = st.selectbox("选项 2", ["home", "away", "draw"], key="p_s2")
            l2_o = st.number_input("赔率 2", 1.01, 10.0, 1.80, 0.05, key="p_o2")
            submit_p = st.button("🚀 发射串子单据", use_container_width=True)

        if submit_s or submit_p:
            if submit_s:
                ticket = CustomerTicket(ticket_id=f"T-{uuid.uuid4().hex[:4].upper()}", ticket_type="single", stake=stake, legs=[TicketLeg(match_id=match_id, selection=sel, customer_odds=odds)])
            else:
                ticket = CustomerTicket(ticket_id=f"PLY-{uuid.uuid4().hex[:4].upper()}", ticket_type="parlay_2", stake=p_stake, legs=[
                    TicketLeg(match_id="Manchester United vs Tottenham Hotspur", selection=l1_s, customer_odds=l1_o),
                    TicketLeg(match_id="Real Madrid vs Barcelona", selection=l2_s, customer_odds=l2_o)
                ])
                
            try: loop = asyncio.get_running_loop()
            except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            
            st.session_state.last_decision = loop.run_until_complete(orchestrator.evaluate_incoming_tickets([ticket]))[0]
            
        st.markdown("---")
        if "last_decision" in st.session_state:
            render_decision(st.session_state.last_decision)

    with col2:
        st.subheader("🌐 全局净头寸大屏 (防爆仓红线: ¥ -30,000)")
        
        exposures = orchestrator.ledger.get_all_exposures()
        if exposures:
            df_data = []
            for m_id, state in exposures.items():
                wcs = min(state.values())
                df_data.append({
                    "赛事 (Match ID)": m_id.split("vs")[0].strip() + " vs...",
                    "主队赢(你盈亏)": state["home"],
                    "平局出(你盈亏)": state["draw"],
                    "客队赢(你盈亏)": state["away"],
                    "🚨 最惨境地 (Risk)": wcs
                })
            df = pd.DataFrame(df_data)
            
            # 格式化显示：负数为红色(庄家亏损)，正数为绿色(庄家赚客损)
            def color_pnl(val):
                if isinstance(val, (int, float)):
                    if val < 0: return 'color: #ff4b4b; font-weight: bold'
                    if val > 0: return 'color: #00fa9a; font-weight: bold'
                return ''
                
            styled_df = df.style.map(color_pnl, subset=["主队赢(你盈亏)", "平局出(你盈亏)", "客队赢(你盈亏)", "🚨 最惨境地 (Risk)"]).format(precision=0)
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("水池空空如也，等待源源不断的水位注入。")

        if st.button("💣 强制平盘清理 (模拟次日结算)"):
            st.session_state.ledger = GlobalLedger()
            st.session_state.orchestrator = BrokerOrchestrator(st.session_state.ledger)
            if "last_decision" in st.session_state: del st.session_state.last_decision
            st.rerun()

if __name__ == "__main__":
    main()