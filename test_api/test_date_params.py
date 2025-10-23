#!/usr/bin/env python3
"""
测试API-Football日期参数的影响
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class APIFootballTester:
    def __init__(self):
        self.api_key = os.getenv('API_FOOTBALL_KEY')
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'v3.football.api-sports.io'
        }

    def test_headtohead_with_dates(self, home_id, away_id):
        """测试带日期参数和不带日期参数的差异"""
        url = f"{self.base_url}/fixtures/headtohead"
        
        # 计算日期范围
        now = datetime.now()
        end_date = now.strftime('%Y-%m-%d')
        start_date = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        
        print(f"测试球队 {home_id} vs {away_id} 的对战记录")
        print(f"日期范围: {start_date} 到 {end_date}")
        print("=" * 50)
        
        # 测试1: 不带日期参数
        print("1. 不带日期参数的请求:")
        params1 = {
            'h2h': f'{home_id}-{away_id}',
            'timezone': 'UTC',
            'last': 10
        }
        print(f"参数: {params1}")
        
        response1 = requests.get(url, headers=self.headers, params=params1)
        print(f"状态码: {response1.status_code}")
        
        if response1.status_code == 200:
            data1 = response1.json()
            matches1 = data1.get('response', [])
            print(f"找到 {len(matches1)} 场比赛")
            if matches1:
                for i, match in enumerate(matches1):
                    fixture_date = match['fixture']['date']
                    print(f"  比赛{i+1}: {fixture_date}")
        print()
        
        # 测试2: 带日期参数
        print("2. 带日期参数的请求:")
        params2 = {
            'h2h': f'{home_id}-{away_id}',
            'timezone': 'UTC',
            'last': 10,
            'from': start_date,
            'to': end_date
        }
        print(f"参数: {params2}")
        
        response2 = requests.get(url, headers=self.headers, params=params2)
        print(f"状态码: {response2.status_code}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            matches2 = data2.get('response', [])
            print(f"找到 {len(matches2)} 场比赛")
            if matches2:
                for i, match in enumerate(matches2):
                    fixture_date = match['fixture']['date']
                    print(f"  比赛{i+1}: {fixture_date}")
        print()
        
        # 测试3: 只带from参数
        print("3. 只带from参数的请求:")
        params3 = {
            'h2h': f'{home_id}-{away_id}',
            'timezone': 'UTC',
            'last': 10,
            'from': start_date
        }
        print(f"参数: {params3}")
        
        response3 = requests.get(url, headers=self.headers, params=params3)
        print(f"状态码: {response3.status_code}")
        
        if response3.status_code == 200:
            data3 = response3.json()
            matches3 = data3.get('response', [])
            print(f"找到 {len(matches3)} 场比赛")
            if matches3:
                for i, match in enumerate(matches3):
                    fixture_date = match['fixture']['date']
                    print(f"  比赛{i+1}: {fixture_date}")

def main():
    tester = APIFootballTester()
    
    # 使用相同的测试参数
    home_id = 1073  # Wacker Innsbruck
    away_id = 8255  # Lauterach
    
    tester.test_headtohead_with_dates(home_id, away_id)

if __name__ == "__main__":
    main()