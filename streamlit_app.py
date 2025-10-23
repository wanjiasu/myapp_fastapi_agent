import streamlit as st
import sys
import os
from typing import Dict, Any
import traceback

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入分析功能
from match_fundamentals_analyst import graph

def main():
    """主应用函数"""
    st.set_page_config(
        page_title="足球比赛基本面分析",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 页面标题
    st.title("⚽ 足球比赛基本面分析系统")
    st.markdown("---")
    
    # 侧边栏输入
    with st.sidebar:
        st.header("📊 分析参数")
        
        # 用户输入fixture_id
        fixture_id = st.text_input(
            "比赛ID (Fixture ID)",
            placeholder="请输入比赛ID，例如：1347805",
            help="输入您要分析的比赛的唯一标识符"
        )
        
        # 分析按钮
        analyze_button = st.button(
            "🔍 开始分析",
            type="primary",
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### 📝 使用说明")
        st.markdown("""
        1. 在上方输入框中输入比赛ID
        2. 点击"开始分析"按钮
        3. 系统将自动获取并分析比赛数据
        4. 分析结果将在右侧显示
        """)
    
    # 主内容区域
    if analyze_button and fixture_id:
        if not fixture_id.strip():
            st.error("❌ 请输入有效的比赛ID")
            return
            
        try:
            # 验证fixture_id是否为数字
            fixture_id_int = int(fixture_id.strip())
            
            # 显示加载状态
            with st.spinner("🔄 正在分析比赛数据，请稍候..."):
                # 调用分析功能
                result = run_analysis(fixture_id_int)
                
            # 显示分析结果
            display_results(fixture_id_int, result)
            
        except ValueError:
            st.error("❌ 比赛ID必须是数字格式")
        except Exception as e:
            st.error(f"❌ 分析过程中出现错误: {str(e)}")
            with st.expander("🔍 查看详细错误信息"):
                st.code(traceback.format_exc())
    
    elif analyze_button and not fixture_id:
        st.warning("⚠️ 请先输入比赛ID")
    
    else:
        # 默认显示欢迎信息
        display_welcome()

def run_analysis(fixture_id: int) -> Dict[str, Any]:
    """运行比赛分析"""
    try:
        # 创建初始状态
        initial_state = {
            "messages": [],
            "fixture_id": fixture_id,
            "fundamentals_repost": ""
        }
        
        # 运行分析图
        result = graph.invoke(initial_state)
        return result
        
    except Exception as e:
        st.error(f"分析失败: {str(e)}")
        raise e

def display_results(fixture_id: int, result: Dict[str, Any]):
    """显示分析结果"""
    st.header(f"📈 比赛 {fixture_id} 分析结果")
    
    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["📊 基本面报告", "💬 详细消息", "📋 原始数据"])
    
    with tab1:
        st.subheader("🎯 基本面分析报告")
        
        # 显示基本面报告
        if "fundamentals_repost" in result and result["fundamentals_repost"]:
            st.markdown(result["fundamentals_repost"])
        else:
            st.info("📝 基本面报告正在生成中...")
            
            # 如果有消息但没有报告，显示最后一条消息的内容
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content') and last_message.content:
                    st.markdown("### 🤖 AI分析结果")
                    st.markdown(last_message.content)
    
    with tab2:
        st.subheader("💬 分析过程详情")
        
        if "messages" in result and result["messages"]:
            for i, message in enumerate(result["messages"]):
                with st.expander(f"消息 {i+1}"):
                    if hasattr(message, 'content'):
                        st.markdown(message.content)
                    
                    # 显示工具调用信息
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        st.markdown("**🔧 工具调用:**")
                        for tool_call in message.tool_calls:
                            st.json(tool_call)
        else:
            st.info("暂无详细消息")
    
    with tab3:
        st.subheader("📋 原始数据")
        st.json(result)

def display_welcome():
    """显示欢迎页面"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ## 🎯 欢迎使用足球比赛基本面分析系统
        
        ### 🚀 功能特点
        - **📊 全面分析**: 获取比赛基本信息、球队数据、积分榜等
        - **🔍 深度洞察**: AI驱动的比赛基本面分析
        - **📈 数据可视化**: 清晰展示分析结果
        - **⚡ 实时数据**: 基于最新的API-Football数据
        
        ### 📋 分析内容包括
        - ⚽ 比赛基本信息（时间、场地、联赛等）
        - 🏆 球队实力对比（排名、积分、进失球）
        - 📊 近期状态分析（最近10场比赛）
        - 🤕 伤停信息
        - 📈 历史交锋记录
        - 🎯 战意分析
        
        ### 🎮 开始使用
        请在左侧输入比赛ID，然后点击"开始分析"按钮开始您的分析之旅！
        """)
        
        # 示例比赛ID
        st.markdown("### 💡 示例比赛ID")
        example_ids = ["1347805", "1451200", "1451373"]
        
        cols = st.columns(len(example_ids))
        for i, example_id in enumerate(example_ids):
            with cols[i]:
                if st.button(f"📝 {example_id}", key=f"example_{i}"):
                    st.session_state.example_fixture_id = example_id
                    st.rerun()

if __name__ == "__main__":
    main()