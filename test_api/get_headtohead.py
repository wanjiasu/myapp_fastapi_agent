#!/usr/bin/env python3
"""
API-Football Head-to-Head获取脚本
获取两支球队之间的历史对战记录并保存为JSON文件
"""

import os
import json
import requests
from datetime import datetime, timedelta
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
    
    def get_headtohead(self, home_id, away_id, last=None, timezone="UTC"):
        """
        获取两支球队的历史对战记录
        
        Args:
            home_id (int): 主队ID
            away_id (int): 客队ID
            last (int, optional): 最近N场比赛，默认为None（获取所有）
            timezone (str): 时区，默认为UTC
            
        Returns:
            dict: API响应数据
        """
        url = f"{self.base_url}/fixtures/headtohead"
        
        # 基本参数
        params = {
            'h2h': f'{home_id}-{away_id}',
            'timezone': timezone
        }
        
        # 如果指定了最近N场比赛
        if last:
            params['last'] = last
        
        print(f"请求URL: {url}")
        print(f"请求参数: {params}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            print(f"HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"API响应结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                
                if 'response' in data:
                    print(f"找到 {len(data['response'])} 场对战记录")
                    return data
                else:
                    print("API响应中没有找到'response'字段")
                    print(f"完整响应: {data}")
                    return data
            else:
                print(f"API请求失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}")
            return None
    
    def extract_headtohead_info(self, h2h_data):
        """
        从API响应中提取head-to-head信息
        
        Args:
            h2h_data (dict): API响应数据
        
        Returns:
            list: 提取的对战记录信息列表
        """
        if not h2h_data or 'response' not in h2h_data:
            return []
        
        extracted_matches = []
        
        for fixture in h2h_data['response']:
            try:
                match_info = {
                    # 球队信息
                    'home_team_id': fixture['teams']['home']['id'],
                    'away_team_id': fixture['teams']['away']['id'],
                    'fixture_date': fixture['fixture']['date'],
                    'home_team_winner': fixture['teams']['home']['winner'],
                    'away_team_winner': fixture['teams']['away']['winner'],
                    
                    # 比分信息
                    'goals_home': fixture['goals']['home'],
                    'goals_away': fixture['goals']['away']
                }
                
                extracted_matches.append(match_info)
                
            except KeyError as e:
                print(f"提取比赛信息时出错，缺少字段: {e}")
                continue
        
        return extracted_matches
    
    def _determine_match_result(self, home_goals, away_goals):
        """
        确定比赛结果
        
        Args:
            home_goals (int): 主队进球数
            away_goals (int): 客队进球数
        
        Returns:
            str: 比赛结果 ('home_win', 'away_win', 'draw', 'unknown')
        """
        if home_goals is None or away_goals is None:
            return 'unknown'
        
        if home_goals > away_goals:
            return 'home_win'
        elif away_goals > home_goals:
            return 'away_win'
        else:
            return 'draw'
    
    def save_headtohead_to_json(self, h2h_data, output_dir, filename=None):
        """
        将head-to-head数据保存到JSON文件
        
        Args:
            h2h_data (list): 提取的对战记录数据
            output_dir (str): 输出目录
            filename (str, optional): 文件名，如果不提供则自动生成
        
        Returns:
            str: 保存的文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"headtohead_{timestamp}.json"
        
        # 完整文件路径
        file_path = os.path.join(output_dir, filename)
        
        # 保存数据
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(h2h_data, f, ensure_ascii=False, indent=2)
        
        print(f"Head-to-head数据已保存到: {file_path}")
        return file_path

def main():
    """主函数"""
    try:
        # 创建API客户端
        client = APIFootballClient()
        
        # 测试参数
        home_id = 1073   # 示例：斯特拉斯堡
        away_id = 8255 # 示例：巴黎圣日耳曼
        last = 10      # 最近10场比赛
        timezone = "UTC"
        
        print(f"获取球队 {home_id} vs {away_id} 的历史对战记录...")
        print(f"参数: last={last}, timezone={timezone}, 不限制时间范围")
        
        # 获取head-to-head数据（不限制时间范围）
        h2h_data = client.get_headtohead(home_id, away_id, last, timezone)
        
        if h2h_data:
            # 提取详细信息
            extracted_data = client.extract_headtohead_info(h2h_data)
            
            if extracted_data:
                print(f"成功提取 {len(extracted_data)} 场对战记录")
                
                # 保存到JSON文件
                output_dir = "/Users/kuriball/Documents/MyProjects/agent/bc_agent/test_api/test_output"
                filename = f"headtohead_team_{home_id}_vs_{away_id}_last_{last}.json"
                
                # 直接保存比赛列表，不包装在额外的结构中
                client.save_headtohead_to_json(extracted_data, output_dir, filename)
                
                # 显示统计信息
                print("\n=== 对战记录统计 ===")
                home_wins = sum(1 for match in extracted_data if match['home_team_winner'] == True)
                away_wins = sum(1 for match in extracted_data if match['away_team_winner'] == True)
                draws = sum(1 for match in extracted_data if match['home_team_winner'] == False and match['away_team_winner'] == False)
                
                print(f"主队胜利: {home_wins} 场")
                print(f"客队胜利: {away_wins} 场")
                print(f"平局: {draws} 场")
                print(f"总计: {len(extracted_data)} 场")
                
            else:
                print("没有找到对战记录数据")
        else:
            print("获取head-to-head数据失败")
            
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()