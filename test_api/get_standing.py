#!/usr/bin/env python3
"""
API-Football Standings获取脚本
获取指定联赛的积分榜数据并保存为JSON文件
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class APIFootballClient:
    """API-Football客户端类"""
    
    def __init__(self):
        """初始化API客户端"""
        self.api_key = os.getenv('API_FOOTBALL_KEY')
        if not self.api_key:
            raise ValueError("请在.env文件中设置API_FOOTBALL_KEY")
        
        # API-Football的基础URL和请求头
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'v3.football.api-sports.io'
        }
    
    def get_standings(self, league_id, season, team_id=None):
        """
        获取联赛积分榜数据
        
        Args:
            league_id (int): 联赛ID
            season (int): 赛季年份
            team_id (int, optional): 特定球队ID，如果提供则只返回该球队的积分榜信息
        
        Returns:
            dict: API响应数据
        """
        endpoint = f"/standings"
        url = f"{self.base_url}{endpoint}"
        
        # 设置查询参数
        params = {
            'league': league_id,
            'season': season
        }
        
        # 如果指定了球队ID，添加到参数中
        if team_id:
            params['team'] = team_id
        
        try:
            print(f"正在获取联赛 {league_id} 赛季 {season} 的积分榜数据...")
            if team_id:
                print(f"筛选球队ID: {team_id}")
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            standings_count = len(data.get('response', []))
            
            if standings_count > 0:
                print(f"成功获取到积分榜数据")
                return data
            else:
                print(f"未找到联赛 {league_id} 赛季 {season} 的积分榜数据")
                return None
            
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None
    
    def extract_standings_info(self, standings_data):
        """
        从API响应中提取积分榜信息
        
        Args:
            standings_data (dict): API返回的完整数据
        
        Returns:
            list: 提取的积分榜信息列表
        """
        if not standings_data or 'response' not in standings_data or not standings_data['response']:
            return []
        
        extracted_standings = []
        
        for league_standing in standings_data['response']:
            league_info = league_standing['league']
            
            # 处理每个积分榜组（通常只有一个，但某些联赛可能有多个组）
            for standing_group in league_standing['league']['standings']:
                for team_standing in standing_group:
                    standing_info = {
                        'league_id': league_info['id'],
                        'league_name': league_info['name'],
                        'league_country': league_info['country'],
                        'league_season': league_info['season'],
                        'team_id': team_standing['team']['id'],
                        'team_name': team_standing['team']['name'],
                        'rank': team_standing['rank'],
                        'points': team_standing['points'],
                        'goalsDiff': team_standing['goalsDiff'],
                        'group': team_standing['group'],
                        'form': team_standing['form'],
                        'status': team_standing['status'],
                        'description': team_standing['description'],
                        'all_played': team_standing['all']['played'],
                        'all_win': team_standing['all']['win'],
                        'all_draw': team_standing['all']['draw'],
                        'all_lose': team_standing['all']['lose'],
                        'all_goals_for': team_standing['all']['goals']['for'],
                        'all_goals_against': team_standing['all']['goals']['against'],
                        'home_played': team_standing['home']['played'],
                        'home_win': team_standing['home']['win'],
                        'home_draw': team_standing['home']['draw'],
                        'home_lose': team_standing['home']['lose'],
                        'home_goals_for': team_standing['home']['goals']['for'],
                        'home_goals_against': team_standing['home']['goals']['against'],
                        'away_played': team_standing['away']['played'],
                        'away_win': team_standing['away']['win'],
                        'away_draw': team_standing['away']['draw'],
                        'away_lose': team_standing['away']['lose'],
                        'away_goals_for': team_standing['away']['goals']['for'],
                        'away_goals_against': team_standing['away']['goals']['against']
                    }
                    extracted_standings.append(standing_info)
        
        return extracted_standings
    
    def save_standings_to_json(self, standings_data, output_dir, filename=None):
        """
        将积分榜数据保存为JSON文件
        
        Args:
            standings_data (list): 积分榜数据
            output_dir (str): 输出目录路径
            filename (str): 文件名，如果为None则自动生成
        
        Returns:
            str: 保存的文件路径
        """
        if not standings_data:
            print("没有数据可保存")
            return None
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"standings_{timestamp}.json"
        
        file_path = os.path.join(output_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(standings_data, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"保存文件失败: {e}")
            return None

def main():
    """主函数"""
    try:
        # 创建API客户端
        client = APIFootballClient()
        
        # 输入参数 - 根据用户要求设置
        league_id = 848      # 联赛ID
        league_season = 2025 # 赛季
        home_id = 95         # 球队ID (这里用作team_id参数)
        
        print(f"🏆 开始获取积分榜数据...")
        print(f"📊 联赛ID: {league_id}")
        print(f"📅 赛季: {league_season}")
        print(f"⚽ 球队ID: {home_id}")
        
        # 获取积分榜数据
        standings_data = client.get_standings(league_id, league_season, home_id)
        
        if standings_data:
            # 提取积分榜信息
            extracted_standings = client.extract_standings_info(standings_data)
            
            if extracted_standings:
                # 保存数据到JSON文件
                output_dir = "/Users/kuriball/Documents/MyProjects/agent/bc_agent/test_api/test_output"
                filename = f"standings_league_{league_id}_season_{league_season}_team_{home_id}.json"
                
                saved_file = client.save_standings_to_json(
                    extracted_standings, 
                    output_dir, 
                    filename
                )
                
                if saved_file:
                    print(f"\n✅ 成功完成!")
                    print(f"🏆 联赛: {extracted_standings[0]['league_name']} ({extracted_standings[0]['league_country']})")
                    print(f"📅 赛季: {extracted_standings[0]['league_season']}")
                    print(f"📊 球队数量: {len(extracted_standings)}")
                    print(f"💾 文件路径: {saved_file}")
                    
                    # 显示积分榜信息
                    print(f"\n📋 积分榜信息:")
                    for i, team in enumerate(extracted_standings):
                        print(f"\n球队 {i+1}:")
                        print(f"  排名: {team['rank']}")
                        print(f"  球队: {team['team_name']}")
                        print(f"  积分: {team['points']}")
                        print(f"  比赛场次: {team['all_played']}")
                        print(f"  胜/平/负: {team['all_win']}/{team['all_draw']}/{team['all_lose']}")
                        print(f"  进球/失球: {team['all_goals_for']}/{team['all_goals_against']}")
                        print(f"  净胜球: {team['goalsDiff']}")
                        print(f"  近期状态: {team['form']}")
                else:
                    print("❌ 保存文件失败")
            else:
                print("❌ 提取积分榜信息失败")
        else:
            print("❌ 获取积分榜数据失败")
            
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")

if __name__ == "__main__":
    main()