#!/usr/bin/env python3
"""
API-Football 通过ID获取Fixture数据脚本
根据fixture ID获取单个足球比赛数据并保存为JSON文件
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
    
    def get_fixture_by_id(self, fixture_id):
        """
        根据fixture ID获取单个比赛数据
        
        Args:
            fixture_id (int): fixture的ID
        
        Returns:
            dict: API响应数据
        """
        endpoint = f"/fixtures"
        url = f"{self.base_url}{endpoint}"
        
        # 设置查询参数
        params = {
            'id': fixture_id
        }
        
        try:
            print(f"正在获取 fixture ID: {fixture_id} 的数据...")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            fixtures_count = len(data.get('response', []))
            
            if fixtures_count > 0:
                print(f"成功获取到fixture数据")
                return data
            else:
                print(f"未找到ID为 {fixture_id} 的fixture数据")
                return None
            
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None
    
    def extract_single_fixture_info(self, fixture_data):
        """
        从API响应中提取单个fixture的信息
        
        Args:
            fixture_data (dict): API返回的完整数据
        
        Returns:
            dict: 提取的fixture信息，如果没有数据则返回None
        """
        if not fixture_data or 'response' not in fixture_data or not fixture_data['response']:
            return None
        
        # 获取第一个（也是唯一的）fixture数据
        fixture = fixture_data['response'][0]
        
        fixture_info = {
            'fixture_id': fixture['fixture']['id'],
            'timezone': fixture['fixture']['timezone'],
            'fixture_date': fixture['fixture']['date'],
            'venue_name': fixture['fixture']['venue']['name'] if fixture['fixture']['venue'] else None,
            'venue_city': fixture['fixture']['venue']['city'] if fixture['fixture']['venue'] else None,
            'league_id': fixture['league']['id'],
            'league_name': fixture['league']['name'],
            'league_country': fixture['league']['country'],
            'league_season': fixture['league']['season'],
            'league_round': fixture['league']['round'],
            'home_id': fixture['teams']['home']['id'],
            'home_name': fixture['teams']['home']['name'],
            'away_id': fixture['teams']['away']['id'],
            'away_name': fixture['teams']['away']['name'],
        }
        
        return fixture_info
    
    def save_fixture_to_json(self, fixture_info, output_dir, filename=None):
        """
        将单个fixture数据保存为JSON文件
        
        Args:
            fixture_info (dict): fixture信息
            output_dir (str): 输出目录路径
            filename (str): 文件名，如果为None则自动生成
        
        Returns:
            str: 保存的文件路径
        """
        if not fixture_info:
            print("没有数据可保存")
            return None
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            fixture_id = fixture_info.get('fixture_id', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fixture_{fixture_id}_{timestamp}.json"
        
        file_path = os.path.join(output_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fixture_info, f, ensure_ascii=False, indent=2)
            
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
        
        # 示例：获取指定ID的fixture数据
        # 这里使用一个示例ID，实际使用时请替换为真实的fixture ID
        fixture_id = 1451373  # 示例ID，请根据需要修改
        
        print(f"🔍 开始获取 fixture ID: {fixture_id} 的数据...")
        
        # 获取fixture数据
        fixture_data = client.get_fixture_by_id(fixture_id)
        
        if fixture_data:
            # 提取fixture信息
            fixture_info = client.extract_single_fixture_info(fixture_data)
            
            if fixture_info:
                # 保存数据到JSON文件
                output_dir = "/Users/kuriball/Documents/MyProjects/agent/bc_agent/test_api/test_output"
                filename = f"fixture_{fixture_id}.json"
                
                saved_file = client.save_fixture_to_json(
                    fixture_info, 
                    output_dir, 
                    filename
                )
                
                if saved_file:
                    print(f"\n✅ 成功完成!")
                    print(f"🆔 Fixture ID: {fixture_info['fixture_id']}")
                    print(f"⚽ 比赛: {fixture_info['home_name']} vs {fixture_info['away_name']}")
                    print(f"🏆 联赛: {fixture_info['league_name']} ({fixture_info['league_country']})")
                    print(f"📅 日期: {fixture_info['fixture_date']}")
                    print(f"🏟️ 场地: {fixture_info['venue_name']}, {fixture_info['venue_city']}")
                    print(f"📊 状态: {fixture_info['status']}")
                    
                    if fixture_info['goals_home'] is not None and fixture_info['goals_away'] is not None:
                        print(f"⚽ 比分: {fixture_info['goals_home']} - {fixture_info['goals_away']}")
                    
                    print(f"💾 文件路径: {saved_file}")
                    
                    # 显示完整的fixture信息
                    print(f"\n📋 完整fixture信息:")
                    for key, value in fixture_info.items():
                        print(f"  {key}: {value}")
                else:
                    print("❌ 保存文件失败")
            else:
                print("❌ 提取fixture信息失败")
        else:
            print("❌ 获取fixture数据失败")
            
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")

if __name__ == "__main__":
    main()