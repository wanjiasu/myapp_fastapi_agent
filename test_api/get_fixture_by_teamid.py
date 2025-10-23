#!/usr/bin/env python3
"""
API-Football 球队比赛获取脚本
获取指定球队的最近N场比赛记录并保存为JSON文件
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
    
    def get_fixtures_by_team(self, team_id, last=10, timezone="UTC"):
        """
        获取指定球队的比赛记录
        
        Args:
            team_id (int): 球队ID
            last (int): 最近N场比赛，默认为10
            timezone (str): 时区，默认为UTC
            
        Returns:
            dict: API响应数据
        """
        url = f"{self.base_url}/fixtures"
        
        # 基本参数
        params = {
            'team': team_id,
            'last': last,
            'timezone': timezone
        }
        
        print(f"请求URL: {url}")
        print(f"请求参数: {params}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            print(f"HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"API响应结构: {list(data.keys())}")
                return data
            else:
                print(f"API请求失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}")
            return None
    
    def extract_fixture_info(self, fixtures_data):
        """
        从API响应中提取比赛信息
        
        Args:
            fixtures_data (dict): API响应数据
            
        Returns:
            list: 提取的比赛信息列表
        """
        if not fixtures_data or 'response' not in fixtures_data:
            print("无效的API响应数据")
            return []
        
        fixtures = fixtures_data['response']
        print(f"找到 {len(fixtures)} 场比赛记录")
        
        extracted_fixtures = []
        
        for fixture in fixtures:
            try:
                fixture_info = {
                    # 比赛基本信息
                    'fixture_id': fixture['fixture']['id'],
                    'fixture_date': fixture['fixture']['date'],
                    'status': fixture['fixture']['status']['short'],
                    
                    # 球队信息
                    'home_team_id': fixture['teams']['home']['id'],
                    'home_team_name': fixture['teams']['home']['name'],
                    'away_team_id': fixture['teams']['away']['id'],
                    'away_team_name': fixture['teams']['away']['name'],
                    
                    # 比赛结果
                    'home_team_winner': fixture['teams']['home']['winner'],
                    'away_team_winner': fixture['teams']['away']['winner'],
                    'goals_home': fixture['goals']['home'],
                    'goals_away': fixture['goals']['away'],
                    
                    # 联赛信息
                    'league_id': fixture['league']['id'],
                    'league_name': fixture['league']['name'],
                    'season': fixture['league']['season']
                }
                
                extracted_fixtures.append(fixture_info)
                
            except KeyError as e:
                print(f"提取比赛信息时出错，缺少字段: {e}")
                continue
        
        print(f"成功提取 {len(extracted_fixtures)} 场比赛记录")
        return extracted_fixtures
    
    def save_fixtures_to_json(self, fixtures_data, output_dir, filename=None):
        """
        将比赛数据保存为JSON文件
        
        Args:
            fixtures_data (list): 比赛数据列表
            output_dir (str): 输出目录
            filename (str, optional): 文件名，如果不提供则自动生成
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 如果没有提供文件名，则自动生成
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fixtures_{timestamp}.json"
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(fixtures_data, f, ensure_ascii=False, indent=2)
            
            print(f"比赛数据已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存文件时出错: {e}")

def main():
    """主函数"""
    try:
        # 创建API客户端
        client = APIFootballClient()
        
        # 配置参数
        team_id = 1073  # 示例球队ID，可以修改
        last_matches = 10  # 最近10场比赛
        timezone = "UTC"
        
        print(f"获取球队 {team_id} 的最近 {last_matches} 场比赛...")
        print(f"参数: team_id={team_id}, last={last_matches}, timezone={timezone}")
        
        # 获取比赛数据
        fixtures_data = client.get_fixtures_by_team(
            team_id=team_id,
            last=last_matches,
            timezone=timezone
        )
        
        if fixtures_data:
            # 提取比赛信息
            extracted_data = client.extract_fixture_info(fixtures_data)
            
            if extracted_data:
                # 保存到JSON文件
                output_dir = "/Users/kuriball/Documents/MyProjects/agent/bc_agent/test_api/test_output"
                filename = f"fixtures_team_{team_id}_last_{last_matches}.json"
                
                # 直接保存比赛列表
                client.save_fixtures_to_json(extracted_data, output_dir, filename)
                
                # 显示统计信息
                print(f"\n=== 比赛记录统计 ===")
                print(f"总比赛场次: {len(extracted_data)} 场")
                
                # 统计胜负情况
                wins = 0
                losses = 0
                draws = 0
                
                for match in extracted_data:
                    if match['home_team_id'] == team_id:
                        # 球队作为主队
                        if match['home_team_winner'] is True:
                            wins += 1
                        elif match['home_team_winner'] is False:
                            losses += 1
                        else:
                            draws += 1
                    else:
                        # 球队作为客队
                        if match['away_team_winner'] is True:
                            wins += 1
                        elif match['away_team_winner'] is False:
                            losses += 1
                        else:
                            draws += 1
                
                print(f"胜利: {wins} 场")
                print(f"失败: {losses} 场")
                print(f"平局: {draws} 场")
                
            else:
                print("未能提取到有效的比赛数据")
        else:
            print("获取比赛数据失败")
            
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()