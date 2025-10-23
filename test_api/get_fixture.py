#!/usr/bin/env python3
"""
API-Football Fixtures获取脚本
获取指定日期的足球比赛fixtures数据并保存为JSON文件
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
        
        # API-Football的基础URL和请求头 <mcreference link="https://github.com/petermclagan/footballAPI" index="1">1</mcreference>
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'v3.football.api-sports.io'
        }
    
    def get_fixtures_by_date(self, date_str, timezone='UTC'):
        """
        根据日期获取fixtures数据
        
        Args:
            date_str (str): 日期字符串，格式为YYYY-MM-DD
            timezone (str): 时区，默认为UTC <mcreference link="https://docs.sportmonks.com/football/tutorials-and-guides/tutorials/timezone-parameters-on-different-endpoints" index="3">3</mcreference>
        
        Returns:
            dict: API响应数据
        """
        endpoint = f"/fixtures"
        url = f"{self.base_url}{endpoint}"
        
        # 设置查询参数
        params = {
            'date': date_str,
            'timezone': timezone
        }
        
        try:
            print(f"正在获取 {date_str} ({timezone}) 的fixtures数据...")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"成功获取到 {len(data.get('response', []))} 场比赛数据")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None
    
    def extract_fixture_info(self, fixtures_data):
        """
        从API响应中提取所需的fixture信息
        
        Args:
            fixtures_data (dict): API返回的完整数据
        
        Returns:
            list: 提取的fixture信息列表
        """
        if not fixtures_data or 'response' not in fixtures_data:
            return []
        
        extracted_fixtures = []
        
        for fixture in fixtures_data['response']:
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
                'away_name': fixture['teams']['away']['name']
            }
            extracted_fixtures.append(fixture_info)
        
        return extracted_fixtures
    
    def save_fixtures_to_json(self, fixtures_data, output_dir, filename=None):
        """
        将fixtures数据保存为JSON文件
        
        Args:
            fixtures_data (dict): fixtures数据
            output_dir (str): 输出目录路径
            filename (str): 文件名，如果为None则自动生成
        
        Returns:
            str: 保存的文件路径
        """
        if not fixtures_data:
            print("没有数据可保存")
            return None
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fixtures_{timestamp}.json"
        
        file_path = os.path.join(output_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fixtures_data, f, ensure_ascii=False, indent=2)
            
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
        
        # 获取2025-10-24的fixtures数据
        target_date = "2025-10-24"
        fixtures_data = client.get_fixtures_by_date(target_date, timezone='Asia/Singapore')
        
        if fixtures_data:
            # 提取所需的fixture信息
            extracted_fixtures = client.extract_fixture_info(fixtures_data)
            
            # 保存提取的数据到JSON文件
            output_dir = "/Users/kuriball/Documents/MyProjects/agent/bc_agent/test_api/test_output"
            filename = f"fixtures_{target_date}_extracted.json"
            
            saved_file = client.save_fixtures_to_json(
                extracted_fixtures, 
                output_dir, 
                filename
            )
            
            if saved_file:
                print(f"\n✅ 成功完成!")
                print(f"📅 日期: {target_date} (UTC)")
                print(f"📊 比赛数量: {len(extracted_fixtures)}")
                print(f"💾 文件路径: {saved_file}")
                
                # 显示前3条数据作为示例
                if extracted_fixtures:
                    print(f"\n📋 数据示例 (前3条):")
                    for i, fixture in enumerate(extracted_fixtures[:3]):
                        print(f"\n比赛 {i+1}:")
                        for key, value in fixture.items():
                            print(f"  {key}: {value}")
            else:
                print("❌ 保存文件失败")
        else:
            print("❌ 获取fixtures数据失败")
            
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")

if __name__ == "__main__":
    main()