import sys, os, asyncio, uuid
import streamlit as st
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.shadow_bookmaker.application.orchestrator import BrokerOrchestrator
from src.shadow_bookmaker.domain.models import CustomerTicket, TicketLeg
from src.shadow_bookmaker.config import settings

st.set_page_config(page_title="Shadow Broker | 现实接轨版", layout="wide")

@st.cache_resource
def get_orchestrator(): return BrokerOrchestrator()
orchestrator = get_orchestrator()

def fetch_live_matches(force=False):
    try: loop = asyncio.get_running_loop()
    except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    return loop.run_until_complete(orchestrator.get_live_market(force))

def render_decision(decision, ticket):
    st.markdown("### ⚡ 智能路由指令")
    if decision.action == "REJECT": 
        st.error(f"🔴 毒药单拦截: {decision.reason}")
    elif decision.action == "ACCEPT_B_BOOK": 
        st.info(f"🔵 吃单入库: {decision.reason}")
    elif decision.action in ["ACCEPT_PARTIAL_HEDGE", "ACCEPT_A_BOOK_HEDGE"]: 
        st.warning(f"🟡 对冲降维: {decision.reason}\n\n👉 **动作指示: 拿 ¥{decision.hedge_stake:.0f} 扔向真实大盘平博(Pinnacle)对冲 (要求赔率不得低于 {decision.hedge_odds:.2f})**")

    if decision.action != "REJECT":
        if st.button("✅ 签字确权 (固化入 SQLite)", type="primary"):
            orchestrator.commit_decision(decision, ticket)
            st.toast("入库成功！资金水池已锁定硬盘。", icon="💾")
            if "last_decision" in st.session_state: del st.session_state.last_decision
            if "last_ticket" in st.session_state: del st.session_state.last_ticket
            st.rerun()

def main():
    with st.sidebar:
        st.header("⚙️ 引擎总控台")
        # 允许在 UI 上直接配置密钥
        api_key = st.text_input("🔑 The Odds API Key", value=settings.ODDS_API_KEY, type="password")
        if api_key and api_key != settings.ODDS_API_KEY: 
            settings.ODDS_API_KEY = api_key
            from src.shadow_bookmaker.infrastructure.bookmakers.the_odds_api import TheOddsAPIBookmaker
            orchestrator.pinnacle = TheOddsAPIBookmaker(orchestrator.mapper)
            fetch_live_matches(force=True)
            
        st.markdown("*[点击免费获取 API Key](https://the-odds-api.com/)*")
        
        if st.button("🔄 强制穿透外网大盘"):
            fetch_live_matches(force=True)
            st.toast("大盘水位已强行握手同步！", icon="📡")

    st.title("🌍 影子做市商 | 全球真实盘口直连版")

    if not settings.ODDS_API_KEY:
        st.warning("⚠️ 引擎处于脱机模拟状态。请在左侧侧边栏输入 API Key 以启动全球雷达监听！")

    with st.spinner("📡 正在穿透国际网络，拉取 Pinnacle 全球最新滚球/早盘数据..."):
        live_market = fetch_live_matches()

    if not live_market:
        st.error("🚨 无法获取真实比赛数据（可能是网络波动或额度耗尽），目前使用模拟兜底数据。")
        match_list = ["Mock Team A vs Mock Team B"]
    else:
        match_list = list(live_market.keys())

    main_tabs = st.tabs(["🎮 进单前台 (真单)", "🌊 庄家水池", "🧾 历史订单簿"])
    
    with main_tabs[0]:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("📥 截获真实散户工单")
            ticket_type = st.radio("单据类型", ["单关", "二串一"], horizontal=True)
            stake = st.number_input("下注金额 (¥)", 1000, 50000, 10000, 1000)
            
            if ticket_type == "单关":
                match_id = st.selectbox("🎯 真实赛事选择", match_list)
                sel = st.selectbox("客户押注", ["home", "away", "draw"])
                
                # 透视外网真实底牌
                if live_market and match_id in live_market:
                    real_odds = live_market[match_id]
                    st.caption(f"*(上帝底牌监控：主 {real_odds.home_odds} | 平 {real_odds.draw_odds} | 客 {real_odds.away_odds})*")
                
                odds = st.number_input("客户填写的赔率", 1.01, 20.0, 2.00, 0.05)
                submit = st.button("🚀 呼叫大脑执行实盘风控", use_container_width=True)
                if submit:
                    ticket = CustomerTicket(ticket_id=f"T-{uuid.uuid4().hex[:5].upper()}", ticket_type="single", stake=stake, legs=[TicketLeg(match_id=match_id, selection=sel, customer_odds=odds)])
            else:
                if len(match_list) < 2:
                    st.error("真实比赛场次不足2场，无法组成串关。")
                    submit = False
                else:
                    l1_m = st.selectbox("赛事 1", match_list, index=0, key="p_m1")
                    if live_market and l1_m in live_market: st.caption(f"*(底牌：主 {live_market[l1_m].home_odds} | 平 {live_market[l1_m].draw_odds} | 客 {live_market[l1_m].away_odds})*")
                    l1_s = st.selectbox("选项 1", ["home", "away", "draw"], key="p_s1")
                    l1_o = st.number_input("赔率 1", 1.01, 20.0, 2.05, 0.05, key="p_o1")
                    
                    st.markdown("---")
                    
                    l2_m = st.selectbox("赛事 2", match_list, index=1, key="p_m2")
                    if live_market and l2_m in live_market: st.caption(f"*(底牌：主 {live_market[l2_m].home_odds} | 平 {live_market[l2_m].draw_odds} | 客 {live_market[l2_m].away_odds})*")
                    l2_s = st.selectbox("选项 2", ["home", "away", "draw"], key="p_s2")
                    l2_o = st.number_input("赔率 2", 1.01, 20.0, 1.80, 0.05, key="p_o2")
                    submit = st.button("🚀 核动力实盘断腿测算", use_container_width=True)
                    if submit:
                        ticket = CustomerTicket(ticket_id=f"PLY-{uuid.uuid4().hex[:5].upper()}", ticket_type="parlay_2", stake=stake, legs=[
                            TicketLeg(match_id=l1_m, selection=l1_s, customer_odds=l1_o), TicketLeg(match_id=l2_m, selection=l2_s, customer_odds=l2_o)
                        ])

            if submit:
                try: loop = asyncio.get_running_loop()
                except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                st.session_state.last_decision = loop.run_until_complete(orchestrator.evaluate_incoming_tickets([ticket]))[0]
                st.session_state.last_ticket = ticket
                
        with c2:
            st.subheader("📊 实战裁决结果")
            if "last_decision" in st.session_state and "last_ticket" in st.session_state:
                render_decision(st.session_state.last_decision, st.session_state.last_ticket)

    with main_tabs[1]:
        st.subheader("🌐 全局净头寸大屏 (真实比赛敞口)")
        exposures = orchestrator.ledger.get_all_exposures()
        if exposures:
            df_data = []
            for m_id, state in exposures.items():
                wcs = min(state.values())
                df_data.append({
                    "赛事": m_id.split("vs")[0].strip() + " vs...",
                    "主队赢(你盈亏)": state["home"], "平局(你盈亏)": state["draw"], "客队赢(你盈亏)": state["away"], "🚨 极限亏损": wcs
                })
            df = pd.DataFrame(df_data)
            def color_pnl(val):
                if isinstance(val, (int, float)):
                    if val < 0: return 'color: #ff4b4b; font-weight: bold'
                    if val > 0: return 'color: #00fa9a; font-weight: bold'
                return ''
            st.dataframe(df.style.map(color_pnl, subset=["主队赢(你盈亏)", "平局(你盈亏)", "客队赢(你盈亏)", "🚨 极限亏损"]).format(precision=0), use_container_width=True)
        else:
            st.info("数据水池为空。")

        if st.button("💣 强制核销全系统数据 (次日清盘)", type="secondary"):
            orchestrator.wipe_all_data()
            if "last_decision" in st.session_state: del st.session_state.last_decision
            st.rerun()

    with main_tabs[2]:
        st.subheader("🧾 历史订单簿")
        history = orchestrator.db.get_order_book()
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True)

if __name__ == "__main__":
    main()