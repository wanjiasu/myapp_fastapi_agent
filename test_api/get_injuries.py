#!/usr/bin/env python3
"""
API-Football 伤病信息获取脚本
根据fixture_id获取比赛相关的伤病记录并保存为JSON文件
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
    
    def get_injuries_by_fixture(self, fixture_id, timezone="UTC"):
        """
        根据fixture_id获取比赛相关的伤病信息
        
        Args:
            fixture_id (int): 比赛ID
            timezone (str): 时区，默认为UTC
            
        Returns:
            dict: API响应数据
        """
        url = f"{self.base_url}/injuries"
        
        # 基本参数
        params = {
            'fixture': fixture_id,
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
    
    def extract_injury_info(self, injuries_data):
        """
        从API响应中提取伤病信息
        
        Args:
            injuries_data (dict): API响应数据
            
        Returns:
            list: 提取的伤病信息列表
        """
        if not injuries_data or 'response' not in injuries_data:
            print("无效的API响应数据")
            return []
        
        injuries = injuries_data['response']
        print(f"找到 {len(injuries)} 条伤病记录")
        
        extracted_injuries = []
        
        for injury in injuries:
            try:
                injury_info = {
                    # 球员信息
                    'player_id': injury['player']['id'],
                    'player_name': injury['player']['name'],
                    'player_photo': injury['player']['photo'],
                    
                    # 球队信息
                    'team_id': injury['team']['id'],
                    'team_name': injury['team']['name'],
                    'team_logo': injury['team']['logo'],
                    
                    # 伤病信息（在player字段内）
                    'injury_type': injury['player']['type'],
                    'injury_reason': injury['player']['reason'],
                    
                    # 比赛信息
                    'fixture_id': injury['fixture']['id'],
                    'fixture_date': injury['fixture']['date'],
                    
                    # 联赛信息
                    'league_id': injury['league']['id'],
                    'league_name': injury['league']['name'],
                    'league_country': injury['league']['country'],
                    'league_logo': injury['league']['logo'],
                    'season': injury['league']['season']
                }
                
                extracted_injuries.append(injury_info)
                
            except KeyError as e:
                print(f"提取伤病信息时出错，缺少字段: {e}")
                continue
        
        print(f"成功提取 {len(extracted_injuries)} 条伤病记录")
        return extracted_injuries
    
    def save_injuries_to_json(self, injuries_data, output_dir, filename=None):
        """
        将伤病数据保存为JSON文件
        
        Args:
            injuries_data (list): 伤病数据列表
            output_dir (str): 输出目录
            filename (str, optional): 文件名，如果不提供则自动生成
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 如果没有提供文件名，则自动生成
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"injuries_{timestamp}.json"
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(injuries_data, f, ensure_ascii=False, indent=2)
            
            print(f"伤病数据已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存文件时出错: {e}")

def main():
    """主函数"""
    try:
        # 创建API客户端
        client = APIFootballClient()
        
        # 配置参数 - 使用一个更可能有伤病记录的比赛ID
        fixture_id = 1451200  # 示例比赛ID，可以修改
        timezone = "UTC"
        
        print(f"获取比赛 {fixture_id} 的伤病信息...")
        print(f"参数: fixture_id={fixture_id}, timezone={timezone}")
        
        # 获取伤病数据
        injuries_data = client.get_injuries_by_fixture(
            fixture_id=fixture_id,
            timezone=timezone
        )
        
        if injuries_data:
            # 提取伤病信息
            extracted_data = client.extract_injury_info(injuries_data)
            
            if extracted_data:
                # 保存到JSON文件
                output_dir = "/Users/kuriball/Documents/MyProjects/agent/bc_agent/test_api/test_output"
                filename = f"injuries_fixture_{fixture_id}.json"
                
                # 直接保存伤病列表
                client.save_injuries_to_json(extracted_data, output_dir, filename)
                
                # 显示统计信息
                print(f"\n=== 伤病记录统计 ===")
                print(f"总伤病记录: {len(extracted_data)} 条")
                
                # 按球队统计
                team_stats = {}
                injury_types = {}
                
                for injury in extracted_data:
                    team_name = injury['team_name']
                    injury_type = injury['injury_type']
                    
                    # 统计球队伤病数量
                    if team_name not in team_stats:
                        team_stats[team_name] = 0
                    team_stats[team_name] += 1
                    
                    # 统计伤病类型
                    if injury_type not in injury_types:
                        injury_types[injury_type] = 0
                    injury_types[injury_type] += 1
                
                print(f"\n按球队统计:")
                for team, count in team_stats.items():
                    print(f"  {team}: {count} 条")
                
                print(f"\n按伤病类型统计:")
                for injury_type, count in injury_types.items():
                    print(f"  {injury_type}: {count} 条")
                
            else:
                print("未能提取到有效的伤病数据")
        else:
            print("获取伤病数据失败")
            
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()