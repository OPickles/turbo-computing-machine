import sys, os, asyncio
import streamlit as st
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.shadow_bookmaker.application.orchestrator import ArbitrageOrchestrator

st.set_page_config(page_title="ShadowBookmaker Terminal", layout="wide")

@st.cache_resource
def get_orchestrator():
    return ArbitrageOrchestrator()

# 核心防封策略：缓存锁死 30 秒，防止用户狂点按钮导致 API 爆量封禁
@st.cache_data(ttl=30)
def fetch_opportunities():
    orchestrator = get_orchestrator()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(orchestrator.run_scan())

def main():
    st.title("🕵️‍♂️ Shadow Bookmaker | 暗影套利终端")
    st.markdown("---")

    if st.button("🚀 极速扫描全网盘口 (强制刷新)"):
        st.cache_data.clear()
        
    with st.spinner("多线程并发穿透各大盘口，执行对冲计算中..."):
        opportunities = fetch_opportunities()
        
    if not opportunities:
        st.info("当前全网水位干涸，庄家风控严密，未发现无风险套利空间。")
    else:
        st.success(f"🔥 破局成功！锁定 {len(opportunities)} 个高价值套利机会。")
        
        display_data = []
        for opp in opportunities:
            display_data.append({
                "赛事 (统一指纹)": opp.match_id,
                "净利润率": f"{opp.profit_margin*100:.2f}%",
                "买入主胜": f"{opp.best_home_bookie} @ {opp.best_home_odds}",
                "主胜注码": f"¥ {opp.recommended_stakes['home']:.2f}",
                "买入客胜": f"{opp.best_away_bookie} @ {opp.best_away_odds}",
                "客胜注码": f"¥ {opp.recommended_stakes['away']:.2f}"
            })
            
        st.dataframe(pd.DataFrame(display_data), use_container_width=True)

if __name__ == "__main__":
    main()